"""Limite comprometido e disponível do cartão (ticket 56; decisão no ticket 23)."""

from datetime import date
from uuid import uuid4

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_cartoes import comprar, novo_cartao


@pytest.fixture(autouse=True)
def hoje_10_04(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 4, 10))


def limite_de(casal: Casal, cartao: str) -> dict:
    resposta = casal.pedir("esposa", "GET", f"/api/cartoes/{cartao}/limite")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def parcelar(casal: Casal, cartao: str, **campos) -> dict:
    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/parcelamentos",
        json={
            "id": str(uuid4()),
            "valor_total_centavos": 30000,
            "parcelas": 3,
            "descricao": "Geladeira",
            "conta_id": cartao,
            "categoria_ids": [casal.categoria()],
            "data": "2026-04-02",
        }
        | campos,
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_comprometido_soma_fatura_aberta_fechada_nao_paga_e_parcelas_futuras(casal: Casal):
    titular = novo_cartao(casal, limite_centavos=500000)["id"]
    adicional = casal.pedir(
        "esposa", "POST", "/api/cartoes", json={"nome": "Nubank da esposa", "titular_id": titular}
    ).json()["id"]
    comprar(casal, titular, "2026-02-26", valor_centavos=10000)  # fatura de 03/2026, fechada
    comprar(casal, titular, "2026-03-28", valor_centavos=2500)  # fatura de 04/2026, aberta
    comprar(casal, adicional, "2026-04-02", valor_centavos=40000, quem="esposa")  # 04/2026
    # 3 x 100,00: a 1ª entra na fatura aberta, as outras 2 são parcelas futuras.
    parcelar(casal, titular)

    limite = limite_de(casal, titular)

    assert (
        limite["limite_centavos"],
        limite["fatura_aberta_centavos"],
        limite["faturas_fechadas_centavos"],
        limite["parcelas_futuras_centavos"],
        limite["comprometido_centavos"],
        limite["disponivel_centavos"],
    ) == (500000, 52500, 10000, 20000, 82500, 417500)


def test_recorrencia_prevista_no_cartao_nao_ocupa_o_limite(casal: Casal):
    cartao = novo_cartao(casal, limite_centavos=100000)["id"]
    comprar(casal, cartao, "2026-04-02", valor_centavos=3000)
    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/recorrencias",
        json={
            "id": str(uuid4()),
            "tipo": "despesa",
            "valor_centavos": 5000,
            "tipo_do_valor": "fixo",
            "descricao": "Streaming",
            "conta_id": cartao,
            "categoria_ids": [casal.categoria("Lazer")],
            "inicio": "2026-04-20",
            "a_cada": 1,
            "unidade": "meses",
        },
    )
    assert resposta.status_code == 201, resposta.text

    limite = limite_de(casal, cartao)

    assert (limite["comprometido_centavos"], limite["disponivel_centavos"]) == (3000, 97000)


def test_pagar_a_fatura_fechada_libera_o_limite(casal: Casal):
    cartao = novo_cartao(casal, limite_centavos=100000)["id"]
    conta = casal.conta()
    comprar(casal, cartao, "2026-02-26", valor_centavos=10000)  # fatura de 03/2026, fechada
    assert limite_de(casal, cartao)["disponivel_centavos"] == 90000

    pagamento = casal.pedir(
        "flavio",
        "POST",
        "/api/transferencias",
        json={
            "id": str(uuid4()),
            "conta_origem_id": conta,
            "conta_destino_id": cartao,
            "valor_centavos": 4000,
            "data": "2026-04-05",
            "descricao": "Fatura Nubank",
            "fatura_mes": "2026-03-01",
        },
    )
    assert pagamento.status_code == 201, pagamento.text

    limite = limite_de(casal, cartao)
    assert (limite["faturas_fechadas_centavos"], limite["disponivel_centavos"]) == (6000, 94000)


