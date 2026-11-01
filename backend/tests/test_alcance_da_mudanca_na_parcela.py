"""Alcance da mudança na parcela: só esta, esta e as próximas, todas (ticket 136)."""

from datetime import date

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_parcelamentos import cartao, criar_geladeira, parcelas

HOJE = date(2026, 10, 28)


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hoje é 28/10/2026 em São Paulo."""
    monkeypatch.setattr(lancamentos, "hoje", lambda: HOJE)


def mudar_parcela(casal: Casal, parcela: dict, alcance: str, quem: str = "flavio", **campos):
    return casal.pedir(
        quem,
        "PATCH",
        f"/api/parcelas/{parcela['id']}",
        json={"versao": parcela["versao"], "alcance": alcance} | campos,
    )


def editar_so_nela(casal: Casal, parcela: dict, **campos) -> dict:
    """A edição comum do lançamento: muda a parcela só nela."""
    resposta = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{parcela['id']}",
        json={"versao": parcela["versao"]} | campos,
    )
    assert resposta.status_code == 200
    return resposta.json()


def test_esta_e_as_proximas_muda_a_descricao_daqui_para_frente_sem_tocar_a_alterada_a_mao(
    casal: Casal,
):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", parcelas=4)
    [_, segunda, _, quarta] = parcelas(casal, novo["id"])
    editar_so_nela(casal, quarta, descricao="Geladeira, última")

    resposta = mudar_parcela(casal, segunda, "esta_e_as_proximas", descricao="Geladeira nova")

    assert resposta.status_code == 200
    assert resposta.json()["parcelas_mantidas"] == 1
    assert resposta.json()["lancamento"]["descricao"] == "Geladeira nova"
    assert [(l["descricao"], l["alterada_a_mao"]) for l in parcelas(casal, novo["id"])] == [
        ("Geladeria", False),
        ("Geladeira nova", False),
        ("Geladeira nova", False),
        ("Geladeira, última", True),
    ]
    # O parcelamento passa a ter a descrição nova: as parcelas que ainda vierem nascem com ela.
    [regra] = [
        p
        for p in casal.pedir("flavio", "GET", "/api/parcelamentos").json()
        if p["id"] == novo["id"]
    ]
    assert regra["descricao"] == "Geladeira nova"


def valores(casal: Casal, id: str) -> list[tuple]:
    return [
        (l["parcela"], l["valor_centavos"], l["data"], l["situacao"], l["alterada_a_mao"])
        for l in parcelas(casal, id)
    ]


def test_todas_muda_o_valor_de_todas_e_avisa_antes_de_mudar_a_realizada(casal: Casal):
    # Lançada em 10/10 com a 1ª nesse dia: hoje (28/10) ela é realizada, as outras, previstas.
    novo = criar_geladeira(
        casal,
        casal.conta(),
        lancada_em="2026-10-10",
        data="2026-10-10",
        automatico=True,
        parcelas=4,
        valor_total_centavos=40000,
    )
    [_, segunda, terceira, _] = parcelas(casal, novo["id"])
    editar_so_nela(casal, terceira, valor_centavos=9000)
    segunda = parcelas(casal, novo["id"])[1]

    aviso = mudar_parcela(casal, segunda, "todas", valor_centavos=12000)

    assert aviso.status_code == 409
    assert [
        (p["parcela"], p["valor_centavos"], p["valor_novo_centavos"])
        for p in aviso.json()["parcelas"]
    ] == [(1, 10000, 12000)]
    assert [v[1] for v in valores(casal, novo["id"])] == [10000, 10000, 9000, 10000]

    resposta = mudar_parcela(
        casal, segunda, "todas", valor_centavos=12000, confirmar_realizadas=True
    )

    assert resposta.status_code == 200
    assert resposta.json()["parcelas_mantidas"] == 1
    assert valores(casal, novo["id"]) == [
        (1, 12000, "2026-10-10", "realizado", False),
        (2, 12000, "2026-11-10", "previsto", False),
        (3, 9000, "2026-12-10", "previsto", True),
        (4, 12000, "2027-01-10", "previsto", False),
    ]
    # O parcelamento passa a valer o valor da parcela vezes o número delas.
    [regra] = [
        p
        for p in casal.pedir("flavio", "GET", "/api/parcelamentos").json()
        if p["id"] == novo["id"]
    ]
    assert regra["valor_total_centavos"] == 48000


def test_esta_e_as_proximas_muda_valor_e_dia_do_boleto_daqui_para_frente_a_mao_em_cada_uma(
    casal: Casal,
):
    novo = criar_geladeira(
        casal, casal.conta(), data="2026-11-10", parcelas=4, valor_total_centavos=40000
    )
    [_, segunda, *_] = parcelas(casal, novo["id"])

    resposta = mudar_parcela(
        casal, segunda, "esta_e_as_proximas", valor_centavos=11000, data="2026-12-15"
    )

    assert resposta.status_code == 200
    assert resposta.json()["parcelas_mantidas"] == 0
    # O parcelamento tem um valor e uma data só: daqui para frente, cada parcela fica à mão.
    assert valores(casal, novo["id"]) == [
        (1, 10000, "2026-11-10", "previsto", False),
        (2, 11000, "2026-12-15", "previsto", True),
        (3, 11000, "2027-01-15", "previsto", True),
        (4, 11000, "2027-02-15", "previsto", True),
    ]
    # A correção do parcelamento depois não as desfaz.
    assert (
        casal.pedir(
            "flavio",
            "PATCH",
            f"/api/parcelamentos/{novo['id']}",
            json={"valor_total_centavos": 80000},
        ).json()["parcelas_mantidas"]
        == 3
    )
    assert [v[1] for v in valores(casal, novo["id"])] == [20000, 11000, 11000, 11000]


def test_so_esta_muda_so_a_parcela_e_a_deixa_alterada_a_mao_no_campo(casal: Casal):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", parcelas=3)
    [primeira, *_] = parcelas(casal, novo["id"])

    resposta = mudar_parcela(casal, primeira, "so_esta", pessoa="esposa")

    assert resposta.status_code == 200
    assert resposta.json()["parcelas_mantidas"] == 0
    assert [(l["pessoa"], l["alterada_a_mao"]) for l in parcelas(casal, novo["id"])] == [
        ("esposa", True),
        (None, False),
        (None, False),
    ]
    # A correção da pessoa no parcelamento a preserva.
    corrigido = casal.pedir(
        "flavio", "PATCH", f"/api/parcelamentos/{novo['id']}", json={"pessoa": "flavio"}
    )
    assert corrigido.json()["parcelas_mantidas"] == 1
    assert [l["pessoa"] for l in parcelas(casal, novo["id"])] == ["esposa", "flavio", "flavio"]


def test_todas_leva_a_descricao_mudada_a_mao_nesta_e_a_conta_a_todas(casal: Casal):
    nubank, inter = cartao(casal), cartao(casal, nome="Inter")
    novo = criar_geladeira(casal, nubank, data="2026-11-10", parcelas=3)
    [_, segunda, _] = parcelas(casal, novo["id"])
    segunda = editar_so_nela(casal, segunda, descricao="Geladeira, a do meio")

    resposta = mudar_parcela(casal, segunda, "todas", descricao="Geladeira", conta_id=inter)

    assert resposta.status_code == 200
    # A parcela mudada segue a descrição nova, mesmo tendo sido mudada à mão antes.
    assert resposta.json()["parcelas_mantidas"] == 0
    depois = parcelas(casal, novo["id"])
    assert [(l["descricao"], l["conta_id"]) for l in depois] == [("Geladeira", inter)] * 3
    # Compra em 10/11, antes do fechamento: cada parcela cai uma fatura depois da outra.
    assert [l["fatura_mes"] for l in depois] == ["2026-11-01", "2026-12-01", "2027-01-01"]


def test_mudanca_com_alcance_recusada(casal: Casal):
    conta = casal.conta()
    novo = criar_geladeira(casal, conta, data="2026-11-10", parcelas=3)
    [primeira, *_] = parcelas(casal, novo["id"])
    editar_so_nela(casal, primeira, descricao="Outra")

    # Sobre a versão de antes, o campo que mudou depois recusa o pedido inteiro.
    velha = mudar_parcela(casal, primeira, "todas", descricao="Mais outra", quem="esposa")
    assert velha.status_code == 422
    assert "descricao" in velha.json()["detail"]
    avulso = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json={
            "id": "00000000-0000-4000-8000-000000000136",
            "tipo": "despesa",
            "valor_centavos": 100,
            "data": "2026-10-28",
            "conta_id": conta,
            "categoria_ids": primeira["categoria_ids"],
        },
    ).json()
    assert mudar_parcela(casal, avulso, "todas", descricao="x").status_code == 422
    assert (
        mudar_parcela(casal, parcelas(casal, novo["id"])[1], "todas", tipo="receita").status_code
        == 422
    )
    assert [l["descricao"] for l in parcelas(casal, novo["id"])] == [
        "Outra",
        "Geladeria",
        "Geladeria",
    ]
