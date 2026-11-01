"""Alcance da mudança na parcela (ticket 136): mudar um campo de uma parcela só nela, nela e nas
próximas, ou em todas, inclusive as já realizadas.

"Só esta" é a edição comum do lançamento e deixa a parcela alterada à mão no campo. Os outros
dois mudam o parcelamento e precisam de internet, como a correção dele (ADR 0011): a descrição,
as categorias, as tags, a pessoa e o item vão para o parcelamento, a partir da parcela mudada ou
desde a 1ª, e em "todas" o valor e a data viram a correção do valor da parcela e da data. O que o
parcelamento não sabe guardar (o valor e a data só daqui para frente, a conta e a fatura) vai
parcela a parcela, como mudança à mão em cada uma. As parcelas que uma pessoa mudou só nelas
ficam como estão nesses campos, e a resposta diz quantas ficaram assim."""

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Literal
from uuid import UUID

import psycopg
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import cartoes, faturas, lancamentos, parcelamentos
from app.banco import conectar, em_transacao
from app.lancamentos import (
    AlteracaoDeLancamento,
    ConflitoDeCampos,
    Exclusao,
    Lancamento,
    LancamentoExcluido,
    LancamentoNaoEncontrado,
    editar,
    iguais,
    recusar,
    url_do_banco,
)
from app.login import UsuarioLogado
from app.parcelamentos import (
    CLASSIFICACAO,
    AlteracaoDeParcelamento,
    AvisoDeRealizadas,
    ParcelaQueMuda,
    RealizadasMudam,
)
from app.recorrencias import mais_meses

router = APIRouter(prefix="/api")

Alcance = Literal["so_esta", "esta_e_as_proximas", "todas"]


class AlteracaoDaParcela(AlteracaoDeLancamento):
    """A edição da parcela, com o alcance. Se uma realizada que não é esta mudar de valor, data,
    conta ou fatura, o pedido só vale com `confirmar_realizadas`."""

    alcance: Alcance
    confirmar_realizadas: bool = False


class MudancaDaParcela(BaseModel):
    # A parcela mudada, como ficou.
    lancamento: Lancamento
    # Quantas das outras parcelas do alcance ficaram como estavam em algum campo pedido, porque
    # uma pessoa o mudou só nelas.
    parcelas_mantidas: int


@dataclass
class _Mudanca:
    """O que falta depois da transação da parcela mudada."""

    parcelamento_id: UUID
    # Se ficou parte parcela a parcela por fazer, gravada no parcelamento (`mudanca_pendente`).
    falta_por_parcela: bool = False
    # A classificação que a correção gravou no parcelamento, para refazer nas parcelas.
    classificacao: dict[str, int] | None = None
    mantidas: set[int] = field(default_factory=set)


# O que vai parcela a parcela, conforme o alcance.
_POR_PARCELA = {
    "esta_e_as_proximas": {"valor_centavos", "data", "conta_id", "fatura_mes"},
    "todas": {"conta_id", "fatura_mes"},
}


# Como ler de volta cada campo que vai parcela a parcela.
_TIPOS = {
    "valor_centavos": int,
    "data": date.fromisoformat,
    "conta_id": UUID,
    "fatura_mes": date.fromisoformat,
}


@dataclass
class _PorParcela:
    """A parte da mudança que vai parcela a parcela, guardada no parcelamento até a última
    parcela mudar (ticket 145): se o pedido cair no meio, a tarefa diária termina com ela."""

    # A parcela mudada: o id, o número e a fatura de antes (a das outras se desloca igual).
    editada: UUID
    parcela: int
    mes: date
    no_cartao: bool
    # Os campos pedidos e o valor de cada um na parcela mudada.
    valores: dict
    # A parcela a partir da qual ainda falta mudar; anda a cada lote.
    desde: int
    usuario: str

    def gravar(self) -> str:
        return json.dumps(
            {
                "editada": str(self.editada),
                "parcela": self.parcela,
                "mes": self.mes.isoformat(),
                "no_cartao": self.no_cartao,
                "valores": {c: str(v) for c, v in self.valores.items()},
                "desde": self.desde,
                "usuario": self.usuario,
            },
            sort_keys=True,
        )

    @classmethod
    def ler(cls, texto: str | None) -> "_PorParcela | None":
        if not texto:
            return None
        lido = json.loads(texto)
        return cls(
            editada=UUID(lido["editada"]),
            parcela=lido["parcela"],
            mes=date.fromisoformat(lido["mes"]),
            no_cartao=lido["no_cartao"],
            valores={c: _TIPOS[c](v) for c, v in lido["valores"].items()},
            desde=lido["desde"],
            usuario=lido["usuario"],
        )


