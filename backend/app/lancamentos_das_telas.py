"""Os lançamentos que as telas leem do servidor em vez de filtrar a lista guardada no aparelho
(ticket 165, ADR 0025): a fatura de um cartão, o Mês e o parcelamento. A lista guardada só tem a
janela do aparelho; estas telas precisam também dos meses antigos."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import faturas
from app.banco import conectar
from app.lancamentos import MES_EM_QUE_CONTA, Lancamento, ler_lancamentos, url_do_banco
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
        return ler_lancamentos(
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
        return ler_lancamentos(conn, f"{MES_EM_QUE_CONTA} = %s", (primeiro_dia(mes),))


@router.get(
    "/parcelamentos/{id}/lancamentos",
    response_model=list[Lancamento],
    operation_id="listar_lancamentos_do_parcelamento",
)
def listar_lancamentos_do_parcelamento(
    id: UUID, usuario: UsuarioLogado, request: Request
) -> list[Lancamento]:
    """Todas as parcelas do parcelamento, da primeira à última; 404 se ele não existe."""
    with conectar(url_do_banco(request)) as conn:
        if not conn.execute("SELECT 1 FROM parcelamentos WHERE id = %s", (id,)).fetchone():
            raise HTTPException(status_code=404, detail="parcelamento não encontrado")
        return ler_lancamentos(conn, "parcelamento_id = %s", (id,), ordem="parcela, id")


class PrimeiroMes(BaseModel):
    mes: date | None


@router.get(
    "/lancamentos-primeiro-mes",
    response_model=PrimeiroMes,
    operation_id="ler_primeiro_mes_com_lancamento",
)
def ler_primeiro_mes(usuario: UsuarioLogado, request: Request) -> PrimeiroMes:
    """O mês mais antigo em que um lançamento conta: até onde o Histórico lê do servidor, mês a
    mês, depois da janela do aparelho (ticket 167). `None` sem lançamentos."""
    with conectar(url_do_banco(request)) as conn:
        linha = conn.execute(
            f"SELECT MIN({MES_EM_QUE_CONTA}) FROM lancamentos WHERE excluido_em IS NULL"
        ).fetchone()
        return PrimeiroMes(mes=linha[0] if linha else None)
