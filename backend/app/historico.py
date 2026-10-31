"""A leitura da aba Histórico: uma métrica por vez (despesas, receitas, sobra ou uma categoria)
em 12 meses contra os 12 anteriores, por ano desde o primeiro lançamento e no mesmo mês de cada
ano. Conta só o realizado e pelo mês em que o lançamento conta (ADR 0003), até o mês atual."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app import lancamentos
from app.banco import conectar
from app.lancamentos import MES_EM_QUE_CONTA, VALOR_COM_SINAL, url_do_banco
from app.login import UsuarioLogado
from app.recorrencias import mais_meses

router = APIRouter(prefix="/api")

Metrica = Literal["despesas", "receitas", "sobra", "categoria"]


class MesDaSerie(BaseModel):
    mes: str
    centavos: int
    # O mesmo mês, um ano antes.
    anterior_centavos: int


class AnoDaSerie(BaseModel):
    ano: int
    centavos: int
    # O ano corrente, que ainda não acabou.
    parcial: bool


class AnoDoMesmoMes(BaseModel):
    ano: int
    centavos: int


class MesmoMesEmCadaAno(BaseModel):
    mes_do_ano: int
    anos: list[AnoDoMesmoMes]


class Historico(BaseModel):
    """Tudo o que a aba Histórico mostra de uma métrica, numa leitura só. A despesa leva os
    ajustes de fatura e o estorno diminui; a categoria conta o lançamento inteiro e não leva o
    ajuste (ADR 0008); a sobra são as receitas menos as despesas."""

    metrica: Metrica
    categoria_id: UUID | None
    # Os 12 meses que terminam no atual, do mais antigo ao mais novo, cada um contra o mesmo mês do
    # ano anterior (os 12 meses anteriores a eles).
    doze_meses: list[MesDaSerie]
    total_centavos: int
    total_anterior_centavos: int
    # Do ano do primeiro lançamento ao corrente.
    por_ano: list[AnoDaSerie]
    mesmo_mes: MesmoMesEmCadaAno


_DO_REALIZADO = (
    f"FROM lancamentos WHERE lancamentos.excluido_em IS NULL"
    f" AND lancamentos.situacao = 'realizado' AND {MES_EM_QUE_CONTA} <= %s"
)
_VALOR = f"CASE WHEN lancamentos.tipo = 'receita' THEN lancamentos.valor_centavos ELSE {VALOR_COM_SINAL} END"


def _somar(conn, sql: str, parametros: tuple) -> dict[date, int]:
    return {mes: centavos for mes, centavos in conn.execute(sql, parametros)}


def _despesas(conn, ate: date) -> dict[date, int]:
    por_mes = _somar(
        conn,
        f"SELECT {MES_EM_QUE_CONTA}, SUM({VALOR_COM_SINAL})::bigint {_DO_REALIZADO}"
        f" AND lancamentos.tipo = 'despesa' GROUP BY 1",
        (ate,),
    )
    for mes, ajuste in conn.execute(
        "SELECT mes, COALESCE(SUM(ajuste_centavos), 0)::bigint FROM faturas WHERE mes <= %s GROUP BY mes",
        (ate,),
    ):
        por_mes[mes] = por_mes.get(mes, 0) + ajuste
    return por_mes


def _receitas(conn, ate: date) -> dict[date, int]:
    return _somar(
        conn,
        f"SELECT {MES_EM_QUE_CONTA}, SUM(lancamentos.valor_centavos)::bigint {_DO_REALIZADO}"
        f" AND lancamentos.tipo = 'receita' GROUP BY 1",
        (ate,),
    )


def _da_categoria(conn, categoria_id: UUID, ate: date) -> dict[date, int]:
    return _somar(
        conn,
        f"SELECT {MES_EM_QUE_CONTA}, SUM({_VALOR})::bigint {_DO_REALIZADO}"
        f" AND EXISTS (SELECT FROM lancamento_categorias lc WHERE lc.lancamento_id = lancamentos.id"
        f" AND lc.categoria_id = %s) GROUP BY 1",
        (ate, categoria_id),
    )


def _serie(conn, metrica: Metrica, categoria_id: UUID | None, ate: date) -> dict[date, int]:
    """O valor da métrica em cada mês até `ate` (os meses sem lançamento ficam de fora)."""
    if metrica == "despesas":
        return _despesas(conn, ate)
    if metrica == "receitas":
        return _receitas(conn, ate)
    if metrica == "categoria":
        assert categoria_id
        return _da_categoria(conn, categoria_id, ate)
    despesas = _despesas(conn, ate)
    sobra = {mes: -centavos for mes, centavos in despesas.items()}
    for mes, centavos in _receitas(conn, ate).items():
        sobra[mes] = sobra.get(mes, 0) + centavos
    return sobra


def _ler_historico(
    conn, metrica: Metrica, categoria_id: UUID | None, mes_do_ano: int | None
) -> Historico:
    atual = lancamentos.hoje().replace(day=1)
    (primeiro,) = conn.execute(
        f"SELECT MIN({MES_EM_QUE_CONTA}) FROM lancamentos WHERE excluido_em IS NULL"
    ).fetchone()
    primeiro_ano = min(primeiro.year, atual.year) if primeiro else atual.year
    serie = _serie(conn, metrica, categoria_id, atual)

    meses = [mais_meses(atual, -n) for n in range(11, -1, -1)]
    doze = [
        MesDaSerie(
            mes=mes.strftime("%Y-%m"),
            centavos=serie.get(mes, 0),
            anterior_centavos=serie.get(mais_meses(mes, -12), 0),
        )
        for mes in meses
    ]
    por_ano = {ano: 0 for ano in range(primeiro_ano, atual.year + 1)}
    for mes, centavos in serie.items():
        por_ano[mes.year] = por_ano.get(mes.year, 0) + centavos
    mes_pedido = mes_do_ano or atual.month
    return Historico(
        metrica=metrica,
        categoria_id=categoria_id,
        doze_meses=doze,
        total_centavos=sum(m.centavos for m in doze),
        total_anterior_centavos=sum(m.anterior_centavos for m in doze),
        por_ano=[
            AnoDaSerie(ano=ano, centavos=centavos, parcial=ano == atual.year)
            for ano, centavos in sorted(por_ano.items())
        ],
        mesmo_mes=MesmoMesEmCadaAno(
            mes_do_ano=mes_pedido,
            anos=[
                AnoDoMesmoMes(ano=ano, centavos=serie.get(date(ano, mes_pedido, 1), 0))
                for ano in sorted(por_ano)
            ],
        ),
    )


@router.get("/historico", response_model=Historico, operation_id="ler_historico")
def ler_historico(
    usuario: UsuarioLogado,
    request: Request,
    metrica: Metrica,
    categoria_id: UUID | None = None,
    mes_do_ano: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> Historico:
    if (metrica == "categoria") != (categoria_id is not None):
        raise HTTPException(422, "categoria_id vai só com a métrica 'categoria', e ela o exige")
    with conectar(url_do_banco(request)) as conn:
        if (
            categoria_id
            and not conn.execute(
                "SELECT 1 FROM categorias WHERE id = %s", (categoria_id,)
            ).fetchone()
        ):
            raise HTTPException(404, "categoria não encontrada")
        return _ler_historico(conn, metrica, categoria_id, mes_do_ano)
