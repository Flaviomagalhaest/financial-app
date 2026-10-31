"""Transferência entre duas contas do casal: não é despesa nem receita, só move o saldo.
Tabela própria porque o DSQL não altera o `CHECK` do tipo dos lançamentos (ADR 0014).

O pagamento de fatura é a transferência de uma conta para um cartão: leva o mês da fatura que
quita, não tem categoria e só mexe no saldo da conta."""

from datetime import date, datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from app import cartoes, faturas, lancamentos
from app.banco import conectar, em_transacao
from app.config import valores_iniciais
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
    # Previsto com data antes de hoje (São Paulo), a mesma regra do lançamento.
    atrasado: bool = False


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
    dia = lancamentos.hoje()
    return [_montar(dict(zip(_NOMES_DAS_COLUNAS, linha)), dia) for linha in linhas]


def _montar(campos: dict, dia: date) -> Transferencia:
    atrasado = campos["situacao"] == "previsto" and campos["data"] < dia
    return Transferencia(**campos, atrasado=atrasado)


def contas_da_semana_de_hoje(conn) -> list[Transferencia]:
    """Os previstos atrasados e os até `contasDaSemanaDias` dias a partir de hoje, como nos
    lançamentos; o pagamento de fatura previsto entra também."""
    ate = lancamentos.hoje() + timedelta(days=valores_iniciais()["contasDaSemanaDias"])
    previstas = _ler(conn, "WHERE situacao = 'previsto' AND data <= %s", (ate,))
    return sorted(previstas, key=lambda t: (t.data, t.criado_em, t.id))


def _conferir_transferencia(
    conn, t: NovaTransferencia, atual: tuple[UUID, UUID, date | None] | None = None
) -> None:
    if t.conta_origem_id == t.conta_destino_id:
        raise recusar("origem e destino são a mesma conta")
    # Arquivada só segue com quem já estava nela (o histórico se edita).
    conferir_conta(conn, t.conta_origem_id, ja_ligada=bool(atual) and t.conta_origem_id == atual[0])
    ja_no_destino = bool(atual) and t.conta_destino_id == atual[1]
    if cartao := faturas.ler_cartao(conn, t.conta_destino_id):
        ja_na_fatura = ja_no_destino and t.fatura_mes == atual[2]
        _conferir_pagamento_de_fatura(conn, t, cartao, ja_no_destino, ja_na_fatura)
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
    conn,
    t: NovaTransferencia,
    cartao: faturas.CartaoComTitular,
    ja_no_destino: bool,
    ja_na_fatura: bool,
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
    # A fatura paga não recebe pagamento novo, nem o previsto (ADR 0021).
    if not ja_na_fatura:
        [fatura] = cartoes.faturas_do_titular(conn, cartao.titular.id, t.fatura_mes)
        if cartoes.paga_pelo_pagamento(fatura):
            raise cartoes.recusa_da_paga(conn, cartao.titular.id, t.fatura_mes)


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

    return em_transacao(url_do_banco(request), cartoes.protegida(gravar))


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
            "SELECT data, situacao, conta_origem_id, conta_destino_id, fatura_mes"
            " FROM transferencias WHERE id = %s",
            (id,),
        ).fetchone()
        if not atual:
            raise HTTPException(status_code=404, detail="transferência não encontrada")
        data_atual, situacao_atual, origem, destino, fatura_mes = atual
        _conferir_transferencia(conn, editada, (origem, destino, fatura_mes))
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

    return em_transacao(url_do_banco(request), cartoes.protegida(gravar))


class ConfirmacaoDeTransferencia(BaseModel):
    """O que de fato aconteceu; campo ausente fica como estava no previsto."""

    valor_centavos: int | None = Field(default=None, gt=0)
    data: date | None = None


@router.post(
    "/transferencias/{id}/confirmar",
    response_model=Transferencia,
    operation_id="confirmar_transferencia",
    responses={409: {"description": "Já confirmada com outros valores"}},
)
def confirmar_transferencia(
    id: UUID, confirmacao: ConfirmacaoDeTransferencia, usuario: UsuarioLogado, request: Request
) -> Transferencia:
    """Como no lançamento: confirmar de novo sem ajuste diferente devolve o gravado; com ajuste
    diferente de uma já realizada é 409, para nada se perder em silêncio."""

    def gravar(conn) -> Transferencia:
        atual = next(iter(_ler_transferencias(conn, id)), None)
        if not atual:
            raise HTTPException(status_code=404, detail="transferência não encontrada")
        ajustes = {
            campo: pedido
            for campo, pedido in confirmacao.model_dump(exclude_none=True).items()
            if pedido != getattr(atual, campo)
        }
        if atual.situacao == "realizado":
            if ajustes:
                raise HTTPException(
                    status_code=409,
                    detail=f"já confirmada com outros valores ({', '.join(sorted(ajustes))})",
                )
            return atual
        conn.execute(
            "UPDATE transferencias SET situacao = 'realizado',"
            " valor_centavos = COALESCE(%s, valor_centavos), data = COALESCE(%s, data),"
            " alterado_por = %s, alterado_em = now() WHERE id = %s",
            (confirmacao.valor_centavos, confirmacao.data, usuario, id),
        )
        return _ler_transferencias(conn, id)[0]

    return em_transacao(url_do_banco(request), cartoes.protegida(gravar))


@router.delete("/transferencias/{id}", status_code=204, operation_id="excluir_transferencia")
def excluir_transferencia(id: UUID, usuario: UsuarioLogado, request: Request) -> Response:
    """Idempotente: excluir o que já não existe também dá 204."""
    em_transacao(
        url_do_banco(request),
        cartoes.protegida(
            lambda conn: conn.execute("DELETE FROM transferencias WHERE id = %s", (id,))
        ),
    )
    return Response(status_code=204)
