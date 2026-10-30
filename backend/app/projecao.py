"""A leitura da aba Futuro: a projeção de saldo, a soma das contas no fim de cada mês."""

from datetime import date

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import cartoes, faturas, lancamentos, planejamento
from app.banco import conectar
from app.lancamentos import url_do_banco
from app.login import UsuarioLogado

router = APIRouter(prefix="/api")

MESES_A_FRENTE = 12
MESES_PARA_TRAS = 12


class MesDoPassado(BaseModel):
    mes: date
    # A soma das contas no fim do mês, só com os realizados. Cada conta entra a partir da data de
    # abertura dela; nula quando nenhuma estava aberta, porque o histórico importado não tem saldo
    # (ADR 0007).
    saldo_centavos: int | None


class MesDaProjecao(BaseModel):
    mes: date
    # Receitas menos despesas previstas nas contas que caem no mês.
    previstos_centavos: int
    # O que falta pagar das faturas do mês (ADR 0003); no mês atual, também o das anteriores.
    faturas_centavos: int
    # O saldo no fim do mês com os previstos e as faturas.
    so_previstos_centavos: int
    # O que ainda falta lançar do planejamento de despesas do mês.
    planejamento_centavos: int
    # O saldo no fim do mês descontando também o que falta do planejamento até ele.
    com_planejamento_centavos: int


class Futuro(BaseModel):
    hoje: date
    saldo_hoje_centavos: int
    passado: list[MesDoPassado]
    proximos_meses: list[MesDaProjecao]


# O efeito de cada realizado no saldo de cada conta, com a data. A transferência sai de uma e
# entra na outra; a que vai para um cartão (pagamento de fatura) só sai.
_REALIZADOS_NAS_CONTAS = f"""
    SELECT l.conta_id, l.data, {lancamentos.VALOR_NA_CONTA} FROM lancamentos l
    WHERE l.situacao = 'realizado' AND l.excluido_em IS NULL
    UNION ALL
    SELECT t.conta_destino_id, t.data, t.valor_centavos FROM transferencias t
    WHERE t.situacao = 'realizado'
    UNION ALL
    SELECT t.conta_origem_id, t.data, -t.valor_centavos FROM transferencias t
    WHERE t.situacao = 'realizado'
"""


def _passado(conn, mes_atual: date, contas: list[lancamentos.Conta]) -> list[MesDoPassado]:
    """O saldo no fim de cada mês que passou: o de cada conta hoje menos o que se realizou nela
    depois daquele dia, só das contas já abertas nele."""
    primeiro = faturas.somar_meses(mes_atual, -MESES_PARA_TRAS)
    efeito: dict[tuple, int] = {
        (conta, mes): soma
        for conta, mes, soma in conn.execute(
            "SELECT r.conta_id, date_trunc('month', r.data)::date, SUM(r.valor)::bigint"
            f" FROM ({_REALIZADOS_NAS_CONTAS}) AS r(conta_id, data, valor)"
            " WHERE r.data >= %s GROUP BY 1, 2",
            (faturas.somar_meses(primeiro, 1),),
        )
    }
    # O saldo de cada conta no fim do mês da vez, andando de hoje para trás.
    saldo = {
        c.id: c.saldo_centavos
        - sum(v for (conta, mes), v in efeito.items() if conta == c.id and mes >= mes_atual)
        for c in contas
    }
    passado = []
    for n in range(1, MESES_PARA_TRAS + 1):
        mes = faturas.somar_meses(mes_atual, -n)
        seguinte = faturas.somar_meses(mes, 1)
        abertas = [c.id for c in contas if not c.data_abertura or c.data_abertura < seguinte]
        soma = sum(saldo[id] for id in abertas) if abertas else None
        passado.append(MesDoPassado(mes=mes, saldo_centavos=soma))
        for c in contas:
            saldo[c.id] -= efeito.get((c.id, mes), 0)
    return passado[::-1]


def _previstos_por_mes(conn, mes_atual: date) -> dict[date, int]:
    """Receitas menos despesas previstas nas contas, pelo mês da data; o atrasado conta no mês
    atual, até ser confirmado ou excluído."""
    return dict(
        conn.execute(
            "SELECT GREATEST(date_trunc('month', l.data)::date, %s),"
            f" SUM({lancamentos.VALOR_NA_CONTA})::bigint FROM lancamentos l JOIN contas c ON c.id = l.conta_id"
            " WHERE l.situacao = 'previsto' AND l.excluido_em IS NULL GROUP BY 1",
            (mes_atual,),
        ).fetchall()
    )


def _faturas_por_mes(conn, mes_atual: date) -> dict[date, int]:
    """O que falta pagar de cada fatura, no mês dela (a compra no cartão conta no mês da fatura,
    ADR 0003); o que falta das faturas de meses que passaram sai no mês atual. O saldo anterior
    já está na fatura de onde veio e não conta de novo."""
    por_mes: dict[date, int] = {}
    for titular in cartoes.titulares(conn):
        for f in cartoes.faturas_do_titular(conn, titular):
            mes = max(f.mes, mes_atual)
            por_mes[mes] = por_mes.get(mes, 0) + f.a_pagar_centavos - f.saldo_anterior_centavos
    return por_mes


@router.get("/futuro", response_model=Futuro, operation_id="ler_futuro")
def ler_futuro(usuario: UsuarioLogado, request: Request) -> Futuro:
    hoje = lancamentos.hoje()
    mes_atual = faturas.mes_de(hoje)
    with conectar(url_do_banco(request)) as conn:
        contas = lancamentos.contas_com_saldo(conn)
        saldo_hoje = sum(c.saldo_centavos for c in contas)
        passado = _passado(conn, mes_atual, contas)
        previstos = _previstos_por_mes(conn, mes_atual)
        das_faturas = _faturas_por_mes(conn, mes_atual)
        meses = [faturas.somar_meses(mes_atual, n) for n in range(MESES_A_FRENTE)]
        a_lancar = {mes: planejamento.a_lancar_nas_despesas(conn, mes) for mes in meses}
    proximos, so_previstos, com_planejamento = [], saldo_hoje, saldo_hoje
    for mes in meses:
        variacao = previstos.get(mes, 0) - das_faturas.get(mes, 0)
        so_previstos += variacao
        com_planejamento += variacao - a_lancar[mes]
        proximos.append(
            MesDaProjecao(
                mes=mes,
                previstos_centavos=previstos.get(mes, 0),
                faturas_centavos=das_faturas.get(mes, 0),
                so_previstos_centavos=so_previstos,
                planejamento_centavos=a_lancar[mes],
                com_planejamento_centavos=com_planejamento,
            )
        )
    return Futuro(
        hoje=hoje, saldo_hoje_centavos=saldo_hoje, passado=passado, proximos_meses=proximos
    )
