"""Recorrência: a regra que gera um previsto a cada N semanas ou N meses (o salário, a luz, o
seguro anual). Ela não é um lançamento (ADR 0004): os previstos são lançamentos comuns, ligados a
ela pelo `recorrencia_id` e pelo número da ocorrência. A recorrência sem fim gera até o horizonte
(`horizonteDaRecorrenciaMeses`), e a tarefa diária o estende e realiza os automáticos."""

from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid5

import psycopg
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field, field_validator, model_validator

from app import lancamentos
from app.backup import LINHAS_POR_LOTE
from app.banco import conectar, em_transacao
from app.config import valores_iniciais
from app.lancamentos import (
    conferir_ligacoes,
    ids_das_tags,
    registrar_mudancas,
    sem_repetidas,
    subir_versao,
    tags_limpas,
    url_do_banco,
)
from app.login import UsuarioLogado

router = APIRouter(prefix="/api")


class NovaRecorrencia(BaseModel):
    id: UUID
    tipo: Literal["despesa", "receita"]
    valor_centavos: int = Field(gt=0)
    # Fixo (o Spotify) ou estimado (o salário, a luz). Só o fixo pode ser automático: o estimado
    # sempre pede confirmação, para o saldo nunca mostrar uma estimativa como real.
    tipo_do_valor: Literal["fixo", "estimado"]
    automatico: bool = False
    descricao: str = ""
    conta_id: UUID
    categoria_ids: list[UUID] = Field(min_length=1)
    tags: list[str] = []
    # O id de uma pessoa do casal, que os previstos herdam; sem ela, a regra é do conjunto.
    pessoa: str | None = None
    # A primeira ocorrência; o dia dela vale para todas, e 31 em mês curto cai no último dia.
    inicio: date
    a_cada: int = Field(ge=1)
    unidade: Literal["semanas", "meses"]
    # Sem os dois, não tem fim; `ate` é a última data possível e `vezes`, o número de ocorrências.
    ate: date | None = None
    vezes: int | None = Field(default=None, ge=1)

    _tags = field_validator("tags")(tags_limpas)
    _categorias = field_validator("categoria_ids")(sem_repetidas)

    @model_validator(mode="after")
    def _regra_coerente(self):
        if self.automatico and self.tipo_do_valor != "fixo":
            raise ValueError("só a recorrência de valor fixo pode ser automática")
        if self.ate is not None and self.vezes is not None:
            raise ValueError("a recorrência termina numa data ou depois de N vezes, não nos dois")
        if self.ate is not None and self.ate < self.inicio:
            raise ValueError("a data de fim vem antes do início")
        return self


class Recorrencia(NovaRecorrencia):
    criado_por: str
    criado_em: datetime
    alterado_por: str
    alterado_em: datetime


_COLUNAS = (
    "id, tipo, valor_centavos, tipo_do_valor, automatico, descricao, conta_id, inicio, a_cada, unidade,"
    " ate, vezes, criado_por, criado_em, alterado_por, alterado_em, pessoa"
)
_NOMES_DAS_COLUNAS = _COLUNAS.replace(" ", "").split(",")


def mais_meses(dia: date, meses: int) -> date:
    """O mesmo dia `meses` depois; o que não existe no mês de chegada cai no último dia."""
    contados = dia.month - 1 + meses
    ano, mes = dia.year + contados // 12, contados % 12 + 1
    return date(ano, mes, min(dia.day, monthrange(ano, mes)[1]))


def data_da_ocorrencia(regra: NovaRecorrencia, n: int) -> date:
    """A data da n-ésima ocorrência (1, 2...), contada do início e nunca da anterior: o dia 31
    passa por 30/11 e volta a 31/12."""
    if regra.unidade == "semanas":
        return regra.inicio + timedelta(weeks=(n - 1) * regra.a_cada)
    return mais_meses(regra.inicio, (n - 1) * regra.a_cada)


def horizonte() -> date:
    """Até onde a recorrência gera previstos: hoje mais o horizonte da configuração."""
    return mais_meses(lancamentos.hoje(), valores_iniciais()["horizonteDaRecorrenciaMeses"])


