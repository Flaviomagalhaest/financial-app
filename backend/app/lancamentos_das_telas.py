"""Os lançamentos que as telas leem do servidor em vez de filtrar a lista guardada no aparelho
(ticket 165, ADR 0025): a fatura de um cartão, o Mês e o parcelamento. A lista guardada só tem a
janela do aparelho; estas telas precisam também dos meses antigos."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Request

from app import faturas
from app.banco import conectar
from app.lancamentos import MES_EM_QUE_CONTA, Lancamento, _todos, url_do_banco
from app.login import UsuarioLogado
from app.planejamento import Mes, primeiro_dia

router = APIRouter(prefix="/api")


@router.get(
    "/cartoes/{id}/faturas/{mes}/lancamentos",
    response_model=list[Lancamento],
    operation_id="listar_lancamentos_da_fatura",
)
def listar_lancamentos_da_fatura(
    id: UUID, mes: date, usuario: UsuarioLogado, request: Request
) -> list[Lancamento]:
    """As compras que contam na fatura `mes` do cartão, com as dos adicionais dele."""
    with conectar(url_do_banco(request)) as conn:
        return _todos(
            conn,
            f"{MES_EM_QUE_CONTA} = %s AND conta_id IN (SELECT id FROM cartoes WHERE %s IN (id, titular_id))",
            (faturas.mes_de(mes), id),
        )


@router.get(
    "/meses/{mes}/lancamentos",
    response_model=list[Lancamento],
    operation_id="listar_lancamentos_do_mes",
)
def listar_lancamentos_do_mes(
    mes: Mes, usuario: UsuarioLogado, request: Request
) -> list[Lancamento]:
    """Os lançamentos que contam no mês: no cartão, o da fatura; no resto, o da data (ADR 0003)."""
    with conectar(url_do_banco(request)) as conn:
        return _todos(conn, f"{MES_EM_QUE_CONTA} = %s", (primeiro_dia(mes),))


@router.get(
    "/parcelamentos/{id}/lancamentos",
    response_model=list[Lancamento],
    operation_id="listar_lancamentos_do_parcelamento",
)
def listar_lancamentos_do_parcelamento(
    id: UUID, usuario: UsuarioLogado, request: Request
) -> list[Lancamento]:
    """Todas as parcelas do parcelamento, da primeira à última."""
    with conectar(url_do_banco(request)) as conn:
        return _todos(conn, "parcelamento_id = %s", (id,), ordem="parcela, id")
