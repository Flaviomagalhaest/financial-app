"""Limite comprometido e disponível do cartão (ticket 23, decidido com o dono): o que as compras
da fatura aberta, as faturas fechadas ainda não pagas e as parcelas futuras ocupam do limite."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import cartoes, faturas, lancamentos
from app.banco import conectar
from app.lancamentos import url_do_banco
from app.login import UsuarioLogado

router = APIRouter(prefix="/api")

MESES_DA_LISTA = 12


class ParcelamentoEmAndamento(BaseModel):
    id: UUID
    descricao: str
    # Quantas parcelas o parcelamento tem e quantas ainda não entraram na fatura aberta.
    parcelas: int
    parcelas_restantes: int
    restante_centavos: int
    # O mês da fatura da última parcela.
    fim_previsto: date


class MesDoLimite(BaseModel):
    """Quanto do comprometido se libera quando as faturas que vencem no mês forem pagas."""

    mes: date
    # A fatura aberta ou fechada que vence no mês.
    fatura_centavos: int
    # As parcelas futuras que estão nas faturas que vencem no mês.
    parcelas_centavos: int
    libera_centavos: int


class LimiteDoCartao(BaseModel):
    """Sem `limite_centavos` o cartão não mostra limite, mas o comprometido continua a conta."""

    limite_centavos: int | None
    # As compras realizadas das faturas ainda não fechadas, com o ajuste delas.
    fatura_aberta_centavos: int
    # O que falta pagar das faturas fechadas, com o saldo anterior.
    faturas_fechadas_centavos: int
    # As parcelas previstas dos parcelamentos; a recorrência prevista não conta.
    parcelas_futuras_centavos: int
    comprometido_centavos: int
    disponivel_centavos: int | None
    parcelamentos: list[ParcelamentoEmAndamento]
    proximos_meses: list[MesDoLimite]


def _indice_do_mes(hoje: date, vencimento: date) -> int:
    """A posição do mês do vencimento na lista; o vencimento que passou libera no mês de hoje."""
    return max(0, (vencimento.year - hoje.year) * 12 + vencimento.month - hoje.month)


@router.get("/cartoes/{id}/limite", response_model=LimiteDoCartao, operation_id="ler_limite")
def ler_limite(id: UUID, usuario: UsuarioLogado, request: Request) -> LimiteDoCartao:
    """O limite do titular, com as compras do adicional dentro do comprometido."""
    with conectar(url_do_banco(request)) as conn:
        titular = cartoes._cartao(conn, id).titular
        hoje = lancamentos.hoje()
        todas = cartoes._faturas(conn, titular.id)
        abertas = [f.mes for f in todas if f.situacao == "aberta"]
        fechadas = [f for f in todas if f.situacao != "aberta"]
        limite = conn.execute(
            "SELECT limite_centavos FROM cartoes WHERE id = %s", (titular.id,)
        ).fetchone()[0]
        no_cartao = (
            " FROM lancamentos JOIN cartoes c ON c.id = lancamentos.conta_id"
            " WHERE COALESCE(c.titular_id, c.id) = %s AND lancamentos.excluido_em IS NULL"
            f" AND {lancamentos.MES_EM_QUE_CONTA} = ANY(%s)"
        )
        realizado, futuras = {}, {}
        for mes, situacao, soma in conn.execute(
            f"SELECT {lancamentos.MES_EM_QUE_CONTA}, situacao,"
            f" SUM({lancamentos.VALOR_COM_SINAL})::bigint {no_cartao}"
            " AND (situacao = 'realizado' OR parcelamento_id IS NOT NULL) GROUP BY 1, 2",
            (titular.id, abertas),
        ):
            if situacao == "realizado":
                realizado[mes] = soma
            else:
                futuras[mes] = soma
        andamento = [
            ParcelamentoEmAndamento(
                id=id,
                descricao=descricao,
                parcelas=parcelas,
                parcelas_restantes=restantes,
                restante_centavos=restante,
                fim_previsto=fim,
            )
            for id, descricao, parcelas, restantes, restante, fim in conn.execute(
                "SELECT p.id, p.descricao, p.parcelas, COUNT(*), SUM(l.valor_centavos)::bigint,"
                " MAX(COALESCE(l.mes, date_trunc('month', l.data)::date))"
                " FROM lancamentos l JOIN parcelamentos p ON p.id = l.parcelamento_id"
                " JOIN cartoes c ON c.id = l.conta_id"
                " WHERE COALESCE(c.titular_id, c.id) = %s AND l.excluido_em IS NULL"
                " AND l.situacao = 'previsto' AND l.tipo = 'despesa' AND l.estorno_de IS NULL"
                " AND COALESCE(l.mes, date_trunc('month', l.data)::date) = ANY(%s)"
                " GROUP BY p.id, p.descricao, p.parcelas ORDER BY MAX(l.data), p.descricao, p.id",
                (titular.id, abertas),
            )
        ]

        ajuste = {f.mes: f.ajuste_centavos for f in todas}
        vencimentos = {f.mes: f.vencimento or f.mes for f in todas}
        meses = [faturas.somar_meses(faturas.mes_de(hoje), n) for n in range(MESES_DA_LISTA)]
        fatura_do_mes = dict.fromkeys(range(MESES_DA_LISTA), 0)
        parcelas_do_mes = dict.fromkeys(range(MESES_DA_LISTA), 0)

        def cair(lista: dict[int, int], vencimento: date, valor: int) -> None:
            if (n := _indice_do_mes(hoje, vencimento)) < MESES_DA_LISTA:
                lista[n] += valor

        # O que sobra de uma fatura fechada passa para a seguinte: a última leva tudo.
        fechadas_centavos = fechadas[-1].a_pagar_centavos if fechadas else 0
        if fechadas:
            cair(fatura_do_mes, vencimentos[fechadas[-1].mes], fechadas_centavos)
        for mes in abertas:
            aberta = realizado.get(mes, 0) + ajuste[mes]
            cair(fatura_do_mes, vencimentos[mes], aberta)
            cair(parcelas_do_mes, vencimentos[mes], futuras.get(mes, 0))
        aberta_centavos = sum(realizado.get(m, 0) + ajuste[m] for m in abertas)
        parcelas_centavos = sum(futuras.values())
        comprometido = aberta_centavos + fechadas_centavos + parcelas_centavos
        return LimiteDoCartao(
            limite_centavos=limite,
            fatura_aberta_centavos=aberta_centavos,
            faturas_fechadas_centavos=fechadas_centavos,
            parcelas_futuras_centavos=parcelas_centavos,
            comprometido_centavos=comprometido,
            disponivel_centavos=None if limite is None else limite - comprometido,
            parcelamentos=andamento,
            proximos_meses=[
                MesDoLimite(
                    mes=mes,
                    fatura_centavos=fatura_do_mes[n],
                    parcelas_centavos=parcelas_do_mes[n],
                    libera_centavos=fatura_do_mes[n] + parcelas_do_mes[n],
                )
                for n, mes in enumerate(meses)
            ],
        )
