"""Parcelamento: a compra ou a dívida em N parcelas. Ele não é um lançamento (ADR 0004): cada
parcela é um lançamento comum, ligado a ele pelo `parcelamento_id` e pelo número da parcela,
para o valor inteiro nunca contar de uma vez num mês só. No cartão, todas as parcelas têm a data
da compra e a parcela n cai n - 1 faturas depois da fatura da compra; fora dele (o boleto), a
parcela n vence n - 1 meses depois da primeira."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid5

import psycopg
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field, field_validator, model_validator

from app import faturas, lancamentos
from app.backup import LINHAS_POR_LOTE
from app.banco import conectar, em_transacao
from app.config import valores_iniciais
from app.lancamentos import (
    conferir_ligacoes,
    ids_das_tags,
    recusar,
    sem_repetidas,
    tags_limpas,
    url_do_banco,
)
from app.login import UsuarioLogado
from app.recorrencias import mais_meses

router = APIRouter(prefix="/api")

# 35 anos de prestações da casa; o limite só protege a geração de um número sem sentido.
MAXIMO_DE_PARCELAS = valores_iniciais()["maximoDeParcelas"]


class DadosDoParcelamento(BaseModel):
    id: UUID
    # Compra ou dívida: as parcelas são despesas. Não é gravado: a receita parcelada, se vier,
    # ganha a coluna.
    tipo: Literal["despesa"] = "despesa"
    parcelas: int = Field(ge=2, le=MAXIMO_DE_PARCELAS)
    # No cartão, a data da compra, a mesma em todas as parcelas; fora dele, a da 1ª parcela.
    data: date
    descricao: str = ""
    # O cartão ou a conta de onde sai o boleto.
    conta_id: UUID
    categoria_ids: list[UUID] = Field(min_length=1)
    tags: list[str] = []
    # O id de uma pessoa do casal, que as parcelas herdam; sem ela, é do conjunto.
    pessoa: str | None = None

    _tags = field_validator("tags")(tags_limpas)
    _categorias = field_validator("categoria_ids")(sem_repetidas)


class NovoParcelamento(DadosDoParcelamento):
    # O total (compra sem juros) ou o da parcela (com juros); os centavos que sobram da divisão
    # do total vão na 1ª parcela.
    valor_total_centavos: int | None = Field(default=None, gt=0)
    valor_da_parcela_centavos: int | None = Field(default=None, gt=0)
    # Sem o campo, o do cartão nasce automático e o boleto pede confirmação de cada parcela.
    automatico: bool | None = None

    @model_validator(mode="after")
    def _um_valor(self):
        if (self.valor_total_centavos is None) == (self.valor_da_parcela_centavos is None):
            raise ValueError("informe o valor total ou o da parcela, um dos dois")
        if self.valor_total_centavos is not None and self.valor_total_centavos < self.parcelas:
            raise ValueError("o total não chega a um centavo por parcela")
        return self

    @property
    def total(self) -> int:
        return self.valor_total_centavos or self.valor_da_parcela_centavos * self.parcelas


class Parcelamento(DadosDoParcelamento):
    valor_total_centavos: int
    # A parcela vira realizada sozinha na data, sem confirmação.
    automatico: bool
    criado_por: str
    criado_em: datetime
    alterado_por: str
    alterado_em: datetime


_COLUNAS = (
    "id, valor_total_centavos, parcelas, data, automatico, descricao, conta_id, pessoa,"
    " criado_por, criado_em, alterado_por, alterado_em"
)
_NOMES_DAS_COLUNAS = _COLUNAS.replace(" ", "").split(",")


def valor_da_parcela(total: int, parcelas: int, n: int) -> int:
    """O total dividido por igual; os centavos que sobram vão na 1ª."""
    return total // parcelas + (total % parcelas if n == 1 else 0)


def realiza_em(conn, conta_id: UUID, parcela: int, mes: date, data: date) -> date:
    """O dia em que a parcela automática vira realizada. No cartão, a parcela n > 1 entra na
    fatura aberta quando a fatura de antes fecha (a importada, sem datas, já está fechada, e
    a que ainda não nasceu fecha no dia padrão); a 1ª e a do boleto, na data."""
    cartao = faturas.ler_cartao(conn, conta_id)
    if cartao is None or parcela == 1:
        return data
    anterior = faturas.somar_meses(mes, -1)
    gravada = conn.execute(
        "SELECT fechamento FROM faturas WHERE cartao_id = %s AND mes = %s",
        (cartao.titular.id, anterior),
    ).fetchone()
    fechamento = gravada[0] if gravada else faturas.datas_padrao(cartao.titular, anterior)[0]
    return fechamento or data


def _ler(conn, filtro: str = "", parametros: tuple = ()) -> list[Parcelamento]:
    linhas = conn.execute(
        f"SELECT {_COLUNAS} FROM parcelamentos {'WHERE ' + filtro if filtro else ''}"
        " ORDER BY data DESC, descricao, id",
        parametros,
    ).fetchall()
    ids = [linha[0] for linha in linhas]
    categorias: dict[UUID, list[UUID]] = {}
    for parcelamento_id, categoria_id in conn.execute(
        "SELECT parcelamento_id, categoria_id FROM parcelamento_categorias"
        " WHERE parcelamento_id = ANY(%s) ORDER BY categoria_id",
        (ids,),
    ):
        categorias.setdefault(parcelamento_id, []).append(categoria_id)
    tags: dict[UUID, list[str]] = {}
    for parcelamento_id, nome in conn.execute(
        "SELECT pt.parcelamento_id, t.nome FROM parcelamento_tags pt"
        " JOIN tags t ON t.id = pt.tag_id WHERE pt.parcelamento_id = ANY(%s) ORDER BY t.nome",
        (ids,),
    ):
        tags.setdefault(parcelamento_id, []).append(nome)
    return [
        Parcelamento(
            **dict(zip(_NOMES_DAS_COLUNAS, linha)),
            categoria_ids=categorias.get(linha[0], []),
            tags=tags.get(linha[0], []),
        )
        for linha in linhas
    ]


def _gerar_um_lote(conn, id: UUID) -> bool:
    """Grava as próximas parcelas, quantas cabem numa transação, e devolve se pode faltar
    alguma. O id de cada parcela vem do parcelamento e do número dela: gerar de novo não
    duplica."""
    [regra] = _ler(conn, "id = %s", (id,))
    (geradas,) = conn.execute("SELECT geradas FROM parcelamentos WHERE id = %s", (id,)).fetchone()
    categorias = regra.categoria_ids
    tags = [
        tag
        for (tag,) in conn.execute(
            "SELECT tag_id FROM parcelamento_tags WHERE parcelamento_id = %s", (id,)
        )
    ]
    no_cartao = faturas.ler_cartao(conn, regra.conta_id) is not None
    # O DSQL aceita até 3.000 linhas por transação; no cartão, cada parcela pode criar a fatura.
    por_lote = max(1, LINHAS_POR_LOTE // (2 + len(categorias) + len(tags)))
    proximas = range(geradas + 1, min(regra.parcelas, geradas + por_lote) + 1)
    if not proximas:
        return False
    dia_de_hoje = lancamentos.hoje()
    for n in proximas:
        lancamento_id = uuid5(id, str(n))
        dia = regra.data if no_cartao else mais_meses(regra.data, n - 1)
        mes = lancamentos.mes_em_que_conta(conn, regra.conta_id, dia, n)
        # A parcela automática que já chegou nasce realizada; o resto, prevista.
        situacao = (
            "realizado"
            if regra.automatico and realiza_em(conn, regra.conta_id, n, mes, dia) <= dia_de_hoje
            else "previsto"
        )
        gravado = conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, descricao,"
            " conta_id, criado_por, alterado_por, versao, parcelamento_id, parcela, automatico,"
            " pessoa, fonte, mes)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s, 'app', %s)"
            " ON CONFLICT (id) DO NOTHING",
            (
                lancamento_id,
                regra.tipo,
                situacao,
                valor_da_parcela(regra.valor_total_centavos, regra.parcelas, n),
                dia,
                regra.descricao,
                regra.conta_id,
                regra.alterado_por,
                regra.alterado_por,
                id,
                n,
                regra.automatico,
                regra.pessoa,
                mes,
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
    if not conn.execute(
        "UPDATE parcelamentos SET geradas = %s WHERE id = %s AND geradas = %s",
        (proximas[-1], id, geradas),
    ).rowcount:
        # Outra geração andou junto: a transação recomeça e parte do que ela gravou.
        raise psycopg.errors.SerializationFailure("o parcelamento mudou durante a geração")
    return proximas[-1] < regra.parcelas


def gerar_as_parcelas(url: str | None, id: UUID) -> None:
    """Gera, em lotes de uma transação cada, as parcelas que faltam. Se parar no meio, o reenvio
    ou a tarefa diária continuam de onde parou."""
    while em_transacao(url, lambda conn: _gerar_um_lote(conn, id)):
        pass


def completar_todos(url: str | None) -> int:
    """Gera as parcelas que faltam nos parcelamentos cuja geração parou no meio; devolve
    quantos completou."""
    with conectar(url) as conn:
        ids = [
            id for (id,) in conn.execute("SELECT id FROM parcelamentos WHERE geradas < parcelas")
        ]
    for id in ids:
        gerar_as_parcelas(url, id)
    return len(ids)


def origem(descricao: str) -> str:
    """Como a tela de conflito nomeia a regra que mudou o lançamento ("O da regra ...")."""
    return f"o parcelamento {descricao}".strip()


def gravar(conn, novo: NovoParcelamento, usuario: str) -> tuple[Parcelamento, bool]:
    """Grava o parcelamento sem as parcelas (`gerar_as_parcelas` as gera depois) e devolve se é
    novo. Reenviar o mesmo id (a fila repete) devolve o gravado."""
    if ja := _ler(conn, "id = %s", (novo.id,)):
        return ja[0], False
    conferir_ligacoes(conn, novo)
    no_cartao = faturas.ler_cartao(conn, novo.conta_id) is not None
    if no_cartao and novo.automatico is False:
        raise recusar("o parcelamento no cartão é automático")
    # A fatura da 1ª parcela (no cartão sem dia de fechamento, não há como escolher) é
    # conferida antes de gravar: senão a regra ficaria sem parcelas, e a tarefa diária
    # tentaria gerá-las todo dia.
    lancamentos.mes_em_que_conta(conn, novo.conta_id, novo.data)
    tags = ids_das_tags(conn, novo.tags, usuario, set())
    gravado = conn.execute(
        f"INSERT INTO parcelamentos ({_COLUNAS}, geradas)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now(), %s, now(), 0)"
        # Dois reenvios ao mesmo tempo: o segundo fica com o que o primeiro gravou.
        " ON CONFLICT (id) DO NOTHING",
        (
            novo.id,
            novo.total,
            novo.parcelas,
            novo.data,
            no_cartao or bool(novo.automatico),
            novo.descricao,
            novo.conta_id,
            novo.pessoa,
            usuario,
            usuario,
        ),
    ).rowcount
    if not gravado:
        return _ler(conn, "id = %s", (novo.id,))[0], False
    for categoria in novo.categoria_ids:
        conn.execute(
            "INSERT INTO parcelamento_categorias (parcelamento_id, categoria_id) VALUES (%s, %s)",
            (novo.id, categoria),
        )
    for tag in tags:
        conn.execute(
            "INSERT INTO parcelamento_tags (parcelamento_id, tag_id) VALUES (%s, %s)",
            (novo.id, tag),
        )
    return _ler(conn, "id = %s", (novo.id,))[0], True


def criar(url: str | None, novo: NovoParcelamento, usuario: str) -> tuple[Parcelamento, bool]:
    """Grava o parcelamento e gera as parcelas; serve à rota e ao lote da fila."""
    criado, gravado = em_transacao(url, lambda conn: gravar(conn, novo, usuario))
    gerar_as_parcelas(url, novo.id)
    return criado, gravado


@router.post(
    "/parcelamentos",
    status_code=201,
    response_model=Parcelamento,
    operation_id="criar_parcelamento",
)
def criar_parcelamento(
    novo: NovoParcelamento, usuario: UsuarioLogado, request: Request, response: Response
) -> Parcelamento:
    """Grava o parcelamento e gera todas as parcelas. Reenviar o mesmo id (a fila repete)
    devolve o gravado, com 200, e completa a geração se ela tiver parado no meio."""
    criado, gravado = criar(url_do_banco(request), novo, usuario)
    response.status_code = 201 if gravado else 200
    return criado


@router.get(
    "/parcelamentos", response_model=list[Parcelamento], operation_id="listar_parcelamentos"
)
def listar_parcelamentos(usuario: UsuarioLogado, request: Request) -> list[Parcelamento]:
    with conectar(url_do_banco(request)) as conn:
        return _ler(conn)