def _pedidas(alteracao: AlteracaoDaParcela) -> dict:
    pedidas = alteracao.model_dump(
        exclude={"versao", "acao_em", "alcance", "confirmar_realizadas"}, exclude_none=True
    )
    if "pessoa" in pedidas:
        pedidas["pessoa"] = pedidas["pessoa"] or None
    return pedidas


def _valores_na_outra(pendente: _PorParcela, outra: Lancamento) -> dict:
    """O que a mudança da parcela editada dá numa outra parcela: o mesmo valor e a mesma conta, a
    data no mesmo dia (no boleto, um mês a mais por parcela) e a fatura deslocada igual."""
    mudou = pendente.valores
    valores = {}
    if "valor_centavos" in mudou:
        valores["valor_centavos"] = mudou["valor_centavos"]
    if "data" in mudou:
        valores["data"] = (
            mudou["data"]
            if pendente.no_cartao
            else mais_meses(mudou["data"], outra.parcela - pendente.parcela)
        )
    if "conta_id" in mudou:
        valores["conta_id"] = mudou["conta_id"]
    if "fatura_mes" in mudou and outra.fatura_mes:
        deslocamento = (mudou["fatura_mes"].year - pendente.mes.year) * 12 + (
            mudou["fatura_mes"].month - pendente.mes.month
        )
        valores["fatura_mes"] = faturas.somar_meses(outra.mes, deslocamento)
    return valores


def _falta(
    conn, parcelamento_id: UUID, pendente: _PorParcela
) -> tuple[list[tuple[Lancamento, dict]], set[int]]:
    """As outras parcelas do alcance que ainda faltam mudar, na ordem do número, com os campos de
    cada uma (menos os que alguém mudou nela), e o número das que ficam como estão em algum
    campo pedido porque uma pessoa o mudou só nelas."""
    outras = lancamentos.ler_por_ids(
        conn,
        [
            i
            for (i,) in conn.execute(
                "SELECT id FROM lancamentos WHERE parcelamento_id = %s AND parcela >= %s"
                " AND id <> %s AND excluido_em IS NULL",
                (parcelamento_id, pendente.desde, pendente.editada),
            )
        ],
    )
    a_mao = lancamentos.campos_a_mao(conn, [l.id for l in outras])
    falta: list[tuple[Lancamento, dict]] = []
    mantidas: set[int] = set()
    for outra in sorted(outras, key=lambda l: l.parcela):
        valores = _valores_na_outra(pendente, outra)
        maos = a_mao.get(outra.id, set())
        if any(c in maos and not iguais(c, v, getattr(outra, c)) for c, v in valores.items()):
            mantidas.add(outra.parcela)
        valores = {
            c: v
            for c, v in valores.items()
            if c not in maos and not iguais(c, v, getattr(outra, c))
        }
        if valores:
            falta.append((outra, valores))
    return falta, mantidas


def _conferir_faturas_pagas(conn, falta: list[tuple[Lancamento, dict]]) -> None:
    """Nenhuma das outras parcelas sai de uma fatura paga nem entra numa (ADR 0021). Conferido
    antes de gravar, para a recusa num lote seguinte não deixar a mudança pela metade."""
    pagas: dict[UUID, set[date]] = {}

    def paga(titular_id: UUID, mes: date) -> bool:
        if titular_id not in pagas:
            pagas[titular_id] = {
                f.mes
                for f in cartoes.faturas_do_titular(conn, titular_id)
                if cartoes.paga_pelo_pagamento(f)
            }
        return mes in pagas[titular_id]

    for outra, valores in falta:
        antes = lancamentos.fatura_em_que_ficaria(conn, outra, {})
        depois = lancamentos.fatura_em_que_ficaria(conn, outra, valores)
        for fatura in (antes, depois):
            if fatura and paga(*fatura):
                raise cartoes.recusa_da_paga(conn, *fatura)


