"""Cartões e faturas. As regras de em que fatura cai a compra ficam em `app.faturas`; aqui
ficam o cadastro, a edição das datas de uma fatura e a redistribuição das compras quando as
datas mudam (fatura fechada nunca muda, ADR 0003)."""

from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from app import faturas, lancamentos
from app.banco import conectar, em_transacao
from app.lancamentos import recusar, url_do_banco
from app.login import UsuarioLogado

router = APIRouter(prefix="/api")


class NovoCartao(BaseModel):
    """O titular tem os dias padrão, a regra do mês e o limite; o adicional (`titular_id`) usa
    os do titular e as compras dele caem na fatura do titular."""

    nome: str = Field(min_length=1)
    # Opcionais para o cartão inativo do histórico; sem eles, a compra precisa escolher a fatura.
    dia_fechamento: int | None = Field(default=None, ge=1, le=31)
    dia_vencimento: int | None = Field(default=None, ge=1, le=31)
    limite_centavos: int | None = Field(default=None, gt=0)
    mes_anterior_ao_fechamento: bool = False
    titular_id: UUID | None = None

    @model_validator(mode="after")
    def _do_titular_ou_do_adicional(self):
        if self.titular_id and (
            self.dia_fechamento
            or self.dia_vencimento
            or self.limite_centavos
            or self.mes_anterior_ao_fechamento
        ):
            raise ValueError("o adicional usa os dias, a regra e o limite do titular")
        if self.dia_vencimento and not self.dia_fechamento:
            raise ValueError("vencimento padrão sem fechamento padrão")
        return self


class EdicaoDeCartao(NovoCartao):
    # Sem o campo, o cartão fica como está: renomear não desarquiva.
    arquivado: bool | None = None


class Cartao(NovoCartao):
    id: UUID
    arquivado: bool


class Fatura(BaseModel):
    cartao_id: UUID
    # Mês da fatura, gravado como o primeiro dia dele.
    mes: date
    fechamento: date | None
    vencimento: date | None
    # Fechada a partir do dia do fechamento; a importada, sem datas, nasce fechada.
    situacao: Literal["aberta", "fechada"]


class AlteracaoDeFatura(BaseModel):
    """Fechamento ou vencimento que escorregou (feriado); o mês da fatura não muda."""

    fechamento: date | None = None
    vencimento: date | None = None


_COLUNAS = (
    "id, nome, dia_fechamento, dia_vencimento, limite_centavos, mes_anterior_ao_fechamento,"
    " titular_id, arquivado_em IS NOT NULL"
)
_NOMES = [
    "id",
    "nome",
    "dia_fechamento",
    "dia_vencimento",
    "limite_centavos",
    "mes_anterior_ao_fechamento",
    "titular_id",
    "arquivado",
]


def _ler(conn, id: UUID) -> Cartao:
    return Cartao(
        **dict(
            zip(
                _NOMES,
                conn.execute(f"SELECT {_COLUNAS} FROM cartoes WHERE id = %s", (id,)).fetchone(),
            )
        )
    )


def _conferir_titular(conn, titular_id: UUID | None) -> None:
    if titular_id is None:
        return
    titular = conn.execute(
        "SELECT titular_id, arquivado_em FROM cartoes WHERE id = %s", (titular_id,)
    ).fetchone()
    if not titular:
        raise recusar("titular não encontrado")
    if titular[0]:
        raise recusar("o titular é um cartão adicional")
    if titular[1]:
        raise recusar("titular arquivado")


@router.post("/cartoes", status_code=201, response_model=Cartao, operation_id="criar_cartao")
def criar_cartao(novo: NovoCartao, usuario: UsuarioLogado, request: Request) -> Cartao:
    id = uuid4()

    def gravar(conn) -> Cartao:
        _conferir_titular(conn, novo.titular_id)
        conn.execute(
            "INSERT INTO cartoes (id, nome, dia_fechamento, dia_vencimento, limite_centavos,"
            " mes_anterior_ao_fechamento, titular_id, criado_por)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                id,
                novo.nome,
                novo.dia_fechamento,
                novo.dia_vencimento,
                novo.limite_centavos,
                novo.mes_anterior_ao_fechamento,
                novo.titular_id,
                usuario,
            ),
        )
        return _ler(conn, id)

    return em_transacao(url_do_banco(request), gravar)


