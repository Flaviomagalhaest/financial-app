"""O que um mês gastou, para as telas do mês e do fechamento. Despesa conta pelo mês em que o
lançamento conta (no cartão, o da fatura, ADR 0003); o estorno diminui; o ajuste de fatura entra
nas despesas do mês, mas não em categoria nem em tag (ADR 0008)."""

from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import faturas
from app.banco import conectar
from app.lancamentos import GASTO_NO_CARTAO, MES_EM_QUE_CONTA, url_do_banco
from app.login import UsuarioLogado
from app.planejamento import Mes, primeiro_dia

router = APIRouter(prefix="/api")


class TotalDeCategoria(BaseModel):
    categoria_id: UUID
    centavos: int


class TotalDeTag(BaseModel):
    tag: str
    centavos: int


class TotaisDoMes(BaseModel):
    mes: str
    # As compras (menos os estornos) e os ajustes de fatura do mês; transferência e pagamento de
    # fatura não entram.
    despesas_centavos: int
    # A parte das despesas que é ajuste de fatura, sem categoria nem tag.
    ajustes_de_fatura_centavos: int
    por_categoria: list[TotalDeCategoria]
    por_tag: list[TotalDeTag]


# Despesa do mês: a que não foi excluída, no mês em que conta. A receita fica de fora.
_DESPESAS_DO_MES = (
    f"FROM lancamentos WHERE lancamentos.excluido_em IS NULL AND lancamentos.tipo = 'despesa'"
    f" AND {MES_EM_QUE_CONTA} = %s"
)


def _totais(conn, mes: str) -> TotaisDoMes:
    dia = primeiro_dia(mes)
    (compras,) = conn.execute(
        f"SELECT COALESCE(SUM({GASTO_NO_CARTAO}), 0)::bigint {_DESPESAS_DO_MES}", (dia,)
    ).fetchone()
    ajustes = faturas.ajustes_do_mes(conn, dia)
    por_categoria = conn.execute(
        f"SELECT lc.categoria_id, SUM({GASTO_NO_CARTAO})::bigint AS centavos"
        f" FROM lancamento_categorias lc JOIN lancamentos ON lancamentos.id = lc.lancamento_id"
        f" WHERE lancamentos.excluido_em IS NULL AND lancamentos.tipo = 'despesa'"
        f" AND {MES_EM_QUE_CONTA} = %s GROUP BY lc.categoria_id"
        f" ORDER BY centavos DESC, lc.categoria_id",
        (dia,),
    ).fetchall()
    por_tag = conn.execute(
        f"SELECT t.nome, SUM({GASTO_NO_CARTAO})::bigint AS centavos"
        f" FROM lancamento_tags lt JOIN lancamentos ON lancamentos.id = lt.lancamento_id"
        f" JOIN tags t ON t.id = lt.tag_id"
        f" WHERE lancamentos.excluido_em IS NULL AND lancamentos.tipo = 'despesa'"
        f" AND {MES_EM_QUE_CONTA} = %s GROUP BY t.nome ORDER BY centavos DESC, t.nome",
        (dia,),
    ).fetchall()
    return TotaisDoMes(
        mes=mes,
        despesas_centavos=compras + ajustes,
        ajustes_de_fatura_centavos=ajustes,
        por_categoria=[TotalDeCategoria(categoria_id=c, centavos=v) for c, v in por_categoria],
        por_tag=[TotalDeTag(tag=t, centavos=v) for t, v in por_tag],
    )


@router.get("/meses/{mes}/totais", response_model=TotaisDoMes, operation_id="ler_totais_do_mes")
def ler_totais(mes: Mes, usuario: UsuarioLogado, request: Request) -> TotaisDoMes:
    with conectar(url_do_banco(request)) as conn:
        return _totais(conn, mes)
