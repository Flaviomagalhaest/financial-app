"""Cartões e faturas. As regras de em que fatura cai a compra ficam em `app.faturas`; aqui
ficam o cadastro, a edição das datas de uma fatura e a redistribuição das compras quando as
datas mudam (fatura fechada nunca muda, ADR 0003)."""

from collections import Counter
from collections.abc import Callable
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
    # Opcionais para o cartão arquivado do histórico; sem eles, a compra escolhe a fatura.
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
    # Fechada a partir do dia do fechamento. Paga quando fechada e com um pagamento realizado, de
    # qualquer valor (ADR 0021); a importada do Mobills, sem datas, nasce paga sem pagamento.
    situacao: Literal["aberta", "fechada", "paga"]
    # As compras da fatura (despesas menos estornos e receitas, previstas e realizadas).
    compras_centavos: int
    # A diferença para o valor real da fatura (ADR 0008); pode ser negativa.
    ajuste_centavos: int
    # Compras mais o ajuste.
    total_centavos: int
    # O que faltou pagar da fatura anterior paga: não é compra e não conta de novo.
    saldo_anterior_centavos: int
    # Os pagamentos de fatura realizados desta fatura.
    pago_centavos: int
    # Saldo anterior mais o total menos o pago; zero na paga, que passou o que faltou adiante.
    a_pagar_centavos: int


class AlteracaoDeFatura(BaseModel):
    """Fechamento ou vencimento que escorregou (feriado), ou o ajuste da fatura; o mês da fatura
    não muda."""

    fechamento: date | None = None
    vencimento: date | None = None
    # Sem o campo, o ajuste fica como está; 0 desfaz.
    ajuste_centavos: int | None = Field(default=None, ge=-(10**12), le=10**12)


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

    return em_transacao(url_do_banco(request), protegida(gravar))


@router.get("/cartoes", response_model=list[Cartao], operation_id="listar_cartoes")
def listar_cartoes(
    usuario: UsuarioLogado, request: Request, arquivados: bool = False
) -> list[Cartao]:
    """Os arquivados só vêm com `arquivados=true`."""
    filtro = "" if arquivados else "WHERE arquivado_em IS NULL "
    with conectar(url_do_banco(request)) as conn:
        linhas = conn.execute(f"SELECT {_COLUNAS} FROM cartoes {filtro}ORDER BY nome, id")
        return [Cartao(**dict(zip(_NOMES, linha))) for linha in linhas]


def titulares(conn) -> list[UUID]:
    """Os cartões que têm faturas: os titulares, arquivados inclusive."""
    return [id for (id,) in conn.execute("SELECT id FROM cartoes WHERE titular_id IS NULL")]


def faturas_do_titular(
    conn, titular_id: UUID, mes: date | None = None, compras_a_mais: dict[date, int] | None = None
) -> list[Fatura]:
    """As faturas do titular, com os números. O saldo anterior de cada uma vem da anterior
    paga, por isso a conta corre desde a mais antiga, mesmo quando se pede um mês só. As
    `compras_a_mais` (com sinal, por mês) simulam compras que ainda não foram gravadas."""
    dia = lancamentos.hoje()
    compras = Counter(compras_a_mais or {})
    compras.update(
        dict(
            conn.execute(
                f"SELECT {lancamentos.MES_EM_QUE_CONTA}, SUM({lancamentos.VALOR_COM_SINAL})::bigint"
                " FROM lancamentos JOIN cartoes c ON c.id = lancamentos.conta_id"
                " WHERE COALESCE(c.titular_id, c.id) = %s AND lancamentos.excluido_em IS NULL"
                f" GROUP BY {lancamentos.MES_EM_QUE_CONTA}",
                (titular_id,),
            )
        )
    )
    pagos = {
        mes: (soma, quantos)
        for mes, soma, quantos in conn.execute(
            "SELECT t.fatura_mes, SUM(t.valor_centavos)::bigint, COUNT(*) FROM transferencias t"
            " JOIN cartoes c ON c.id = t.conta_destino_id"
            " WHERE COALESCE(c.titular_id, c.id) = %s AND t.situacao = 'realizado'"
            " GROUP BY t.fatura_mes",
            (titular_id,),
        )
    }
    resultado = []
    saldo_anterior = 0
    for cartao_id, mes_da_fatura, fechamento, vencimento, ajuste in conn.execute(
        "SELECT cartao_id, mes, fechamento, vencimento, COALESCE(ajuste_centavos, 0)"
        " FROM faturas WHERE cartao_id = %s ORDER BY mes",
        (titular_id,),
    ).fetchall():
        compras_da_fatura = compras.get(mes_da_fatura, 0)
        pago, pagamentos = pagos.get(mes_da_fatura, (0, 0))
        total = compras_da_fatura + ajuste
        devido = saldo_anterior + total
        # A importada já foi paga no Mobills, e o pagamento não veio no histórico.
        importada = faturas.importada(fechamento, vencimento)
        aberta = faturas.aberta(fechamento, dia)
        # Um pagamento realizado, de qualquer valor, deixa paga a fatura fechada (ADR 0021).
        paga = not aberta and (importada or pagamentos > 0)
        a_pagar = 0 if paga else max(devido - pago, 0)
        situacao = "aberta" if aberta else "paga" if paga else "fechada"
        if not mes or mes == mes_da_fatura:
            resultado.append(
                Fatura(
                    cartao_id=cartao_id,
                    mes=mes_da_fatura,
                    fechamento=fechamento,
                    vencimento=vencimento,
                    situacao=situacao,
                    compras_centavos=compras_da_fatura,
                    ajuste_centavos=ajuste,
                    total_centavos=total,
                    saldo_anterior_centavos=saldo_anterior,
                    pago_centavos=pago,
                    a_pagar_centavos=a_pagar,
                )
            )
        # Só a fatura paga passa o que faltou: a aberta ainda recebe compras, a fechada sem
        # pagamento continua devendo e a importada já foi paga no Mobills.
        saldo_anterior = max(devido - pago, 0) if paga and not importada else 0
    return resultado


