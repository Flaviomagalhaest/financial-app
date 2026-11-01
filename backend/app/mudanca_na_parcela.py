"""Alcance da mudança na parcela (ticket 136): mudar um campo de uma parcela só nela, nela e nas
próximas, ou em todas, inclusive as já realizadas.

"Só esta" é a edição comum do lançamento e deixa a parcela alterada à mão no campo. Os outros
dois mudam o parcelamento e precisam de internet, como a correção dele (ADR 0011): a descrição,
as categorias, as tags, a pessoa e o item vão para o parcelamento, a partir da parcela mudada ou
desde a 1ª, e em "todas" o valor e a data viram a correção do valor da parcela e da data. O que o
parcelamento não sabe guardar (o valor e a data só daqui para frente, a conta e a fatura) vai
parcela a parcela, como mudança à mão em cada uma. As parcelas que uma pessoa mudou só nelas
ficam como estão nesses campos, e a resposta diz quantas ficaram assim."""

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

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
    # Os campos que vão parcela a parcela, por parcela, nas que ainda faltam.
    por_parcela: list[tuple[UUID, dict]] = field(default_factory=list)
    # A classificação que a correção gravou no parcelamento, para refazer nas parcelas.
    classificacao: dict[str, int] | None = None
    mantidas: set[int] = field(default_factory=set)


# O que vai parcela a parcela, conforme o alcance.
_POR_PARCELA = {
    "esta_e_as_proximas": {"valor_centavos", "data", "conta_id", "fatura_mes"},
    "todas": {"conta_id", "fatura_mes"},
}


def _pedidas(alteracao: AlteracaoDaParcela) -> dict:
    pedidas = alteracao.model_dump(
        exclude={"versao", "acao_em", "alcance", "confirmar_realizadas"}, exclude_none=True
    )
    if "pessoa" in pedidas:
        pedidas["pessoa"] = pedidas["pessoa"] or None
    return pedidas


def _valores_na_outra(antes: Lancamento, outra: Lancamento, mudou: dict, no_cartao: bool) -> dict:
    """O que a mudança da parcela `antes` dá numa outra parcela: o mesmo valor e a mesma conta, a
    data no mesmo dia (no boleto, um mês a mais por parcela) e a fatura deslocada igual."""
    valores = {}
    if "valor_centavos" in mudou:
        valores["valor_centavos"] = mudou["valor_centavos"]
    if "data" in mudou:
        valores["data"] = (
            mudou["data"] if no_cartao else mais_meses(mudou["data"], outra.parcela - antes.parcela)
        )
    if "conta_id" in mudou:
        valores["conta_id"] = mudou["conta_id"]
    if "fatura_mes" in mudou and outra.fatura_mes:
        deslocamento = (mudou["fatura_mes"].year - antes.mes.year) * 12 + (
            mudou["fatura_mes"].month - antes.mes.month
        )
        valores["fatura_mes"] = faturas.somar_meses(outra.mes, deslocamento)
    return valores


def _mudar_a_parcela(conn, id: UUID, alteracao: AlteracaoDaParcela, usuario: str) -> _Mudanca:
    """A parcela mudada, o parcelamento e o primeiro lote das outras, numa transação só; avisa,
    antes de gravar, se uma realizada que não é esta mudaria."""
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
    no_cartao = faturas.ler_cartao(conn, regra.conta_id) is not None
    desde = antes.parcela if alteracao.alcance == "esta_e_as_proximas" else 1

    # O que vai parcela a parcela: cada outra do alcance, menos nos campos que alguém mudou nela.
    por_parcela = {c: v for c, v in mudou.items() if c in _POR_PARCELA[alteracao.alcance]}
    realizadas: list[ParcelaQueMuda] = []
    if por_parcela:
        outras = [
            l
            for l in lancamentos.ler_por_ids(
                conn,
                [
                    i
                    for (i,) in conn.execute(
                        "SELECT id FROM lancamentos WHERE parcelamento_id = %s AND parcela >= %s"
                        " AND id <> %s AND excluido_em IS NULL",
                        (regra.id, desde, id),
                    )
                ],
            )
        ]
        a_mao = lancamentos.campos_a_mao(conn, [l.id for l in outras])
        for outra in sorted(outras, key=lambda l: l.parcela):
            valores = _valores_na_outra(antes, outra, por_parcela, no_cartao)
            maos = a_mao.get(outra.id, set())
            ficam = {
                c for c in valores if c in maos and not iguais(c, valores[c], getattr(outra, c))
            }
            if ficam:
                mudanca.mantidas.add(outra.parcela)
            valores = {
                c: v
                for c, v in valores.items()
                if c not in maos and not iguais(c, v, getattr(outra, c))
            }
            if not valores:
                continue
            mudanca.por_parcela.append((outra.id, valores))
            if outra.situacao == "realizado":
                realizadas.append(
                    ParcelaQueMuda(
                        id=outra.id,
                        parcela=outra.parcela,
                        valor_centavos=outra.valor_centavos,
                        data=outra.data,
                        valor_novo_centavos=valores.get("valor_centavos", outra.valor_centavos),
                        data_nova=valores.get("data", outra.data),
                        sai=False,
                    )
                )

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
    quantas = parcelamentos.parcelas_por_lote(regra)
    _mudar_as_outras(conn, mudanca.por_parcela[:quantas], usuario)
    mudanca.por_parcela = mudanca.por_parcela[quantas:]
    return mudanca


def _mudar_as_outras(conn, lote: list[tuple[UUID, dict]], usuario: str) -> None:
    """Muda as parcelas do lote, à mão em cada uma; a que foi excluída no meio fica como está."""
    for outra, valores in lote:
        [atual] = lancamentos.ler_por_ids(conn, [outra]) or [None]
        if atual is None:
            continue
        editar(conn, outra, AlteracaoDeLancamento(versao=atual.versao, **valores), usuario)


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
    try:
        mudanca = em_transacao(
            url, cartoes.protegida(lambda conn: _mudar_a_parcela(conn, id, alteracao, usuario))
        )
        # As que não couberam na transação da parcela mudada, em lotes do mesmo tamanho.
        quantas = 0
        while mudanca.por_parcela:
            if not quantas:
                with conectar(url) as conn:
                    regra = parcelamentos.ler_um(conn, mudanca.parcelamento_id)
                if regra is None:
                    break
                quantas = parcelamentos.parcelas_por_lote(regra)
            lote = mudanca.por_parcela[:quantas]
            em_transacao(
                url,
                cartoes.protegida(lambda conn, lote=lote: _mudar_as_outras(conn, lote, usuario)),
            )
            mudanca.por_parcela = mudanca.por_parcela[quantas:]
    except LancamentoNaoEncontrado:
        raise HTTPException(status_code=404, detail="lançamento não encontrado")
    except LancamentoExcluido as e:
        return JSONResponse(e.exclusao.model_dump(mode="json"), status_code=410)
    except ConflitoDeCampos as e:
        raise _motivo_do_conflito(e)
    except RealizadasMudam as e:
        return JSONResponse(e.aviso.model_dump(mode="json"), status_code=409)
    if mudanca.classificacao is not None:
        parcelamentos.refazer_as_parcelas(
            url, mudanca.parcelamento_id, usuario, mudanca.classificacao
        )
    with conectar(url) as conn:
        [parcela] = lancamentos.ler_por_ids(conn, [id]) or [None]
    if parcela is None:
        raise HTTPException(status_code=404, detail="lançamento não encontrado")
    return MudancaDaParcela(lancamento=parcela, parcelas_mantidas=len(mudanca.mantidas))