def _ha_pendente(conn, parcelamento_id: UUID) -> bool:
    (texto,) = conn.execute(
        "SELECT mudanca_pendente FROM parcelamentos WHERE id = %s", (parcelamento_id,)
    ).fetchone()
    return bool(texto) or bool(parcelamentos.classificacao_pendente(conn, parcelamento_id))


def _mudar_a_parcela(conn, id: UUID, alteracao: AlteracaoDaParcela, usuario: str) -> _Mudanca:
    """A parcela mudada, o parcelamento e o primeiro lote das outras, numa transação só; avisa,
    antes de gravar, se uma realizada que não é esta mudaria, e recusa se uma das outras sai de
    uma fatura paga ou entra numa. O resto parcela a parcela fica gravado no parcelamento."""
    so_nela = AlteracaoDeLancamento(
        **alteracao.model_dump(include=set(AlteracaoDeLancamento.model_fields))
    )
    [antes] = lancamentos.ler_por_ids(conn, [id]) or [None]
    if antes is None:
        # O excluído vira 410, o que não existe, 404.
        editar(conn, id, so_nela, usuario)
        raise LancamentoNaoEncontrado()
    if not antes.parcelamento_id:
        raise recusar("só a parcela tem alcance")
    mudou = {
        campo: valor
        for campo, valor in _pedidas(alteracao).items()
        if not iguais(campo, valor, getattr(antes, campo))
    }
    if alteracao.alcance != "so_esta" and "tipo" in mudou:
        raise recusar("a parcela é uma despesa")
    # A parcela mudada primeiro, com a edição de sempre: conflito, recusas e fatura paga.
    editar(conn, id, so_nela, usuario)
    mudanca = _Mudanca(antes.parcelamento_id)
    if alteracao.alcance == "so_esta":
        return mudanca
    regra = parcelamentos.ler_um(conn, antes.parcelamento_id)
    if regra is None:
        raise HTTPException(status_code=404, detail="parcelamento não encontrado")
    # A rota termina antes o que outro pedido deixou pela metade; sobra só o que outro pedido
    # gravou no meio deste. Juntos, a classificação de "esta e as próximas" se misturaria com a
    # pendente desde a 1ª, e as parcelas a parcela de um e de outro se atropelariam.
    if _ha_pendente(conn, regra.id):
        raise recusar("o parcelamento ainda está terminando outra mudança: tente de novo")
    no_cartao = faturas.ler_cartao(conn, regra.conta_id) is not None
    desde = antes.parcela if alteracao.alcance == "esta_e_as_proximas" else 1

    # O que vai parcela a parcela: cada outra do alcance, menos nos campos que alguém mudou nela.
    pendente = _PorParcela(
        editada=id,
        parcela=antes.parcela,
        mes=antes.mes,
        no_cartao=no_cartao,
        valores={c: v for c, v in mudou.items() if c in _POR_PARCELA[alteracao.alcance]},
        desde=desde,
        usuario=usuario,
    )
    falta: list[tuple[Lancamento, dict]] = []
    if pendente.valores:
        falta, mudanca.mantidas = _falta(conn, regra.id, pendente)
        _conferir_faturas_pagas(conn, falta)
    realizadas = [
        ParcelaQueMuda(
            id=outra.id,
            parcela=outra.parcela,
            valor_centavos=outra.valor_centavos,
            data=outra.data,
            valor_novo_centavos=valores.get("valor_centavos", outra.valor_centavos),
            data_nova=valores.get("data", outra.data),
            sai=False,
        )
        for outra, valores in falta
        if outra.situacao == "realizado"
    ]

    # O que o parcelamento guarda vai na correção dele, que avisa das realizadas.
    na_regra = {c: v for c, v in mudou.items() if c in CLASSIFICACAO}
    if alteracao.alcance == "todas" and "valor_centavos" in mudou:
        na_regra["valor_da_parcela_centavos"] = mudou["valor_centavos"]
    if alteracao.alcance == "todas" and "data" in mudou:
        na_regra["data"] = (
            mudou["data"] if no_cartao else mais_meses(mudou["data"], 1 - antes.parcela)
        )
    if na_regra:
        correcao = parcelamentos.gravar_correcao(
            conn,
            regra.id,
            AlteracaoDeParcelamento(
                **na_regra, confirmar_realizadas=alteracao.confirmar_realizadas
            ),
            usuario,
            desde=desde,
            editada=id,
            tambem_mudam=realizadas,
        )
        mudanca.classificacao = correcao.classificacao
        mudanca.mantidas |= correcao.mantidas
    elif realizadas and not alteracao.confirmar_realizadas:
        raise RealizadasMudam(
            AvisoDeRealizadas(motivo="a mudança muda parcelas já realizadas", parcelas=realizadas)
        )
    mudanca.mantidas.discard(antes.parcela)
    mudanca.falta_por_parcela = _mudar_o_lote(
        conn, regra.id, pendente, falta, parcelamentos.parcelas_por_lote(regra)
    )
    return mudanca