def _todas(conn) -> dict[tuple[UUID, date], Fatura]:
    return {
        k: f for t in titulares(conn) for k, f in _por_chave(faturas_do_titular(conn, t)).items()
    }


def _o_que_so_um_evento_muda(f: Fatura) -> tuple[date | None, date | None, int, int, int]:
    """As datas, as compras, o ajuste e os pagamentos da fatura; o saldo anterior vem da
    anterior."""
    return f.fechamento, f.vencimento, f.compras_centavos, f.ajuste_centavos, f.pago_centavos


def paga_pelo_pagamento(f: Fatura) -> bool:
    """A paga que recebeu um pagamento; a importada do Mobills (sem datas) segue recebendo as
    compras escolhidas à mão."""
    return f.situacao == "paga" and not faturas.importada(f.fechamento, f.vencimento)


def recusa_da_paga(conn, cartao_id: UUID, mes: date) -> HTTPException:
    (nome,) = conn.execute("SELECT nome FROM cartoes WHERE id = %s", (cartao_id,)).fetchone()
    return recusar(
        f"a fatura de {mes:%m/%Y} do {nome} está paga: para mudá-la, use a correção da fatura"
    )


def _passa_adiante(f: Fatura) -> int:
    """O que faltou pagar da fatura paga, que vira saldo anterior da seguinte."""
    if not paga_pelo_pagamento(f):
        return 0
    return max(f.saldo_anterior_centavos + f.total_centavos - f.pago_centavos, 0)


def _garantir_a_seguinte(conn, todas: dict[tuple[UUID, date], Fatura]) -> bool:
    """O saldo anterior precisa de uma fatura seguinte: se a última fatura de um titular é paga e
    passa algo adiante, a do mês seguinte nasce aqui. Havendo uma mais adiante, o saldo pula os
    meses sem fatura até ela. Devolve se alguma nasceu."""
    ultimas: dict[UUID, Fatura] = {}
    for (titular_id, _), f in sorted(todas.items()):
        ultimas[titular_id] = f
    nasceu = False
    for titular_id, ultima in ultimas.items():
        if _passa_adiante(ultima):
            titular = faturas.ler_cartao(conn, titular_id).titular
            faturas.garantir_fatura(conn, titular, faturas.somar_meses(ultima.mes, 1))
            nasceu = True
    return nasceu


def _conferir_faturas(
    conn,
    antes: dict[tuple[UUID, date], Fatura],
    corrigida: tuple[UUID, date] | None,
) -> None:
    depois_de_tudo = _todas(conn)
    if _garantir_a_seguinte(conn, depois_de_tudo):
        depois_de_tudo = _todas(conn)
    _conferir_o_que_mudou(conn, antes, depois_de_tudo, corrigida)


