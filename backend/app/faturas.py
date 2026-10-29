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


def fechamentos(conn, titular: Titular, meses: list[date]) -> dict[date, date | None]:
    """O fechamento de cada mês: o da fatura que já existe ou, sem ela (ou sem data, como a
    importada), o padrão."""
    gravados = dict(
        conn.execute(
            "SELECT mes, fechamento FROM faturas WHERE cartao_id = %s AND mes = ANY(%s)"
            " AND fechamento IS NOT NULL",
            (titular.id, meses),
        ).fetchall()
    )
    return {mes: gravados.get(mes) or datas_padrao(titular, mes)[0] for mes in meses}


def mes_da_compra(conn, titular: Titular, data: date) -> date:
    """A primeira fatura que fecha depois da data da compra: compra feita no próprio dia do
    fechamento já vai para a seguinte. Começa pela fatura do mês anterior, porque um
    fechamento editado pode ter escorregado para o mês da compra."""
    primeiro = somar_meses(mes_de(data), -1 - _meses_ate_o_fechamento(titular))
    meses = [somar_meses(primeiro, n) for n in range(4)]
    for mes, fechamento in fechamentos(conn, titular, meses).items():
        if fechamento is None:
            raise HTTPException(
                status_code=422, detail="cartão sem dia de fechamento: escolha a fatura"
            )
        if fechamento > data:
            return mes
    raise HTTPException(status_code=422, detail="nenhuma fatura fecha depois da compra")


def mes_da_parcela(conn, titular: Titular, data: date, parcela: int | None) -> date:
    """A parcela n de uma compra parcelada cai n - 1 faturas depois da fatura da compra; a
    compra à vista (sem parcela) cai na da compra."""
    return somar_meses(mes_da_compra(conn, titular, data), (parcela or 1) - 1)


def aberta(fechamento: date | None, hoje: date) -> bool:
    """Fatura aberta: o fechamento ainda não chegou. A importada, sem datas, é fechada."""
    return fechamento is not None and fechamento > hoje


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