def _mudar_o_lote(
    conn,
    parcelamento_id: UUID,
    pendente: _PorParcela,
    falta: list[tuple[Lancamento, dict]],
    quantas: int,
    gravado: str = "",
) -> bool:
    """Muda as primeiras `quantas` parcelas que faltam, à mão em cada uma, e grava no
    parcelamento o que sobra (ou tira o pendente `gravado`, se acabou). Devolve se sobrou."""
    lote = falta[:quantas]
    for outra, valores in lote:
        editar(
            conn,
            outra.id,
            AlteracaoDeLancamento(versao=outra.versao, **valores),
            usuario=pendente.usuario,
        )
    sobra = len(falta) > quantas
    if sobra:
        pendente.desde = lote[-1][0].parcela + 1
    texto = pendente.gravar() if sobra else ""
    if (
        texto != gravado
        and not conn.execute(
            "UPDATE parcelamentos SET mudanca_pendente = %s WHERE id = %s"
            " AND coalesce(mudanca_pendente, '') = %s",
            (texto, parcelamento_id, gravado),
        ).rowcount
    ):
        raise psycopg.errors.SerializationFailure("o parcelamento mudou durante a mudança")
    return sobra


def _mudar_um_lote(conn, parcelamento_id: UUID) -> bool:
    """Um lote do que ficou parcela a parcela no parcelamento; devolve se ainda sobra."""
    linha = conn.execute(
        "SELECT mudanca_pendente FROM parcelamentos WHERE id = %s", (parcelamento_id,)
    ).fetchone()
    regra = parcelamentos.ler_um(conn, parcelamento_id)
    if not linha or regra is None or not (pendente := _PorParcela.ler(linha[0])):
        return False
    falta, _ = _falta(conn, parcelamento_id, pendente)
    return _mudar_o_lote(
        conn, parcelamento_id, pendente, falta, parcelamentos.parcelas_por_lote(regra), linha[0]
    )


def _desistir(conn, parcelamento_id: UUID) -> None:
    conn.execute("UPDATE parcelamentos SET mudanca_pendente = '' WHERE id = %s", (parcelamento_id,))


def terminar_o_pendente(url: str | None, parcelamento_id: UUID) -> bool:
    """Termina, em lotes, a parte parcela a parcela que um pedido deixou no parcelamento, e
    devolve se havia alguma. Se uma parcela que falta passou a recusar a mudança depois do
    pedido (a fatura dela foi paga no meio), as que faltam ficam como estão e a recusa sobe."""
    feito = False
    try:
        while em_transacao(
            url, cartoes.protegida(lambda conn: _mudar_um_lote(conn, parcelamento_id))
        ):
            feito = True
    except HTTPException:
        em_transacao(url, lambda conn: _desistir(conn, parcelamento_id))
        raise
    return feito


def terminar_as_mudancas_pendentes(url: str | None) -> int:
    """A tarefa diária termina a parte parcela a parcela das mudanças que pararam no meio.
    Devolve quantas terminou; a que uma recusa trava sai do pendente e fica como parou."""
    with conectar(url) as conn:
        ids = [
            id
            for (id,) in conn.execute(
                "SELECT id FROM parcelamentos WHERE coalesce(mudanca_pendente, '') <> ''"
            )
        ]
    terminadas = 0
    for id in ids:
        try:
            terminar_o_pendente(url, id)
        except HTTPException:
            continue  # ficou como estava: a pessoa vê as parcelas e muda de novo
        terminadas += 1
    return terminadas


