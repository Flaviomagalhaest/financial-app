"""Regras que tiram parcela ou ocorrência com estorno (ticket 188, ADR 0016)."""

from tests.conftest import Casal
from tests.test_estorno_de_parte_e_de_parcelas import estorno_de_todas, parcelada_no_cartao
from tests.test_fatura_paga import abril_paga  # noqa: F401 (fixture)
from tests.test_lancamentos import lancamento
from tests.test_parcelamentos import parcelas


def estornar_parcela(casal: Casal, novo: dict, parcela: dict, valor: int):
    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(
            novo["conta_id"],
            [],
            data="2026-06-10",
            valor_centavos=valor,
            estorno_de=parcela["id"],
        ),
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def corrigir(casal: Casal, novo: dict, **campos):
    return casal.pedir("flavio", "PATCH", f"/api/parcelamentos/{novo['id']}", json=campos)


def estado(casal: Casal, novo: dict):
    [lido] = [
        p
        for p in casal.pedir("flavio", "GET", "/api/parcelamentos").json()
        if p["id"] == novo["id"]
    ]
    return (
        lido["parcelas"],
        lido["valor_total_centavos"],
        [
            (p["parcela"], p["valor_centavos"], p.get("excluido"))
            for p in parcelas(casal, novo["id"])
        ],
    )


def test_corrigir_para_menos_parcelas_com_estorno_na_que_sairia_recusa_e_nao_grava(casal: Casal):
    _, _, novo = parcelada_no_cartao(casal)
    [_, _, terceira] = parcelas(casal, novo["id"])
    estornar_parcela(casal, novo, terceira, 1000)
    antes = estado(casal, novo)

    recusada = corrigir(casal, novo, parcelas=2)

    assert recusada.status_code == 422
    assert recusada.json()["detail"] == "a parcela 3: a compra tem estorno; exclua o estorno antes"
    assert estado(casal, novo) == antes


def test_com_estorno_de_todas_corrigir_ou_excluir_abaixo_do_estornado_recusa_e_nao_grava(
    casal: Casal,
):
    # 30.000 em 3 de 10.000; estornado de todas: 15.000.
    _, _, novo = parcelada_no_cartao(casal)
    assert estorno_de_todas(casal, novo, 15000).status_code == 201
    antes = estado(casal, novo)
    [_, segunda, terceira] = parcelas(casal, novo["id"])

    total_menor = corrigir(casal, novo, valor_total_centavos=12000)
    menos_parcelas = corrigir(casal, novo, parcelas=2, valor_total_centavos=14000)
    excluir_duas = None
    primeira_fora = casal.pedir("flavio", "DELETE", f"/api/lancamentos/{terceira['id']}")
    if primeira_fora.status_code == 204:
        excluir_duas = casal.pedir("flavio", "DELETE", f"/api/lancamentos/{segunda['id']}")

    assert (total_menor.status_code, menos_parcelas.status_code) == (422, 422)
    assert "estornados" in total_menor.json()["detail"]
    # Ficam 20.000 depois de excluir a 3ª; excluir também a 2ª deixaria 10.000 < 15.000.
    assert primeira_fora.status_code == 204
    assert excluir_duas.status_code == 422
    [lido] = [
        p
        for p in casal.pedir("flavio", "GET", "/api/parcelamentos").json()
        if p["id"] == novo["id"]
    ]
    assert (lido["parcelas"], lido["valor_total_centavos"]) == antes[:2]


def test_com_estorno_de_todas_a_correcao_que_fica_no_limite_passa(casal: Casal):
    _, _, novo = parcelada_no_cartao(casal)
    assert estorno_de_todas(casal, novo, 15000).status_code == 201

    no_limite = corrigir(casal, novo, valor_total_centavos=15000, confirmar_realizadas=True)

    assert no_limite.status_code == 200, no_limite.text


# --- Recorrência -----------------------------------------------------------------------------


def previsto_com_estorno(casal: Casal, monkeypatch):
    """Recorrência no cartão com o 1º previsto (10/11) estornado."""
    from tests.test_cartoes import novo_cartao
    from tests.test_recorrencias import HOJE, gerados, no_dia, recorrencia

    cartao = novo_cartao(casal)["id"]
    nova = recorrencia(
        cartao, [casal.categoria("Assinaturas")], inicio="2026-11-10", vezes=4, tipo_do_valor="fixo"
    )
    no_dia(monkeypatch, HOJE.isoformat())
    assert casal.pedir("flavio", "POST", "/api/recorrencias", json=nova).status_code == 201
    [primeiro, *_] = gerados(casal, nova["id"])
    estorno = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(
            cartao, [], data="2026-11-10", valor_centavos=1000, estorno_de=primeiro["id"]
        ),
    )
    assert estorno.status_code == 201, estorno.text
    return nova, primeiro


def test_reajuste_e_exclusao_da_regra_deixam_o_previsto_com_estorno_e_tiram_os_outros(
    casal: Casal, monkeypatch
):
    from tests.test_recorrencias import gerados, mudar

    nova, primeiro = previsto_com_estorno(casal, monkeypatch)

    reajustada = mudar(casal, nova["id"], 1, valor_centavos=21000)

    assert reajustada.status_code == 200, reajustada.text
    assert [(l["ocorrencia"], l["valor_centavos"]) for l in gerados(casal, nova["id"])] == [
        (1, 18990),
        (2, 21000),
        (3, 21000),
        (4, 21000),
    ]
    encerrada = mudar(casal, nova["id"], 1, vezes=1)
    assert encerrada.status_code == 200, encerrada.text
    assert [l["id"] for l in gerados(casal, nova["id"])] == [primeiro["id"]]

    excluida = casal.pedir("flavio", "DELETE", f"/api/recorrencias/{nova['id']}")

    assert excluida.status_code == 204
    assert [l["id"] for l in gerados(casal, nova["id"])] == [primeiro["id"]]


# --- Correção de fatura ----------------------------------------------------------------------


def test_correcao_de_fatura_exclui_estorno_e_compra_em_qualquer_ordem_e_recusa_so_a_compra(
    casal: Casal,
    abril_paga,  # noqa: F811
):
    from tests.test_fatura_paga import corrigir as corrigir_fatura

    compra = abril_paga.compra
    estorno = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(
            abril_paga.cartao,
            [],
            data="2026-05-08",
            valor_centavos=1000,
            estorno_de=compra["id"],
        ),
    ).json()

    so_a_compra = corrigir_fatura(casal, abril_paga, compras_excluidas=[{"id": compra["id"]}])
    assert (so_a_compra.status_code, so_a_compra.json()["detail"]) == (
        422,
        "a compra tem estorno; exclua o estorno antes",
    )
    ids = {l["id"] for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()}
    assert {compra["id"], estorno["id"]} <= ids

    resposta = corrigir_fatura(
        casal,
        abril_paga,
        compras_novas=[
            lancamento(
                abril_paga.cartao, [casal.categoria()], data="2026-04-10", valor_centavos=100000
            )
        ],
        compras_excluidas=[{"id": compra["id"]}, {"id": estorno["id"]}],
    )

    assert resposta.status_code == 200, resposta.text
    ids = {l["id"] for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()}
    assert not ({compra["id"], estorno["id"]} & ids)