def _ler(conn, filtro: str = "", parametros: tuple = ()) -> list[Recorrencia]:
    linhas = conn.execute(
        f"SELECT {_COLUNAS} FROM recorrencias {'WHERE ' + filtro if filtro else ''}"
        " ORDER BY descricao, id",
        parametros,
    ).fetchall()
    ids = [linha[0] for linha in linhas]
    categorias: dict[UUID, list[UUID]] = {}
    for recorrencia_id, categoria_id in conn.execute(
        "SELECT recorrencia_id, categoria_id FROM recorrencia_categorias"
        " WHERE recorrencia_id = ANY(%s) ORDER BY categoria_id",
        (ids,),
    ):
        categorias.setdefault(recorrencia_id, []).append(categoria_id)
    tags: dict[UUID, list[str]] = {}
    for recorrencia_id, nome in conn.execute(
        "SELECT rt.recorrencia_id, t.nome FROM recorrencia_tags rt JOIN tags t ON t.id = rt.tag_id"
        " WHERE rt.recorrencia_id = ANY(%s) ORDER BY t.nome",
        (ids,),
    ):
        tags.setdefault(recorrencia_id, []).append(nome)
    return [
        Recorrencia(
            **dict(zip(_NOMES_DAS_COLUNAS, linha)),
            categoria_ids=categorias.get(linha[0], []),
            tags=tags.get(linha[0], []),
        )
        for linha in linhas
    ]


def _gerar_um_lote(conn, id: UUID) -> bool:
    """Grava as próximas ocorrências até o horizonte, quantas cabem numa transação, e devolve se
    pode faltar alguma. O id de cada previsto vem da regra e do número da ocorrência: gerar de
    novo não duplica, e o previsto excluído (o mês pulado) não volta."""
    [regra] = _ler(conn, "id = %s", (id,))
    (geradas,) = conn.execute("SELECT geradas FROM recorrencias WHERE id = %s", (id,)).fetchone()
    categorias = regra.categoria_ids
    tags = [
        tag
        for (tag,) in conn.execute(
            "SELECT tag_id FROM recorrencia_tags WHERE recorrencia_id = %s", (id,)
        )
    ]
    # O DSQL aceita até 3.000 linhas por transação: a mesma folga da restauração.
    por_lote = max(1, LINHAS_POR_LOTE // (1 + len(categorias) + len(tags)))
    ultimo_dia, dia_de_hoje = horizonte(), lancamentos.hoje()
    proximas: list[tuple[int, date]] = []
    for n in range(geradas + 1, geradas + 1 + por_lote):
        dia = data_da_ocorrencia(regra, n)
        if (regra.vezes and n > regra.vezes) or (regra.ate and dia > regra.ate):
            break
        if dia > ultimo_dia:
            break
        proximas.append((n, dia))
    if not proximas:
        return False
    for n, dia in proximas:
        lancamento_id = uuid5(id, str(n))
        # O automático com data de hoje ou do passado já nasce realizado; o resto, previsto.
        situacao = "realizado" if regra.automatico and dia <= dia_de_hoje else "previsto"
        gravado = conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, descricao,"
            " conta_id, criado_por, alterado_por, versao, recorrencia_id, ocorrencia, automatico,"
            " pessoa, fonte) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s, 'app')"
            " ON CONFLICT (id) DO NOTHING",
            (
                lancamento_id,
                regra.tipo,
                situacao,
                regra.valor_centavos,
                dia,
                regra.descricao,
                regra.conta_id,
                regra.alterado_por,
                regra.alterado_por,
                id,
                n,
                regra.automatico,
                regra.pessoa,
            ),
        ).rowcount
        if not gravado:
            continue
        for categoria in categorias:
            conn.execute(
                "INSERT INTO lancamento_categorias (lancamento_id, categoria_id) VALUES (%s, %s)",
                (lancamento_id, categoria),
            )
        for tag in tags:
            conn.execute(
                "INSERT INTO lancamento_tags (lancamento_id, tag_id) VALUES (%s, %s)",
                (lancamento_id, tag),
            )
    ate = proximas[-1][0]
    if not conn.execute(
        "UPDATE recorrencias SET geradas = %s WHERE id = %s AND geradas = %s", (ate, id, geradas)
    ).rowcount:
        # Outra geração andou junto: a transação recomeça e parte do que ela gravou.
        raise psycopg.errors.SerializationFailure("a recorrência mudou durante a geração")
    return len(proximas) == por_lote


def gerar_ate_o_horizonte(url: str | None, id: UUID) -> None:
    """Gera, em lotes de uma transação cada, o que falta até o horizonte. Se parar no meio, a
    próxima chamada (ou a tarefa diária) continua de onde parou."""
    while em_transacao(url, lambda conn: _gerar_um_lote(conn, id)):
        pass


def origem(descricao: str) -> str:
    """Como a tela de conflito nomeia a regra que mudou o lançamento ("O da regra ...")."""
    return f"a recorrência {descricao}".strip()


