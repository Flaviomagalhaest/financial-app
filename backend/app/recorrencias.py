"""Recorrência: a regra que gera um previsto a cada N semanas ou N meses (o salário, a luz, o
seguro anual). Ela não é um lançamento (ADR 0004): os previstos são lançamentos comuns, ligados a
ela pelo `recorrencia_id` e pelo número da ocorrência. A recorrência sem fim gera até o horizonte
(`horizonteDaRecorrenciaMeses`), e a tarefa diária o estende e realiza os automáticos."""

from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid5

import psycopg
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app import faturas, lancamentos
from app.backup import LINHAS_POR_LOTE
from app.banco import conectar, em_transacao
from app.config import valores_iniciais
from app.lancamentos import (
    conferir_ligacoes,
    excluir,
    gravar_categorias,
    ids_das_tags,
    recusar,
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
    # O item do planejamento em que os previstos contam, quando o casal o escolheu (ADR 0006); os
    # previstos herdam a escolha assim que o lançamento passar a guardá-la (ticket 51).
    item_id: UUID | None = None

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
    # O número da ocorrência que cai em `inicio`: 1 até a regra mudar de calendário "daqui para
    # frente", quando `inicio` passa a ser a data da ocorrência em que a mudança começou.
    ocorrencia_do_inicio: int = 1
    criado_por: str
    criado_em: datetime
    alterado_por: str
    alterado_em: datetime


class AlteracaoDeRecorrencia(BaseModel):
    """Os campos da regra que mudam "daqui para frente", a partir da ocorrência dada: a regra
    passa a valer assim e os previstos dessa ocorrência em diante, que ninguém alterou à mão,
    são refeitos. O que já foi realizado e os previstos de antes ficam como estão. Campo
    ausente fica como está; `pessoa` vazia passa a regra para o conjunto."""

    a_partir_da_ocorrencia: int = Field(ge=1)
    # Sem `None` no tipo: mandar null num campo obrigatório da regra é erro, não "limpar".
    tipo: Literal["despesa", "receita"] = Field(default=None)
    valor_centavos: int = Field(default=None, gt=0)
    tipo_do_valor: Literal["fixo", "estimado"] = Field(default=None)
    automatico: bool = Field(default=None)
    descricao: str = Field(default=None)
    conta_id: UUID = Field(default=None)
    categoria_ids: list[UUID] = Field(default=None, min_length=1)
    tags: list[str] = Field(default=None)
    pessoa: str | None = None
    item_id: UUID | None = None
    # Mudar o calendário daqui para frente: a ocorrência `a_partir_da_ocorrencia` cai em `inicio`
    # (sem ele, na data que já tinha) e as seguintes, a cada N semanas ou meses.
    a_cada: int = Field(default=None, ge=1)
    unidade: Literal["semanas", "meses"] = Field(default=None)
    inicio: date = Field(default=None)
    # Encerrar: os previstos depois da data (ou da N-ésima vez) saem. Mandar um tira o outro, e
    # null tira o fim.
    ate: date | None = None
    vezes: int | None = Field(default=None, ge=1)

    _tags = field_validator("tags")(tags_limpas)
    _categorias = field_validator("categoria_ids")(sem_repetidas)


_GRAVADAS = (
    "id, tipo, valor_centavos, tipo_do_valor, automatico, descricao, conta_id, inicio, a_cada, unidade,"
    " ate, vezes, criado_por, criado_em, alterado_por, alterado_em, pessoa, item_id"
)
# Recorrência de antes do ticket 45 não tem a ocorrência do início: é a 1ª.
_COLUNAS = f"{_GRAVADAS}, COALESCE(ocorrencia_do_inicio, 1)"
_NOMES_DAS_COLUNAS = [*_GRAVADAS.replace(" ", "").split(","), "ocorrencia_do_inicio"]


def mais_meses(dia: date, meses: int) -> date:
    """O mesmo dia `meses` depois; o que não existe no mês de chegada cai no último dia."""
    contados = dia.month - 1 + meses
    ano, mes = dia.year + contados // 12, contados % 12 + 1
    return date(ano, mes, min(dia.day, monthrange(ano, mes)[1]))


def data_da_ocorrencia(regra: Recorrencia, n: int) -> date:
    """A data da n-ésima ocorrência (1, 2...), contada do início e nunca da anterior: o dia 31
    passa por 30/11 e volta a 31/12."""
    desde_o_inicio = n - regra.ocorrencia_do_inicio
    if regra.unidade == "semanas":
        return regra.inicio + timedelta(weeks=desde_o_inicio * regra.a_cada)
    return mais_meses(regra.inicio, desde_o_inicio * regra.a_cada)


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
    tags = _tags_da_regra(conn, id)
    # O DSQL aceita até 3.000 linhas por transação: a mesma folga da restauração.
    por_lote = max(1, LINHAS_POR_LOTE // (1 + len(categorias) + len(tags)))
    ultimo_dia, dia_de_hoje = horizonte(), lancamentos.hoje()
    proximas: list[tuple[int, date]] = []
    for n in range(geradas + 1, geradas + 1 + por_lote):
        dia = data_da_ocorrencia(regra, n)
        if _fora_do_fim(regra, n, dia) or dia > ultimo_dia:
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
            " pessoa, fonte, mes)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s, 'app', %s)"
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
                # No cartão, o mês da fatura em que o previsto cai (ADR 0003).
                lancamentos.mes_em_que_conta(conn, regra.conta_id, dia),
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


def _tags_da_regra(conn, id: UUID) -> list[UUID]:
    return [
        tag
        for (tag,) in conn.execute(
            "SELECT tag_id FROM recorrencia_tags WHERE recorrencia_id = %s", (id,)
        )
    ]


def _campos_da_regra(nova: NovaRecorrencia) -> dict:
    """O que um previsto herda da regra, com os nomes dos campos do lançamento."""
    return {
        "tipo": nova.tipo,
        "valor_centavos": nova.valor_centavos,
        "descricao": nova.descricao,
        "conta_id": nova.conta_id,
        "pessoa": nova.pessoa,
        "categoria_ids": set(nova.categoria_ids),
        "tags": {tag.casefold() for tag in nova.tags},
    }


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
            f"INSERT INTO recorrencias ({_GRAVADAS}, geradas)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), %s, now(), %s, %s,"
            " 0)"
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
                nova.item_id,
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


def _fora_do_fim(regra: Recorrencia, n: int, dia: date) -> bool:
    return bool((regra.vezes and n > regra.vezes) or (regra.ate and dia > regra.ate))


def _por_lote(regra: Recorrencia) -> int:
    """Quantos previstos cabem numa transação, pelas linhas que cada um mexe (a folga do DSQL é a
    mesma da geração)."""
    return max(1, LINHAS_POR_LOTE // (10 + 2 * (len(regra.categoria_ids) + len(regra.tags))))


def _reajustar_um_lote(conn, id: UUID, desde: int, usuario: str) -> bool:
    """Põe os previstos de acordo com a regra de hoje, até um lote, e devolve se pode faltar
    algum: tira os que passaram do fim e refaz, da ocorrência `desde` em diante, os que ninguém
    alterou à mão (previsto com algum campo de `origem` vazia, mexido por uma pessoa, fica como
    está por inteiro). Não toca no realizado. O que já está como a regra
    manda não conta, por isso o lote seguinte sempre anda."""
    [regra] = _ler(conn, "id = %s", (id,))
    previstos = conn.execute(
        f"SELECT l.id, l.ocorrencia, l.data, l.tipo, l.valor_centavos, l.descricao, l.conta_id,"
        f" l.pessoa, COALESCE(l.automatico, false), {lancamentos.VERSAO},"
        " EXISTS (SELECT FROM lancamento_campos c WHERE c.lancamento_id = l.id"
        " AND c.origem IS NULL)"
        " FROM lancamentos l WHERE l.recorrencia_id = %s"
        " AND l.situacao = 'previsto' AND l.excluido_em IS NULL ORDER BY l.ocorrencia",
        (id,),
    ).fetchall()
    ids = [linha[0] for linha in previstos]
    categorias: dict[UUID, set[UUID]] = {}
    for lancamento_id, categoria_id in conn.execute(
        "SELECT lancamento_id, categoria_id FROM lancamento_categorias"
        " WHERE lancamento_id = ANY(%s)",
        (ids,),
    ):
        categorias.setdefault(lancamento_id, set()).add(categoria_id)
    tags: dict[UUID, set[str]] = {}
    for lancamento_id, nome in conn.execute(
        "SELECT lt.lancamento_id, t.nome FROM lancamento_tags lt JOIN tags t ON t.id = lt.tag_id"
        " WHERE lt.lancamento_id = ANY(%s)",
        (ids,),
    ):
        tags.setdefault(lancamento_id, set()).add(nome.casefold())
    regras = _campos_da_regra(regra)
    trabalho: list[tuple[UUID, int, list[str], date] | UUID] = []
    for (
        lancamento_id,
        n,
        dia,
        tipo,
        valor,
        descricao,
        conta,
        pessoa,
        automatico,
        versao,
        a_mao,
    ) in previstos:
        if _fora_do_fim(regra, n, dia):
            trabalho.append(lancamento_id)
            continue
        if a_mao or n < desde:
            continue
        tem = {
            "tipo": tipo,
            "valor_centavos": valor,
            "descricao": descricao,
            "conta_id": conta,
            "pessoa": pessoa,
            "data": dia,
            "categoria_ids": categorias.get(lancamento_id, set()),
            "tags": tags.get(lancamento_id, set()),
        }
        # Antes da última mudança de calendário a regra não sabe mais a data: fica a que tem.
        dia_novo = data_da_ocorrencia(regra, n) if n >= regra.ocorrencia_do_inicio else dia
        quer = regras | {"data": dia_novo}
        mudou = [campo for campo in quer if quer[campo] != tem[campo]]
        if mudou or automatico != regra.automatico:
            trabalho.append((lancamento_id, versao, mudou, quer["data"]))
    tags_da_regra = _tags_da_regra(conn, id)
    agora = datetime.now(UTC)
    por_lote = _por_lote(regra)
    for item in trabalho[:por_lote]:
        if isinstance(item, UUID):
            excluir(conn, item, None, usuario)
            continue
        lancamento_id, versao, mudou, dia = item
        nova = subir_versao(
            conn,
            lancamento_id,
            versao,
            "tipo = %s, valor_centavos = %s, descricao = %s, conta_id = %s, pessoa = %s,"
            " data = %s, automatico = %s, mes = %s, alterado_por = %s, alterado_em = %s",
            (
                regra.tipo,
                regra.valor_centavos,
                regra.descricao,
                regra.conta_id,
                regra.pessoa,
                dia,
                regra.automatico,
                lancamentos.mes_em_que_conta(conn, regra.conta_id, dia),
                usuario,
                agora,
            ),
        )
        # A fatura que o app escolheu de novo conta como mudança da regra (ADR 0011).
        if {"data", "conta_id"} & set(mudou) and faturas.ler_cartao(conn, regra.conta_id):
            mudou.append("fatura_mes")
        registrar_mudancas(
            conn, lancamento_id, mudou, nova, usuario, agora, origem=origem(regra.descricao)
        )
        if "categoria_ids" in mudou:
            gravar_categorias(conn, lancamento_id, regra.categoria_ids)
        if "tags" in mudou:
            conn.execute("DELETE FROM lancamento_tags WHERE lancamento_id = %s", (lancamento_id,))
            for tag in tags_da_regra:
                conn.execute(
                    "INSERT INTO lancamento_tags (lancamento_id, tag_id) VALUES (%s, %s)",
                    (lancamento_id, tag),
                )
    return len(trabalho) > por_lote


def _mudar(conn, id: UUID, alteracao: AlteracaoDeRecorrencia, usuario: str) -> Recorrencia:
    """Valida e grava a regra nova (a ocorrência precisa existir; `ate` e `vezes` não valem juntos;
    mudar o calendário remarca o `inicio` na ocorrência dada); o reajuste dos previstos vem
    depois, em lotes."""
    if not (lidas := _ler(conn, "id = %s", (id,))):
        raise HTTPException(status_code=404, detail="recorrência não encontrada")
    [atual] = lidas
    (geradas,) = conn.execute("SELECT geradas FROM recorrencias WHERE id = %s", (id,)).fetchone()
    n = alteracao.a_partir_da_ocorrencia
    if n > geradas + 1:
        raise recusar("a ocorrência ainda não foi gerada")
    pedidas = alteracao.model_dump(
        exclude={"a_partir_da_ocorrencia"}, include=alteracao.model_fields_set
    )
    if pedidas.get("ate") is not None:
        pedidas.setdefault("vezes", None)
    if pedidas.get("vezes") is not None:
        pedidas.setdefault("ate", None)
    if {"a_cada", "unidade", "inicio"} & pedidas.keys():
        if n < atual.ocorrencia_do_inicio:
            raise recusar("o calendário já mudou depois dessa ocorrência")
        pedidas.setdefault("inicio", data_da_ocorrencia(atual, n))
        pedidas["ocorrencia_do_inicio"] = n
    try:
        nova = Recorrencia(**(atual.model_dump() | pedidas))
    except ValidationError as erro:
        raise recusar("; ".join(e["msg"] for e in erro.errors())) from erro
    conferir_ligacoes(conn, nova, atual.conta_id, frozenset(atual.categoria_ids))
    tags_de_antes = set(_tags_da_regra(conn, id))
    tags = ids_das_tags(conn, nova.tags, usuario, tags_de_antes)
    if not conn.execute(
        "UPDATE recorrencias SET tipo = %s, valor_centavos = %s, tipo_do_valor = %s,"
        " automatico = %s, descricao = %s, conta_id = %s, pessoa = %s, item_id = %s,"
        " inicio = %s, a_cada = %s, unidade = %s, ate = %s, vezes = %s,"
        " ocorrencia_do_inicio = %s, alterado_por = %s, alterado_em = now()"
        " WHERE id = %s AND geradas = %s",
        (
            nova.tipo,
            nova.valor_centavos,
            nova.tipo_do_valor,
            nova.automatico,
            nova.descricao,
            nova.conta_id,
            nova.pessoa,
            nova.item_id,
            nova.inicio,
            nova.a_cada,
            nova.unidade,
            nova.ate,
            nova.vezes,
            nova.ocorrencia_do_inicio,
            usuario,
            id,
            geradas,
        ),
    ).rowcount:
        raise psycopg.errors.SerializationFailure("a recorrência mudou durante a alteração")
    if set(nova.categoria_ids) != set(atual.categoria_ids):
        conn.execute("DELETE FROM recorrencia_categorias WHERE recorrencia_id = %s", (id,))
        for categoria in nova.categoria_ids:
            conn.execute(
                "INSERT INTO recorrencia_categorias (recorrencia_id, categoria_id) VALUES (%s, %s)",
                (id, categoria),
            )
    if set(tags) != tags_de_antes:
        conn.execute("DELETE FROM recorrencia_tags WHERE recorrencia_id = %s", (id,))
        for tag in tags:
            conn.execute(
                "INSERT INTO recorrencia_tags (recorrencia_id, tag_id) VALUES (%s, %s)", (id, tag)
            )
    return _ler(conn, "id = %s", (id,))[0]


@router.patch("/recorrencias/{id}", response_model=Recorrencia, operation_id="alterar_recorrencia")
def alterar_recorrencia(
    id: UUID, alteracao: AlteracaoDeRecorrencia, usuario: UsuarioLogado, request: Request
) -> Recorrencia:
    """Muda a regra "daqui para frente" (a partir de uma ocorrência), tira os previstos que
    passaram do fim e refaz os que ninguém alterou à mão. Mudar só um mês é editar o previsto, e
    pular um mês é excluí-lo: a geração não o traz de volta."""
    url = url_do_banco(request)
    em_transacao(url, lambda conn: _mudar(conn, id, alteracao, usuario))
    desde = alteracao.a_partir_da_ocorrencia
    while em_transacao(url, lambda conn: _reajustar_um_lote(conn, id, desde, usuario)):
        pass
    gerar_ate_o_horizonte(url, id)
    with conectar(url) as conn:
        return _ler(conn, "id = %s", (id,))[0]


def _excluir_um_lote(conn, id: UUID, usuario: str) -> bool:
    """Exclui, até um lote, os previstos da regra de hoje em diante e devolve se pode faltar
    algum. O atrasado (previsto de data passada) fica: nada some sem o casal confirmar ou
    excluir."""
    if not (lidas := _ler(conn, "id = %s", (id,))):
        return False
    por_lote = _por_lote(lidas[0])
    a_excluir = [
        lancamento_id
        for (lancamento_id,) in conn.execute(
            "SELECT id FROM lancamentos WHERE recorrencia_id = %s AND situacao = 'previsto'"
            " AND excluido_em IS NULL AND data >= %s ORDER BY ocorrencia LIMIT %s",
            (id, lancamentos.hoje(), por_lote + 1),
        )
    ]
    for lancamento_id in a_excluir[:por_lote]:
        excluir(conn, lancamento_id, None, usuario)
    return len(a_excluir) > por_lote


@router.delete("/recorrencias/{id}", status_code=204, operation_id="excluir_recorrencia")
def excluir_recorrencia(id: UUID, usuario: UsuarioLogado, request: Request) -> Response:
    """Idempotente. Tira a regra e os previstos de hoje em diante; o realizado e o atrasado
    ficam, como lançamentos que a regra gerou."""
    url = url_do_banco(request)

    def fechar(conn) -> None:
        # Sem fim ontem, a tarefa diária geraria previstos novos enquanto os de hoje saem.
        conn.execute(
            "UPDATE recorrencias SET ate = %s, vezes = NULL WHERE id = %s",
            (lancamentos.hoje() - timedelta(days=1), id),
        )

    em_transacao(url, fechar)
    while em_transacao(url, lambda conn: _excluir_um_lote(conn, id, usuario)):
        pass

    def tirar(conn) -> None:
        conn.execute("DELETE FROM recorrencia_categorias WHERE recorrencia_id = %s", (id,))
        conn.execute("DELETE FROM recorrencia_tags WHERE recorrencia_id = %s", (id,))
        conn.execute("DELETE FROM recorrencias WHERE id = %s", (id,))

    em_transacao(url, tirar)
    return Response(status_code=204)