def test_estorno_e_ajuste_da_fatura_entram_na_conta(casal: Casal):
    cartao = novo_cartao(casal, limite_centavos=100000)["id"]
    original = comprar(casal, cartao, "2026-04-02", valor_centavos=10000)
    estorno = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento_de_estorno(casal, original, valor_centavos=4000),
    )
    assert estorno.status_code == 201, estorno.text
    comprar(casal, cartao, "2026-02-26", valor_centavos=10000)  # fatura de 03/2026, fechada
    ajuste = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/cartoes/{cartao}/faturas/2026-03-01",
        json={"ajuste_centavos": 150},
    )
    assert ajuste.status_code == 200, ajuste.text

    limite = limite_de(casal, cartao)

    assert (limite["fatura_aberta_centavos"], limite["faturas_fechadas_centavos"]) == (6000, 10150)


def lancamento_de_estorno(casal: Casal, original: dict, **campos) -> dict:
    return {
        "id": str(uuid4()),
        "tipo": "despesa",
        "valor_centavos": original["valor_centavos"],
        "data": "2026-04-03",
        "descricao": "Estorno",
        "conta_id": original["conta_id"],
        "categoria_ids": original["categoria_ids"],
        "estorno_de": original["id"],
    } | campos


def test_cartao_sem_limite_informado_nao_tem_disponivel(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-02", valor_centavos=3000)

    limite = limite_de(casal, cartao)

    assert (limite["limite_centavos"], limite["disponivel_centavos"]) == (None, None)
    assert limite["comprometido_centavos"] == 3000


def test_adicional_mostra_o_limite_do_titular(casal: Casal):
    titular = novo_cartao(casal, limite_centavos=100000)["id"]
    adicional = casal.pedir(
        "esposa", "POST", "/api/cartoes", json={"nome": "Nubank da esposa", "titular_id": titular}
    ).json()["id"]
    comprar(casal, titular, "2026-04-02", valor_centavos=3000)
    comprar(casal, adicional, "2026-04-03", valor_centavos=2000, quem="esposa")

    assert limite_de(casal, adicional) == limite_de(casal, titular)
    assert limite_de(casal, adicional)["comprometido_centavos"] == 5000


def test_parcelamentos_em_andamento_e_os_proximos_12_meses(casal: Casal):
    cartao = novo_cartao(casal, limite_centavos=500000)["id"]
    comprar(casal, cartao, "2026-02-26", valor_centavos=10000)  # 03/2026, fechada, vence 05/04
    comprar(casal, cartao, "2026-03-28", valor_centavos=2500)  # 04/2026, vence 05/05
    geladeira = parcelar(casal, cartao)  # parcela 1 em 04/2026; 2 e 3 em 05 e 06/2026

    limite = limite_de(casal, cartao)

    assert limite["parcelamentos"] == [
        {
            "id": geladeira["id"],
            "descricao": "Geladeira",
            "parcelas": 3,
            "parcelas_restantes": 2,
            "restante_centavos": 20000,
            "fim_previsto": "2026-06-01",
        }
    ]
    assert len(limite["proximos_meses"]) == 12
    assert (limite["proximos_meses"][0]["mes"], limite["proximos_meses"][-1]["mes"]) == (
        "2026-04-01",
        "2027-03-01",
    )
    assert [
        (m["mes"], m["fatura_centavos"], m["parcelas_centavos"], m["libera_centavos"])
        for m in limite["proximos_meses"][:5]
    ] == [
        ("2026-04-01", 10000, 0, 10000),  # a fechada de março vence em 05/04
        ("2026-05-01", 12500, 0, 12500),  # a aberta, com a 1ª parcela, vence em 05/05
        ("2026-06-01", 0, 10000, 10000),  # a 2ª parcela, na fatura de maio que vence em 05/06
        ("2026-07-01", 0, 10000, 10000),
        ("2026-08-01", 0, 0, 0),
    ]