def _conferir_o_que_mudou(
    conn,
    antes: dict[tuple[UUID, date], Fatura],
    depois_de_tudo: dict[tuple[UUID, date], Fatura],
    corrigida: tuple[UUID, date] | None,
) -> None:
    for chave, depois in depois_de_tudo.items():
        anterior = antes.get(chave)
        if (
            anterior
            and chave != corrigida
            and paga_pelo_pagamento(anterior)
            and _o_que_so_um_evento_muda(anterior) != _o_que_so_um_evento_muda(depois)
        ):
            raise recusa_da_paga(conn, *chave)
        # Só a fatura que mudou: a gravada antes da regra (ticket 125) não trava o resto.
        if chave == corrigida and not paga_pelo_pagamento(depois):
            raise recusar("a correção não reabre a fatura: ela continua paga")
        mudou = not anterior or anterior != depois
        devido = depois.saldo_anterior_centavos + depois.total_centavos
        if mudou and depois.pago_centavos > max(devido, 0):
            raise recusar("o pagamento passa do valor da fatura")


def protegida[T](
    trabalho: Callable[..., T], corrigida: tuple[UUID, date] | None = None
) -> Callable[..., T]:
    """`trabalho(conn)` com as regras da fatura paga (ADR 0021) conferidas no resultado: a paga
    não recebe mais pagamento, compra, troca de fatura, estorno nem acerto de datas, e nenhum
    pagamento passa do valor da fatura (saldo anterior mais o total). Só a `corrigida` (titular e
    mês, na correção de fatura) muda sendo paga, e ela continua paga. A fatura paga que é a
    última e passa saldo anterior adiante ganha a seguinte."""

    def com_as_regras(conn) -> T:
        antes = _todas(conn)
        resultado = trabalho(conn)
        _conferir_faturas(conn, antes, corrigida)
        return resultado

    return com_as_regras


def conferir_sem_gravar(conn, passos: list[dict[tuple[UUID, date], int]]) -> None:
    """As regras de `protegida` em passos ainda não gravados, cada um uma transação: as compras
    que mudam (com sinal) em cada fatura, por titular e mês. Recusa o que um dos passos
    recusaria ao gravar, antes de gravar o primeiro."""
    a_mais: dict[UUID, Counter] = {}
    antes = {
        t: _por_chave(faturas_do_titular(conn, t))
        for t in {titular for passo in passos for titular, _ in passo}
    }
    for passo in passos:
        for (titular, mes), valor in passo.items():
            a_mais.setdefault(titular, Counter())[mes] += valor
        for titular in {t for t, _ in passo}:
            depois = _por_chave(faturas_do_titular(conn, titular, compras_a_mais=a_mais[titular]))
            _conferir_o_que_mudou(conn, antes[titular], depois, None)
            antes[titular] = depois


def _por_chave(lista: list[Fatura]) -> dict[tuple[UUID, date], Fatura]:
    return {(f.cartao_id, f.mes): f for f in lista}


def faturas_que_vencem_ate(conn, ate: date) -> list[Fatura]:
    """As faturas fechadas, com saldo a pagar, que vencem até `ate` (as já vencidas inclusive), dos
    cartões titulares não arquivados, da que vence primeiro à que vence depois."""
    titulares = [
        id
        for (id,) in conn.execute(
            "SELECT id FROM cartoes WHERE titular_id IS NULL AND arquivado_em IS NULL"
        )
    ]
    que_vencem = [
        f
        for titular in titulares
        for f in faturas_do_titular(conn, titular)
        if f.situacao == "fechada"
        and f.a_pagar_centavos > 0
        and f.vencimento
        and f.vencimento <= ate
    ]
    return sorted(que_vencem, key=lambda f: (f.vencimento, f.cartao_id, f.mes))


def cartao_ou_404(conn, id: UUID) -> faturas.CartaoComTitular:
    cartao = faturas.ler_cartao(conn, id)
    if not cartao:
        raise HTTPException(status_code=404, detail="cartão não encontrado")
    return cartao


@router.get("/cartoes/{id}/faturas", response_model=list[Fatura], operation_id="listar_faturas")
def listar_faturas(id: UUID, usuario: UsuarioLogado, request: Request) -> list[Fatura]:
    """As faturas que já nasceram, da mais antiga à mais nova. As do adicional são as do
    titular."""
    with conectar(url_do_banco(request)) as conn:
        return faturas_do_titular(conn, cartao_ou_404(conn, id).titular.id)


def _abertas(conn, titular: faturas.Titular) -> list[date]:
    """Os meses das faturas abertas e futuras: as que ainda não fecharam."""
    dia = lancamentos.hoje()
    return [
        mes
        for mes, fechamento in conn.execute(
            "SELECT mes, fechamento FROM faturas WHERE cartao_id = %s ORDER BY mes", (titular.id,)
        )
        if faturas.aberta(fechamento, dia)
    ]