@router.put("/cartoes/{id}", response_model=Cartao, operation_id="editar_cartao")
def editar_cartao(
    id: UUID, editado: EdicaoDeCartao, usuario: UsuarioLogado, request: Request
) -> Cartao:
    """Arquivar tira o cartão das opções e mantém o histórico. Mudar o dia padrão ou a regra do
    mês vale só para as faturas abertas e futuras, e redistribui as compras delas."""

    def gravar(conn) -> Cartao:
        atual = conn.execute(
            "SELECT titular_id, arquivado_em, dia_fechamento, dia_vencimento,"
            " mes_anterior_ao_fechamento FROM cartoes WHERE id = %s",
            (id,),
        ).fetchone()
        if not atual:
            raise HTTPException(status_code=404, detail="cartão não encontrado")
        if editado.titular_id != atual[0]:
            raise recusar("o titular de um cartão não muda")
        padrao = (
            editado.dia_fechamento,
            editado.dia_vencimento,
            editado.mes_anterior_ao_fechamento,
        )
        # Reenviar arquivado=true mantém a data em que foi arquivado.
        arquivado = editado.arquivado if editado.arquivado is not None else bool(atual[1])
        arquivado_em = (atual[1] or datetime.now(UTC)) if arquivado else None
        conn.execute(
            "UPDATE cartoes SET nome = %s, dia_fechamento = %s, dia_vencimento = %s,"
            " limite_centavos = %s, mes_anterior_ao_fechamento = %s, arquivado_em = %s"
            " WHERE id = %s",
            (
                editado.nome,
                editado.dia_fechamento,
                editado.dia_vencimento,
                editado.limite_centavos,
                editado.mes_anterior_ao_fechamento,
                arquivado_em,
                id,
            ),
        )
        # Sem dia de fechamento, as faturas que já existem ficam com as datas que têm.
        if padrao != tuple(atual[2:]) and editado.dia_fechamento:
            _novo_padrao(conn, faturas.ler_cartao(conn, id).titular, usuario)
        return _ler(conn, id)

    return em_transacao(url_do_banco(request), gravar)


@router.get("/cartoes", response_model=list[Cartao], operation_id="listar_cartoes")
def listar_cartoes(
    usuario: UsuarioLogado, request: Request, arquivados: bool = False
) -> list[Cartao]:
    """Os arquivados só vêm com `arquivados=true`."""
    filtro = "" if arquivados else "WHERE arquivado_em IS NULL "
    with conectar(url_do_banco(request)) as conn:
        linhas = conn.execute(f"SELECT {_COLUNAS} FROM cartoes {filtro}ORDER BY nome, id")
        return [Cartao(**dict(zip(_NOMES, linha))) for linha in linhas]


def _faturas(conn, titular_id: UUID, mes: date | None = None) -> list[Fatura]:
    filtro, parametros = ("AND mes = %s", (mes,)) if mes else ("", ())
    dia = lancamentos.hoje()
    return [
        Fatura(
            cartao_id=cartao_id,
            mes=mes,
            fechamento=fechamento,
            vencimento=vencimento,
            situacao="aberta" if fechamento and fechamento > dia else "fechada",
        )
        for cartao_id, mes, fechamento, vencimento in conn.execute(
            "SELECT cartao_id, mes, fechamento, vencimento FROM faturas WHERE cartao_id = %s"
            f" {filtro} ORDER BY mes",
            (titular_id, *parametros),
        )
    ]


def _cartao(conn, id: UUID) -> faturas.Cartao:
    cartao = faturas.ler_cartao(conn, id)
    if not cartao:
        raise HTTPException(status_code=404, detail="cartão não encontrado")
    return cartao


