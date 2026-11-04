"""A janela do aparelho (ticket 166, ADR 0025): a lista que o aparelho guarda traz só os
lançamentos que contam nos últimos 12 meses, pelo mês em que contam, e todos daqui para frente."""

from datetime import date
from uuid import uuid4

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_cartoes import comprar, novo_cartao
from tests.test_lancamentos import lancamento
from tests.test_recorrencias import recorrencia


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch: pytest.MonkeyPatch) -> None:
    # Com hoje em 28/10/2026, a janela começa em novembro de 2025.
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 10, 28))


def ids_da_lista(casal: Casal) -> set[str]:
    resposta = casal.pedir("esposa", "GET", "/api/lancamentos")
    assert resposta.status_code == 200, resposta.text
    return {l["id"] for l in resposta.json()}


def lancar(casal: Casal, conta: str, data: str) -> str:
    resposta = casal.pedir(
        "flavio", "POST", "/api/lancamentos", json=lancamento(conta, [casal.categoria()], data=data)
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["id"]


def test_a_lista_traz_os_12_meses_ate_hoje_e_deixa_de_fora_o_mes_antes_deles(casal: Casal):
    conta = casal.conta()
    primeiro_dia_da_janela = lancar(casal, conta, "2025-11-01")
    ultimo_dia_antes = lancar(casal, conta, "2025-10-31")
    deste_mes = lancar(casal, conta, "2026-10-28")

    lista = ids_da_lista(casal)

    assert {primeiro_dia_da_janela, deste_mes} <= lista
    assert ultimo_dia_antes not in lista


def test_a_compra_no_cartao_entra_pelo_mes_da_fatura_e_nao_pela_data(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    # A fatura fecha dia 25: a compra de 28/10/2025 conta em novembro, dentro da janela; a de
    # 20/10/2025 conta em outubro, fora dela.
    na_fatura_de_novembro = comprar(casal, cartao, "2025-10-28")
    na_fatura_de_outubro = comprar(casal, cartao, "2025-10-20")

    lista = ids_da_lista(casal)

    assert na_fatura_de_novembro["mes"] == "2025-11-01"
    assert na_fatura_de_novembro["id"] in lista
    assert na_fatura_de_outubro["id"] not in lista


def test_os_previstos_futuros_da_recorrencia_vem_todos_ate_o_horizonte(casal: Casal):
    conta, categoria = casal.conta(), casal.categoria()
    regra = recorrencia(conta, [categoria], inicio="2026-11-10")
    assert casal.pedir("flavio", "POST", "/api/recorrencias", json=regra).status_code == 201
    futuro_distante = lancar(casal, conta, "2030-01-10")

    resposta = casal.pedir("esposa", "GET", "/api/lancamentos").json()

    previstos = [l for l in resposta if l["recorrencia_id"] == regra["id"]]
    # Até o horizonte de 24 meses: o último previsto é o de 10/10/2028.
    assert max(l["data"] for l in previstos) == "2028-10-10"
    assert futuro_distante in {l["id"] for l in resposta}


def test_um_lancamento_fora_da_janela_se_le_pelo_id(casal: Casal):
    antigo = lancar(casal, casal.conta(), "2024-03-10")

    resposta = casal.pedir("esposa", "GET", f"/api/lancamentos/{antigo}")

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["lancamento"]["id"] == antigo
    assert resposta.json()["ligados"] == []


def test_o_lancamento_pelo_id_vem_com_os_estornos_e_o_estorno_com_a_compra(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    compra = comprar(casal, cartao, "2024-03-10")
    estorno = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(
            cartao, [], data="2024-03-12", valor_centavos=1000, estorno_de=compra["id"]
        ),
    )
    assert estorno.status_code == 201, estorno.text
    comprar(casal, cartao, "2024-03-11")  # outra compra, sem ligação

    da_compra = casal.pedir("esposa", "GET", f"/api/lancamentos/{compra['id']}").json()
    do_estorno = casal.pedir("esposa", "GET", f"/api/lancamentos/{estorno.json()['id']}").json()

    assert [l["id"] for l in da_compra["ligados"]] == [estorno.json()["id"]]
    assert [l["id"] for l in do_estorno["ligados"]] == [compra["id"]]


def test_a_parcela_pelo_id_vem_com_as_outras_parcelas_e_os_estornos_delas(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    parcelamento = {
        "id": str(uuid4()),
        "valor_total_centavos": 30000,
        "parcelas": 3,
        "descricao": "Geladeira",
        "conta_id": cartao,
        "categoria_ids": [casal.categoria()],
        "data": "2024-03-10",
    }
    assert casal.pedir("flavio", "POST", "/api/parcelamentos", json=parcelamento).status_code == 201
    parcelas = sorted(
        casal.pedir("esposa", "GET", f"/api/parcelamentos/{parcelamento['id']}/lancamentos").json(),
        key=lambda l: l["parcela"],
    )
    estorno = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(
            cartao, [], data="2024-05-12", valor_centavos=1000, estorno_de=parcelas[2]["id"]
        ),
    ).json()

    lida = casal.pedir("esposa", "GET", f"/api/lancamentos/{parcelas[0]['id']}").json()

    assert {l["id"] for l in lida["ligados"]} == {
        parcelas[1]["id"],
        parcelas[2]["id"],
        estorno["id"],
    }


def test_lancamento_que_nao_existe_ou_foi_excluido_pelo_id_e_404(casal: Casal):
    excluido = lancar(casal, casal.conta(), "2024-03-10")
    assert casal.pedir("flavio", "DELETE", f"/api/lancamentos/{excluido}").status_code == 204

    assert casal.pedir("esposa", "GET", f"/api/lancamentos/{uuid4()}").status_code == 404
    assert casal.pedir("esposa", "GET", f"/api/lancamentos/{excluido}").status_code == 404
