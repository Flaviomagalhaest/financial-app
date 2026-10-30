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
    # A soma das contas no fim do mês, só com os realizados; nula antes da abertura de alguma
    # conta, porque o histórico importado não tem saldo (ADR 0007).
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


# O efeito de cada realizado na soma das contas, com a data. A transferência entre duas contas
# entra e sai; a que vai para um cartão (pagamento de fatura) só sai.
_REALIZADOS_NAS_CONTAS = """
    SELECT l.data, CASE l.tipo WHEN 'receita' THEN l.valor_centavos ELSE -l.valor_centavos END
    FROM lancamentos l JOIN contas c ON c.id = l.conta_id
    WHERE l.situacao = 'realizado' AND l.excluido_em IS NULL
    UNION ALL
    SELECT t.data, t.valor_centavos FROM transferencias t JOIN contas c ON c.id = t.conta_destino_id
    WHERE t.situacao = 'realizado'
    UNION ALL
    SELECT t.data, -t.valor_centavos FROM transferencias t JOIN contas c ON c.id = t.conta_origem_id
    WHERE t.situacao = 'realizado'
"""


def _passado(conn, mes_atual: date, saldo_hoje: int) -> list[MesDoPassado]:
    """O saldo no fim de cada mês que passou: o de hoje menos o que se realizou depois dele."""
    primeiro = faturas.somar_meses(mes_atual, -MESES_PARA_TRAS)
    efeito = dict(
        conn.execute(
            "SELECT date_trunc('month', r.data)::date, SUM(r.valor)::bigint"
            f" FROM ({_REALIZADOS_NAS_CONTAS}) AS r(data, valor) WHERE r.data >= %s GROUP BY 1",
            (faturas.somar_meses(primeiro, 1),),
        ).fetchall()
    )
    (abertura,) = conn.execute("SELECT MAX(data_abertura) FROM contas").fetchone()
    saldo = saldo_hoje - sum(v for mes, v in efeito.items() if mes >= mes_atual)
    passado = []
    for n in range(1, MESES_PARA_TRAS + 1):
        mes = faturas.somar_meses(mes_atual, -n)
        seguinte = faturas.somar_meses(mes, 1)
        passado.append(
            MesDoPassado(
                mes=mes, saldo_centavos=None if abertura and abertura >= seguinte else saldo
            )
        )
        saldo -= efeito.get(mes, 0)
    return passado[::-1]


def _previstos_por_mes(conn, mes_atual: date) -> dict[date, int]:
    """Receitas menos despesas previstas nas contas, pelo mês da data; o atrasado conta no mês
    atual, até ser confirmado ou excluído."""
    return dict(
        conn.execute(
            "SELECT GREATEST(date_trunc('month', l.data)::date, %s),"
            " SUM(CASE l.tipo WHEN 'receita' THEN l.valor_centavos ELSE -l.valor_centavos END)"
            "::bigint FROM lancamentos l JOIN contas c ON c.id = l.conta_id"
            " WHERE l.situacao = 'previsto' AND l.excluido_em IS NULL GROUP BY 1",
            (mes_atual,),
        ).fetchall()
    )


def _faturas_por_mes(conn, mes_atual: date) -> dict[date, int]:
    """O que falta pagar de cada fatura, no mês dela (a compra no cartão conta no mês da fatura,
    ADR 0003); o que falta das faturas de meses que passaram sai no mês atual. O saldo anterior
    já está na fatura de onde veio e não conta de novo."""
    por_mes: dict[date, int] = {}
    titulares = conn.execute("SELECT id FROM cartoes WHERE titular_id IS NULL").fetchall()
    for (titular,) in titulares:
        for f in cartoes.faturas_do_titular(conn, titular):
            mes = max(f.mes, mes_atual)
            por_mes[mes] = por_mes.get(mes, 0) + f.a_pagar_centavos - f.saldo_anterior_centavos
    return por_mes


def _a_lancar_do_planejamento(conn, mes: date) -> int:
    """O que falta de cada item de despesa do planejamento do mês (o planejado menos o realizado
    e o previsto), sem compensar o item estourado com a sobra de outro, menos os ajustes de
    fatura, como o "ainda dá para gastar". O item de transferência fica de fora: guardar na
    reserva move dinheiro entre contas e não muda a soma delas."""
    plano = planejamento.ler(conn, mes.strftime("%Y-%m"))
    de_despesa = {
        id
        for (id,) in conn.execute(
            "SELECT id FROM categorias WHERE tipo = 'despesa' AND id = ANY(%s)",
            ([i.categoria_id for i in plano.itens],),
        )
    }
    falta = sum(
        max(i.ainda_da_para_gastar_centavos, 0) for i in plano.itens if i.categoria_id in de_despesa
    )
    return max(falta - plano.ajustes_de_fatura_centavos, 0)


@router.get("/futuro", response_model=Futuro, operation_id="ler_futuro")
def ler_futuro(usuario: UsuarioLogado, request: Request) -> Futuro:
    hoje = lancamentos.hoje()
    mes_atual = faturas.mes_de(hoje)
    with conectar(url_do_banco(request)) as conn:
        saldo_hoje = lancamentos.saldo_das_contas(conn)
        passado = _passado(conn, mes_atual, saldo_hoje)
        previstos = _previstos_por_mes(conn, mes_atual)
        a_pagar = _faturas_por_mes(conn, mes_atual)
        meses = [faturas.somar_meses(mes_atual, n) for n in range(MESES_A_FRENTE)]
        a_lancar = {mes: _a_lancar_do_planejamento(conn, mes) for mes in meses}
    proximos, so_previstos, com_planejamento = [], saldo_hoje, saldo_hoje
    for mes in meses:
        variacao = previstos.get(mes, 0) - a_pagar.get(mes, 0)
        so_previstos += variacao
        com_planejamento += variacao - a_lancar[mes]
        proximos.append(
            MesDaProjecao(
                mes=mes,
                previstos_centavos=previstos.get(mes, 0),
                faturas_centavos=a_pagar.get(mes, 0),
                so_previstos_centavos=so_previstos,
                planejamento_centavos=a_lancar[mes],
                com_planejamento_centavos=com_planejamento,
            )
        )
    return Futuro(
        hoje=hoje, saldo_hoje_centavos=saldo_hoje, passado=passado, proximos_meses=proximos
    )