def _novo_padrao(conn, titular: faturas.Titular, usuario: str) -> None:
    """As faturas abertas e futuras passam a ter as datas do novo padrão; a fechada nunca muda."""
    abertas = _abertas(conn, titular)
    for mes in abertas:
        faturas.gravar_datas(conn, titular, mes, *faturas.datas_padrao(titular, mes))
    _redistribuir(conn, titular, abertas, usuario)


def _redistribuir(conn, titular: faturas.Titular, meses: list[date], usuario: str) -> None:
    """Escolhe de novo a fatura das compras desses meses, salvo as trocadas à mão; a parcela n
    fica n - 1 faturas depois da fatura da compra. A compra que muda de fatura conta como
    mudança do app, com a origem, para a tela de conflito (ADR 0011). Sem dia de fechamento no
    cartão, toda compra já teve a fatura escolhida."""
    if titular.dia_fechamento is None:
        return
    compras = conn.execute(
        "SELECT l.id, l.data, l.mes, COALESCE(l.versao, 1), l.parcela FROM lancamentos l"
        " JOIN cartoes c ON c.id = l.conta_id"
        " WHERE COALESCE(c.titular_id, c.id) = %s AND l.mes = ANY(%s)"
        " AND l.excluido_em IS NULL AND NOT COALESCE(l.fatura_a_mao, false)",
        (titular.id, meses),
    ).fetchall()
    for id, data, mes, versao, parcela in compras:
        nova = faturas.mes_da_parcela(conn, titular, data, parcela)
        if nova == mes:
            continue
        faturas.garantir_fatura(conn, titular, nova)
        lancamentos.mudar_fatura(conn, id, versao, nova, usuario, f"datas do cartão {titular.nome}")


def alterar_fatura(
    conn, titular: faturas.Titular, mes: date, alteracao: AlteracaoDeFatura, usuario: str
) -> None:
    """Grava o ajuste ou acerta as datas da fatura (a que ainda não nasceu nasce aqui) e
    redistribui as compras dela e das abertas e futuras."""
    abertas = _abertas(conn, titular)
    faturas.garantir_fatura(conn, titular, mes)
    if alteracao.ajuste_centavos is not None:
        conn.execute(
            "UPDATE faturas SET ajuste_centavos = %s WHERE cartao_id = %s AND mes = %s",
            (alteracao.ajuste_centavos, titular.id, mes),
        )
    # Só o ajuste não mexe nas datas nem nas compras da fatura.
    if not (alteracao.fechamento or alteracao.vencimento):
        return
    fechamento, vencimento = conn.execute(
        "SELECT fechamento, vencimento FROM faturas WHERE cartao_id = %s AND mes = %s",
        (titular.id, mes),
    ).fetchone()
    fechamento = alteracao.fechamento or fechamento
    vencimento = alteracao.vencimento or vencimento
    if fechamento and vencimento and vencimento <= fechamento:
        raise recusar("vencimento antes do fechamento")
    # A escolha da fatura (`faturas.mes_da_compra`) conta com fechamentos em ordem.
    anterior, seguinte = faturas.fechamentos(
        conn, titular, [faturas.somar_meses(mes, -1), faturas.somar_meses(mes, 1)]
    ).values()
    if fechamento and (
        (anterior and fechamento <= anterior) or (seguinte and fechamento >= seguinte)
    ):
        raise recusar("fechamento fora do intervalo entre a fatura anterior e a seguinte")
    faturas.gravar_datas(conn, titular, mes, fechamento, vencimento)
    _redistribuir(conn, titular, sorted({*abertas, mes}), usuario)


@router.patch("/cartoes/{id}/faturas/{mes}", response_model=Fatura, operation_id="editar_fatura")
def editar_fatura(
    id: UUID, mes: date, alteracao: AlteracaoDeFatura, usuario: UsuarioLogado, request: Request
) -> Fatura:
    """Acerta o fechamento ou o vencimento de uma fatura e redistribui as compras dela e das
    abertas e futuras, ou grava o ajuste dela (ADR 0008); o mês da fatura não muda. A fatura paga
    só muda pela correção de fatura (ADR 0021)."""
    mes = faturas.mes_de(mes)

    def gravar(conn) -> Fatura:
        titular = cartao_ou_404(conn, id).titular
        alterar_fatura(conn, titular, mes, alteracao, usuario)
        return faturas_do_titular(conn, titular.id, mes)[0]

    return em_transacao(url_do_banco(request), protegida(gravar))