@router.get("/cartoes/{id}/faturas", response_model=list[Fatura], operation_id="listar_faturas")
def listar_faturas(id: UUID, usuario: UsuarioLogado, request: Request) -> list[Fatura]:
    """As faturas que já nasceram, da mais antiga à mais nova. As do adicional são as do
    titular."""
    with conectar(url_do_banco(request)) as conn:
        return _faturas(conn, _cartao(conn, id).titular.id)


def _abertas(conn, titular: faturas.Titular) -> list[date]:
    """Os meses das faturas abertas e futuras: as que ainda não fecharam."""
    return [
        mes
        for (mes,) in conn.execute(
            "SELECT mes FROM faturas WHERE cartao_id = %s AND fechamento > %s ORDER BY mes",
            (titular.id, lancamentos.hoje()),
        )
    ]


def _novo_padrao(conn, titular: faturas.Titular, usuario: str) -> None:
    """As faturas abertas e futuras passam a ter as datas do novo padrão; a fechada nunca muda."""
    abertas = _abertas(conn, titular)
    for mes in abertas:
        conn.execute(
            "UPDATE faturas SET fechamento = %s, vencimento = %s WHERE cartao_id = %s AND mes = %s",
            (*faturas.datas_padrao(titular, mes), titular.id, mes),
        )
    _redistribuir(conn, titular, abertas, usuario)


def _redistribuir(conn, titular: faturas.Titular, meses: list[date], usuario: str) -> None:
    """Escolhe de novo a fatura das compras desses meses, salvo as trocadas à mão. A compra
    que muda de fatura conta como mudança do app, com a origem, para a tela de conflito
    (ADR 0011). Sem dia de fechamento no cartão, toda compra já teve a fatura escolhida."""
    if titular.dia_fechamento is None:
        return
    compras = conn.execute(
        "SELECT l.id, l.data, l.mes, COALESCE(l.versao, 1) FROM lancamentos l"
        " JOIN cartoes c ON c.id = l.conta_id"
        " WHERE COALESCE(c.titular_id, c.id) = %s AND l.mes = ANY(%s)"
        " AND l.excluido_em IS NULL AND NOT COALESCE(l.fatura_a_mao, false)",
        (titular.id, meses),
    ).fetchall()
    for id, data, mes, versao in compras:
        nova = faturas.mes_da_compra(conn, titular, data)
        if nova == mes:
            continue
        faturas.garantir_fatura(conn, titular, nova)
        versao = lancamentos.subir_versao(
            conn, id, versao, "mes = %s, alterado_por = %s, alterado_em = now()", (nova, usuario)
        )
        lancamentos.registrar_mudancas(
            conn, id, ["fatura_mes"], versao, usuario, origem=f"datas do cartão {titular.nome}"
        )


@router.patch("/cartoes/{id}/faturas/{mes}", response_model=Fatura, operation_id="editar_fatura")
def editar_fatura(
    id: UUID, mes: date, alteracao: AlteracaoDeFatura, usuario: UsuarioLogado, request: Request
) -> Fatura:
    """Acerta o fechamento ou o vencimento de uma fatura (a que ainda não nasceu nasce aqui) e
    redistribui as compras dela e das abertas e futuras; o mês da fatura não muda."""
    mes = faturas.mes_de(mes)

    def gravar(conn) -> Fatura:
        titular = _cartao(conn, id).titular
        abertas = _abertas(conn, titular)
        faturas.garantir_fatura(conn, titular, mes)
        fechamento, vencimento = conn.execute(
            "SELECT fechamento, vencimento FROM faturas WHERE cartao_id = %s AND mes = %s",
            (titular.id, mes),
        ).fetchone()
        fechamento = alteracao.fechamento or fechamento
        vencimento = alteracao.vencimento or vencimento
        if fechamento and vencimento and vencimento <= fechamento:
            raise recusar("vencimento antes do fechamento")
        conn.execute(
            "UPDATE faturas SET fechamento = %s, vencimento = %s WHERE cartao_id = %s AND mes = %s",
            (fechamento, vencimento, titular.id, mes),
        )
        _redistribuir(conn, titular, sorted({*abertas, mes}), usuario)
        return _faturas(conn, titular.id, mes)[0]

    return em_transacao(url_do_banco(request), gravar)