def _realizar(conn, id: UUID) -> bool:
    """Realiza o previsto automático, se ele ainda for um: a leitura fora da transação pode ter
    envelhecido (alguém confirmou ou excluiu no meio)."""
    linha = conn.execute(
        f"SELECT {lancamentos.VERSAO}, r.descricao, r.alterado_por FROM lancamentos l"
        " JOIN recorrencias r ON r.id = l.recorrencia_id"
        " WHERE l.id = %s AND l.situacao = 'previsto' AND COALESCE(l.automatico, false)"
        " AND l.excluido_em IS NULL AND l.data <= %s",
        (id, lancamentos.hoje()),
    ).fetchone()
    if not linha:
        return False
    versao, descricao, quem = linha
    # Quem responde pela regra é quem a mudou por último; a `origem` diz que foi a regra.
    nova = subir_versao(
        conn, id, versao, "situacao = 'realizado', alterado_por = %s, alterado_em = now()", (quem,)
    )
    registrar_mudancas(
        conn, id, ["situacao"], nova, quem, datetime.now(UTC), origem=origem(descricao)
    )
    return True


def realizar_automaticos(url: str | None) -> int:
    """Vira realizado, sem confirmação, cada previsto automático com data até hoje, um por
    transação; devolve quantos."""
    with conectar(url) as conn:
        devidos = [
            id
            for (id,) in conn.execute(
                "SELECT id FROM lancamentos WHERE situacao = 'previsto'"
                " AND COALESCE(automatico, false) AND excluido_em IS NULL AND data <= %s",
                (lancamentos.hoje(),),
            )
        ]
    return sum(em_transacao(url, lambda conn, id=id: _realizar(conn, id)) for id in devidos)


def estender_todas(url: str | None) -> int:
    """Gera o que falta até o horizonte em cada recorrência que ainda pode gerar; devolve
    quantas olhou."""
    with conectar(url) as conn:
        ids = [
            id
            for (id,) in conn.execute(
                "SELECT id FROM recorrencias WHERE vezes IS NULL OR geradas < vezes"
            )
        ]
    for id in ids:
        gerar_ate_o_horizonte(url, id)
    return len(ids)


@router.post(
    "/recorrencias",
    status_code=201,
    response_model=Recorrencia,
    operation_id="criar_recorrencia",
)
def criar_recorrencia(
    nova: NovaRecorrencia, usuario: UsuarioLogado, request: Request, response: Response
) -> Recorrencia:
    """Grava a regra e gera os previstos até o horizonte. Reenviar o mesmo id (a fila repete)
    devolve a regra gravada, com 200, e completa a geração se ela tiver parado no meio."""

    def gravar(conn) -> Recorrencia:
        if ja := _ler(conn, "id = %s", (nova.id,)):
            response.status_code = 200
            return ja[0]
        conferir_ligacoes(conn, nova)
        tags = ids_das_tags(conn, nova.tags, usuario, set())
        gravada = conn.execute(
            f"INSERT INTO recorrencias ({_COLUNAS}, geradas)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), %s, now(), %s, 0)"
            # Dois reenvios ao mesmo tempo: o segundo fica com a regra que o primeiro gravou.
            " ON CONFLICT (id) DO NOTHING",
            (
                nova.id,
                nova.tipo,
                nova.valor_centavos,
                nova.tipo_do_valor,
                nova.automatico,
                nova.descricao,
                nova.conta_id,
                nova.inicio,
                nova.a_cada,
                nova.unidade,
                nova.ate,
                nova.vezes,
                usuario,
                usuario,
                nova.pessoa,
            ),
        ).rowcount
        if not gravada:
            response.status_code = 200
            return _ler(conn, "id = %s", (nova.id,))[0]
        for categoria in nova.categoria_ids:
            conn.execute(
                "INSERT INTO recorrencia_categorias (recorrencia_id, categoria_id) VALUES (%s, %s)",
                (nova.id, categoria),
            )
        for tag in tags:
            conn.execute(
                "INSERT INTO recorrencia_tags (recorrencia_id, tag_id) VALUES (%s, %s)",
                (nova.id, tag),
            )
        return _ler(conn, "id = %s", (nova.id,))[0]

    url = url_do_banco(request)
    criada = em_transacao(url, gravar)
    gerar_ate_o_horizonte(url, nova.id)
    return criada


@router.get("/recorrencias", response_model=list[Recorrencia], operation_id="listar_recorrencias")
def listar_recorrencias(usuario: UsuarioLogado, request: Request) -> list[Recorrencia]:
    with conectar(url_do_banco(request)) as conn:
        return _ler(conn)
