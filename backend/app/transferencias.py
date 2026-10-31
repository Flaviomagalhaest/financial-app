"""Transferência entre duas contas do casal: não é despesa nem receita, só move o saldo.
Tabela própria porque o DSQL não altera o `CHECK` do tipo dos lançamentos (ADR 0014).

O pagamento de fatura é a transferência de uma conta para um cartão: leva o mês da fatura que
quita, não tem categoria e só mexe no saldo da conta."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from app import faturas
from app.banco import conectar, em_transacao
from app.lancamentos import conferir_conta, recusar, situacao_pela_data, url_do_banco
from app.login import UsuarioLogado

router = APIRouter(prefix="/api")


class NovaTransferencia(BaseModel):
    id: UUID
    conta_origem_id: UUID
    conta_destino_id: UUID
    valor_centavos: int = Field(gt=0)
    data: date
    descricao: str = ""
    # Opcional, e só da lista de categorias de transferência.
    categoria_id: UUID | None = None
    situacao: Literal["previsto", "realizado"] | None = None
    # Só no pagamento de fatura (destino num cartão): o mês da fatura que ele quita.
    fatura_mes: date | None = None

    @field_validator("fatura_mes")
    @classmethod
    def _primeiro_dia_do_mes(cls, mes: date | None) -> date | None:
        return mes and faturas.mes_de(mes)


class Transferencia(NovaTransferencia):
    situacao: Literal["previsto", "realizado"]
    criado_por: str
    criado_em: datetime
    alterado_por: str
    alterado_em: datetime


_COLUNAS = (
    "id, conta_origem_id, conta_destino_id, valor_centavos, data, descricao, categoria_id,"
    " situacao, fatura_mes, criado_por, criado_em, alterado_por, alterado_em"
)

_NOMES_DAS_COLUNAS = _COLUNAS.replace(" ", "").split(",")


def _ler_transferencias(conn, id: UUID | None = None) -> list[Transferencia]:
    return _ler(conn, *(("WHERE id = %s", (id,)) if id else ("", ())))


def ler_por_ids(conn, ids: list[UUID]) -> list[Transferencia]:
    return _ler(conn, "WHERE id = ANY(%s)", (ids,))


def _ler(conn, filtro: str, parametros: tuple) -> list[Transferencia]:
    linhas = conn.execute(
        f"SELECT {_COLUNAS} FROM transferencias {filtro} ORDER BY data DESC, criado_em DESC, id",
        parametros,
    ).fetchall()
    return [Transferencia(**dict(zip(_NOMES_DAS_COLUNAS, linha))) for linha in linhas]


def _conferir_transferencia(
    conn, t: NovaTransferencia, atual: tuple[UUID, UUID] | None = None
) -> None:
    if t.conta_origem_id == t.conta_destino_id:
        raise recusar("origem e destino são a mesma conta")
    # Arquivada só segue com quem já estava nela (o histórico se edita).
    conferir_conta(conn, t.conta_origem_id, ja_ligada=bool(atual) and t.conta_origem_id == atual[0])
    ja_no_destino = bool(atual) and t.conta_destino_id == atual[1]
    if cartao := faturas.ler_cartao(conn, t.conta_destino_id):
        _conferir_pagamento_de_fatura(conn, t, cartao, ja_no_destino)
    else:
        conferir_conta(conn, t.conta_destino_id, ja_ligada=ja_no_destino)
        if t.fatura_mes:
            raise recusar("fatura só no pagamento de fatura, com o destino num cartão")
    if t.categoria_id:
        tipo = conn.execute(
            "SELECT tipo FROM categorias WHERE id = %s", (t.categoria_id,)
        ).fetchone()
        if not tipo:
            raise recusar("categoria não encontrada")
        if tipo[0] != "transferencia":
            raise recusar(f"categoria de {tipo[0]} numa transferência")


def _conferir_pagamento_de_fatura(
    conn, t: NovaTransferencia, cartao: faturas.CartaoComTitular, ja_no_destino: bool
) -> None:
    if cartao.arquivado and not ja_no_destino:
        raise recusar("cartão arquivado")
    if t.categoria_id:
        raise recusar("pagamento de fatura não tem categoria")
    if not t.fatura_mes:
        raise recusar("pagamento de fatura precisa do mês da fatura")
    existe = conn.execute(
        "SELECT 1 FROM faturas WHERE cartao_id = %s AND mes = %s", (cartao.titular.id, t.fatura_mes)
    ).fetchone()
    if not existe:
        raise recusar("fatura não encontrada")


@router.post(
    "/transferencias",
    status_code=201,
    response_model=Transferencia,
    operation_id="criar_transferencia",
)
def criar_transferencia(
    nova: NovaTransferencia, usuario: UsuarioLogado, request: Request, response: Response
) -> Transferencia:
    """Reenviar o mesmo id (a fila repete) devolve o que já está gravado, com 200."""

    def gravar(conn) -> Transferencia:
        _conferir_transferencia(conn, nova)
        gravadas = conn.execute(
            "INSERT INTO transferencias (id, conta_origem_id, conta_destino_id, valor_centavos,"
            " data, descricao, categoria_id, situacao, fatura_mes, criado_por, alterado_por)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (
                nova.id,
                nova.conta_origem_id,
                nova.conta_destino_id,
                nova.valor_centavos,
                nova.data,
                nova.descricao,
                nova.categoria_id,
                nova.situacao or situacao_pela_data(nova.data),
                nova.fatura_mes,
                usuario,
                usuario,
            ),
        ).rowcount
        # O 200 vale para a tentativa que terminou: refeita, `gravadas` é lido de novo.
        response.status_code = 201 if gravadas else 200
        return _ler_transferencias(conn, nova.id)[0]

    return em_transacao(url_do_banco(request), gravar)


@router.get(
    "/transferencias", response_model=list[Transferencia], operation_id="listar_transferencias"
)
def listar_transferencias(usuario: UsuarioLogado, request: Request) -> list[Transferencia]:
    with conectar(url_do_banco(request)) as conn:
        return _ler_transferencias(conn)


@router.put(
    "/transferencias/{id}", response_model=Transferencia, operation_id="editar_transferencia"
)
def editar_transferencia(
    id: UUID, editada: NovaTransferencia, usuario: UsuarioLogado, request: Request
) -> Transferencia:
    if editada.id != id:
        raise recusar("o id do corpo difere do id da URL")

    def gravar(conn) -> Transferencia:
        atual = conn.execute(
            "SELECT data, situacao, conta_origem_id, conta_destino_id FROM transferencias"
            " WHERE id = %s",
            (id,),
        ).fetchone()
        if not atual:
            raise HTTPException(status_code=404, detail="transferência não encontrada")
        data_atual, situacao_atual, origem, destino = atual
        _conferir_transferencia(conn, editada, (origem, destino))
        # Como no lançamento: sem situação no pedido, só mudar a data refaz a inferência.
        if editada.situacao:
            situacao = editada.situacao
        elif editada.data != data_atual:
            situacao = situacao_pela_data(editada.data)
        else:
            situacao = situacao_atual
        conn.execute(
            "UPDATE transferencias SET conta_origem_id = %s, conta_destino_id = %s,"
            " valor_centavos = %s, data = %s, descricao = %s, categoria_id = %s, situacao = %s,"
            " fatura_mes = %s, alterado_por = %s, alterado_em = now() WHERE id = %s",
            (
                editada.conta_origem_id,
                editada.conta_destino_id,
                editada.valor_centavos,
                editada.data,
                editada.descricao,
                editada.categoria_id,
                situacao,
                editada.fatura_mes,
                usuario,
                id,
            ),
        )
        return _ler_transferencias(conn, id)[0]

    return em_transacao(url_do_banco(request), gravar)


@router.delete("/transferencias/{id}", status_code=204, operation_id="excluir_transferencia")
def excluir_transferencia(id: UUID, usuario: UsuarioLogado, request: Request) -> Response:
    """Idempotente: excluir o que já não existe também dá 204."""
    em_transacao(
        url_do_banco(request),
        lambda conn: conn.execute("DELETE FROM transferencias WHERE id = %s", (id,)),
    )
    return Response(status_code=204)
