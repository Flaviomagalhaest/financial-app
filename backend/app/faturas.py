"""Em que fatura cai uma compra no cartão e em que mês ela conta (ADR 0003).

Cada cartão titular tem uma fatura por mês da fatura, criada quando a primeira compra precisa
dela, com fechamento e vencimento que nascem dos dias padrão do cartão e podem ser editados. O
cartão adicional não tem fatura: as compras dele caem na do titular.
"""

import calendar
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from fastapi import HTTPException


@dataclass(frozen=True)
class Titular:
    """O cartão que tem as faturas: o próprio cartão, ou o titular de um adicional."""

    id: UUID
    nome: str
    dia_fechamento: int | None
    dia_vencimento: int | None
    # A fatura conta no mês anterior ao do fechamento (cartões que fecham no começo do mês).
    mes_anterior_ao_fechamento: bool


@dataclass(frozen=True)
class CartaoComTitular:
    id: UUID
    arquivado: bool
    titular: Titular


def mes_de(dia: date) -> date:
    """O mês como o banco o grava: o primeiro dia dele."""
    return dia.replace(day=1)


def somar_meses(mes: date, n: int) -> date:
    total = mes.year * 12 + mes.month - 1 + n
    return date(total // 12, total % 12 + 1, 1)


def _no_mes(mes: date, dia: int) -> date:
    """O dia no mês; dia 31 em mês curto cai no último dia."""
    return mes.replace(day=min(dia, calendar.monthrange(mes.year, mes.month)[1]))


def _meses_ate_o_fechamento(titular: Titular) -> int:
    return 1 if titular.mes_anterior_ao_fechamento else 0


def mes_do_fechamento(titular: Titular, mes: date) -> date:
    return somar_meses(mes, _meses_ate_o_fechamento(titular))


def datas_padrao(titular: Titular, mes: date) -> tuple[date | None, date | None]:
    """Fechamento e vencimento da fatura do mês pelos dias padrão. O vencimento cai no mês do
    fechamento se vier depois dele, senão no mês seguinte (fecha 25/04, vence 05/05)."""
    if titular.dia_fechamento is None:
        return None, None
    mes_fechamento = mes_do_fechamento(titular, mes)
    fechamento = _no_mes(mes_fechamento, titular.dia_fechamento)
    if titular.dia_vencimento is None:
        return fechamento, None
    vencimento = _no_mes(mes_fechamento, titular.dia_vencimento)
    if vencimento <= fechamento:
        vencimento = _no_mes(somar_meses(mes_fechamento, 1), titular.dia_vencimento)
    return fechamento, vencimento


def ler_cartao(conn, id: UUID) -> CartaoComTitular | None:
    """O cartão com o titular das faturas; `None` se o id não é de um cartão. O adicional de
    um titular arquivado conta como arquivado."""
    linha = conn.execute(
        "SELECT c.id, c.arquivado_em IS NOT NULL OR t.arquivado_em IS NOT NULL, t.id, t.nome, t.dia_fechamento,"
        " t.dia_vencimento, t.mes_anterior_ao_fechamento"
        " FROM cartoes c JOIN cartoes t ON t.id = COALESCE(c.titular_id, c.id)"
        " WHERE c.id = %s",
        (id,),
    ).fetchone()
    if not linha:
        return None
    id, arquivado, *titular = linha
    return CartaoComTitular(id=id, arquivado=arquivado, titular=Titular(*titular))


def _gravados(conn, titular: Titular, meses: list[date]) -> dict[date, date]:
    """O fechamento das faturas que já existem nesses meses e têm data."""
    return dict(
        conn.execute(
            "SELECT mes, fechamento FROM faturas WHERE cartao_id = %s AND mes = ANY(%s)"
            " AND fechamento IS NOT NULL",
            (titular.id, meses),
        ).fetchall()
    )


def _com_padrao(
    titular: Titular, gravados: dict[date, date], meses: list[date]
) -> dict[date, date | None]:
    return {mes: gravados.get(mes) or datas_padrao(titular, mes)[0] for mes in meses}


def fechamentos(conn, titular: Titular, meses: list[date]) -> dict[date, date | None]:
    """O fechamento de cada mês: o da fatura que já existe ou, sem ela (ou sem data, como a
    importada), o padrão."""
    return _com_padrao(titular, _gravados(conn, titular, meses), meses)


def _candidatos(titular: Titular, data: date) -> list[date]:
    """Os meses em que a compra pode cair. Começa pela fatura do mês anterior, porque um
    fechamento editado pode ter escorregado para o mês da compra."""
    primeiro = somar_meses(mes_de(data), -1 - _meses_ate_o_fechamento(titular))
    return [somar_meses(primeiro, n) for n in range(4)]


def escolher_fatura(titular: Titular, gravados: dict[date, date], data: date) -> date:
    """A primeira fatura que fecha depois da data da compra, dados os fechamentos gravados:
    compra feita no próprio dia do fechamento já vai para a seguinte. O app repete a escolha no
    aviso de planejamento (`tabelas-de-teste/mes-da-compra.json`)."""
    for mes, fechamento in _com_padrao(titular, gravados, _candidatos(titular, data)).items():
        if fechamento is None:
            raise HTTPException(
                status_code=422, detail="cartão sem dia de fechamento: escolha a fatura"
            )
        if fechamento > data:
            return mes
    raise HTTPException(status_code=422, detail="nenhuma fatura fecha depois da compra")


def mes_da_compra(conn, titular: Titular, data: date) -> date:
    """A fatura em que cai a compra feita em `data` (`escolher_fatura`)."""
    gravados = _gravados(conn, titular, _candidatos(titular, data))
    return escolher_fatura(titular, gravados, data)


def mes_da_parcela(conn, titular: Titular, data: date, parcela: int | None) -> date:
    """A parcela n de um parcelamento cai n - 1 faturas depois da fatura da compra; a compra
    à vista (sem parcela) cai na da compra."""
    return somar_meses(mes_da_compra(conn, titular, data), (parcela or 1) - 1)


def aberta(fechamento: date | None, hoje: date) -> bool:
    """Fatura aberta: o fechamento ainda não chegou. A importada, sem datas, é fechada."""
    return fechamento is not None and fechamento > hoje


def importada(fechamento: date | None, vencimento: date | None) -> bool:
    """A fatura importada do Mobills não tem datas: nasce fechada e paga, sem pagamento de
    fatura (`## Answer` do ticket 18). A fatura escolhida à mão num cartão sem os dias padrão
    também nasce sem datas, e conta como paga até alguém dar as datas a ela."""
    return fechamento is None and vencimento is None


def gravar_datas(conn, titular: Titular, mes: date, fechamento, vencimento) -> None:
    conn.execute(
        "UPDATE faturas SET fechamento = %s, vencimento = %s WHERE cartao_id = %s AND mes = %s",
        (fechamento, vencimento, titular.id, mes),
    )


def garantir_fatura(conn, titular: Titular, mes: date) -> None:
    """A fatura nasce, com as datas padrão, quando a primeira compra precisa dela."""
    fechamento, vencimento = datas_padrao(titular, mes)
    conn.execute(
        "INSERT INTO faturas (cartao_id, mes, fechamento, vencimento) VALUES (%s, %s, %s, %s)"
        " ON CONFLICT (cartao_id, mes) DO NOTHING",
        (titular.id, mes, fechamento, vencimento),
    )


def ajustes_do_mes(conn, mes: date) -> int:
    """A soma dos ajustes das faturas do mês, de todos os cartões (ADR 0008)."""
    (soma,) = conn.execute(
        "SELECT COALESCE(SUM(ajuste_centavos), 0)::bigint FROM faturas WHERE mes = %s", (mes,)
    ).fetchone()
    return soma