def _terminar_o_que_outro_pedido_deixou(url: str | None, id: UUID) -> None:
    """Antes de uma mudança com alcance, termina a que outro pedido deixou pela metade no
    parcelamento da parcela: a classificação pendente e a parte parcela a parcela."""
    with conectar(url) as conn:
        linha = conn.execute(
            "SELECT p.id, coalesce(p.mudanca_pendente, ''), coalesce(p.classificacao_pendente, '')"
            " FROM lancamentos l JOIN parcelamentos p ON p.id = l.parcelamento_id"
            " WHERE l.id = %s",
            (id,),
        ).fetchone()
    if not linha:
        return
    parcelamento_id, por_parcela, classificacao = linha
    if por_parcela:
        try:
            terminar_o_pendente(url, parcelamento_id)
        except HTTPException:
            pass  # o pedido anterior fica como parou; este segue
    if classificacao:
        parcelamentos.completar(url, parcelamento_id)


def _motivo_do_conflito(conflito: ConflitoDeCampos) -> HTTPException:
    campos = ", ".join(c.campo for c in conflito.conflito.campos)
    return recusar(f"a parcela mudou depois ({campos}): confira e mude de novo")


_RESPOSTAS = {
    409: {"model": AvisoDeRealizadas, "description": "A mudança muda parcelas realizadas"},
    410: {"model": Exclusao, "description": "A parcela foi excluída"},
}


@router.patch(
    "/parcelas/{id}",
    response_model=MudancaDaParcela,
    operation_id="mudar_parcela",
    responses=_RESPOSTAS,
)
def mudar_parcela(
    id: UUID, alteracao: AlteracaoDaParcela, usuario: UsuarioLogado, request: Request
) -> MudancaDaParcela | JSONResponse:
    """Muda os campos pedidos da parcela, sobre a versão que o aparelho tinha, só nela, nela e nas
    próximas ou em todas. O campo que o outro lado mudou depois recusa o pedido (422), para a
    pessoa conferir e mudar de novo. Se uma realizada que não é esta mudar, responde 409 com o
    aviso e não grava nada até o pedido vir com `confirmar_realizadas`."""
    url = url_do_banco(request)
    if alteracao.alcance != "so_esta":
        _terminar_o_que_outro_pedido_deixou(url, id)
    try:
        mudanca = em_transacao(
            url, cartoes.protegida(lambda conn: _mudar_a_parcela(conn, id, alteracao, usuario))
        )
    except LancamentoNaoEncontrado:
        raise HTTPException(status_code=404, detail="lançamento não encontrado")
    except LancamentoExcluido as e:
        return JSONResponse(e.exclusao.model_dump(mode="json"), status_code=410)
    except ConflitoDeCampos as e:
        raise _motivo_do_conflito(e)
    except RealizadasMudam as e:
        return JSONResponse(e.aviso.model_dump(mode="json"), status_code=409)
    recusa = None
    if mudanca.falta_por_parcela:
        # As que não couberam na transação da parcela mudada, em lotes do mesmo tamanho. A
        # recusa de um lote (a conferência antes de gravar não prevê todas) não para a
        # classificação, já gravada no parcelamento.
        try:
            terminar_o_pendente(url, mudanca.parcelamento_id)
        except HTTPException as e:
            recusa = e
    if mudanca.classificacao is not None:
        parcelamentos.refazer_as_parcelas(
            url, mudanca.parcelamento_id, usuario, mudanca.classificacao
        )
    if recusa:
        raise recusar(
            f"{recusa.detail}. A parcela, a classificação e as primeiras das outras parcelas"
            " mudaram; as demais ficaram como estavam"
        ) from recusa
    with conectar(url) as conn:
        [parcela] = lancamentos.ler_por_ids(conn, [id]) or [None]
    if parcela is None:
        raise HTTPException(status_code=404, detail="lançamento não encontrado")
    return MudancaDaParcela(lancamento=parcela, parcelas_mantidas=len(mudanca.mantidas))
