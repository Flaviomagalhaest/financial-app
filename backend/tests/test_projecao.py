"""Aba Futuro e projeção de saldo (ticket 58): a soma das contas no fim de cada mês, com o
realizado no passado e duas linhas daqui para frente."""

from datetime import date
from uuid import uuid4

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_cartoes import novo_cartao
from tests.test_lancamentos import lancamento


@pytest.fixture(autouse=True)
def hoje_10_04(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 4, 10))


def lancar(
    casal: Casal, conta: str, data: str, valor: int, tipo="despesa", categoria=None, **campos
) -> dict:
    categoria = categoria or casal.categoria(f"{tipo} {uuid4()}", tipo)
    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(conta, [categoria], data=data, valor_centavos=valor, tipo=tipo) | campos,
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def planejar(casal: Casal, mes: str, categoria: str, valor: int) -> None:
    resposta = casal.pedir(
        "flavio",
        "POST",
        f"/api/planejamento/{mes}/itens",
        json={"id": str(uuid4()), "categoria_id": categoria, "valor_centavos": valor},
    )
    assert resposta.status_code == 201, resposta.text


def futuro(casal: Casal) -> dict:
    resposta = casal.pedir("esposa", "GET", "/api/futuro")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def linha(futuro: dict, campo: str) -> dict[str, int]:
    return {m["mes"]: m[campo] for m in futuro["proximos_meses"]}


def test_so_previstos_parte_do_saldo_de_hoje_e_soma_os_previstos_de_cada_mes(casal: Casal):
    conta = casal.conta()
    lancar(casal, conta, "2026-04-02", 100000, tipo="receita")
    lancar(casal, conta, "2026-04-20", 30000, situacao="previsto")
    lancar(casal, conta, "2026-05-05", 50000, tipo="receita", situacao="previsto")

    projecao = futuro(casal)

    assert projecao["saldo_hoje_centavos"] == 100000
    so_previstos = linha(projecao, "so_previstos_centavos")
    assert so_previstos["2026-04-01"] == 70000
    assert so_previstos["2026-05-01"] == 120000
    assert so_previstos["2026-06-01"] == 120000
    assert len(projecao["proximos_meses"]) == 12
    assert projecao["proximos_meses"][-1]["mes"] == "2027-03-01"


def test_previsto_atrasado_conta_no_mes_atual_ate_ser_confirmado(casal: Casal):
    # História 108: a luz de março, sem confirmação, ainda vai sair do bolso.
    conta = casal.conta()
    lancar(casal, conta, "2026-04-01", 100000, tipo="receita")
    luz = lancar(casal, conta, "2026-03-28", 20000, situacao="previsto")
    lancar(casal, conta, "2026-04-05", 5000, situacao="previsto")

    antes = futuro(casal)
    confirmada = casal.pedir("flavio", "POST", f"/api/lancamentos/{luz['id']}/confirmar", json={})
    assert confirmada.status_code == 200, confirmada.text
    depois = futuro(casal)

    assert antes["saldo_hoje_centavos"] == 100000
    assert linha(antes, "so_previstos_centavos")["2026-04-01"] == 75000
    assert depois["saldo_hoje_centavos"] == 80000
    assert linha(depois, "so_previstos_centavos")["2026-04-01"] == 75000


def test_fatura_e_descontada_no_mes_dela(casal: Casal):
    # História 136: o cartão fecha em 25/04 e vence em 05/05; o saldo do fim de abril já
    # desconta a fatura de abril, e o que falta da fatura de março sai no mês atual.
    conta = casal.conta()
    cartao = novo_cartao(casal)["id"]
    lancar(casal, conta, "2026-04-01", 100000, tipo="receita")
    lancar(casal, cartao, "2026-02-26", 3000)  # fatura de março, fechada
    lancar(casal, cartao, "2026-03-28", 10000)  # fatura de abril, aberta
    lancar(casal, cartao, "2026-04-26", 4000)  # fatura de maio
    pagamento = casal.pedir(
        "flavio",
        "POST",
        "/api/transferencias",
        json={
            "id": str(uuid4()),
            "conta_origem_id": conta,
            "conta_destino_id": cartao,
            "valor_centavos": 1000,
            "data": "2026-04-05",
            "fatura_mes": "2026-03-01",
        },
    )
    assert pagamento.status_code == 201, pagamento.text

    projecao = futuro(casal)

    assert projecao["saldo_hoje_centavos"] == 99000
    assert linha(projecao, "faturas_centavos")["2026-04-01"] == 12000
    assert linha(projecao, "faturas_centavos")["2026-05-01"] == 4000
    assert linha(projecao, "so_previstos_centavos")["2026-04-01"] == 87000
    assert linha(projecao, "so_previstos_centavos")["2026-05-01"] == 83000
    assert linha(projecao, "so_previstos_centavos")["2026-06-01"] == 83000


def test_com_planejamento_desconta_o_que_falta_de_cada_item_sem_compensar_o_estourado(
    casal: Casal,
):
    conta = casal.conta()
    alimentacao, lazer = casal.categoria("Alimentação"), casal.categoria("Lazer")
    reserva = casal.categoria("Reserva", "transferencia")
    planejar(casal, "2026-04", alimentacao, 100000)
    # Guardar na reserva é transferência entre contas: a soma delas não muda.
    planejar(casal, "2026-04", reserva, 50000)
    planejar(casal, "2026-05", alimentacao, 80000)
    planejar(casal, "2026-05", lazer, 10000)
    lancar(casal, conta, "2026-04-01", 100000, tipo="receita")
    lancar(casal, conta, "2026-04-03", 30000, categoria=alimentacao)
    lancar(casal, conta, "2026-04-20", 20000, categoria=alimentacao, situacao="previsto")
    # O lazer de maio estoura em 50,00: a sobra da alimentação não cobre.
    lancar(casal, conta, "2026-05-03", 15000, categoria=lazer, situacao="previsto")

    projecao = futuro(casal)

    assert linha(projecao, "planejamento_centavos")["2026-04-01"] == 50000
    assert linha(projecao, "planejamento_centavos")["2026-05-01"] == 80000
    assert linha(projecao, "planejamento_centavos")["2026-06-01"] == 0
    assert linha(projecao, "so_previstos_centavos")["2026-05-01"] == 35000
    com_planejamento = linha(projecao, "com_planejamento_centavos")
    assert com_planejamento["2026-04-01"] == 0
    assert com_planejamento["2026-05-01"] == -95000
    assert com_planejamento["2026-06-01"] == -95000


def conta_com_abertura(casal: Casal, nome: str, saldo: int, data: str) -> str:
    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/contas",
        json={
            "nome": nome,
            "tipo": "corrente",
            "saldo_abertura_centavos": saldo,
            "data_abertura": data,
        },
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["id"]


def test_passado_mostra_o_saldo_realizado_no_fim_de_cada_mes_desde_a_abertura(casal: Casal):
    corrente = conta_com_abertura(casal, "Corrente", 10000, "2025-12-31")
    # A poupança abriu depois: entra na soma só a partir da abertura dela.
    poupanca = conta_com_abertura(casal, "Poupança", 50000, "2026-02-15")
    cartao = novo_cartao(casal)["id"]
    lancar(casal, corrente, "2026-01-15", 100000, tipo="receita")
    lancar(casal, corrente, "2026-02-10", 30000)
    lancar(casal, poupanca, "2026-03-05", 5000)
    # A compra no cartão só sai das contas no pagamento da fatura.
    lancar(casal, cartao, "2026-03-02", 9000)
    transferencia = casal.pedir(
        "flavio",
        "POST",
        "/api/transferencias",
        json={
            "id": str(uuid4()),
            "conta_origem_id": corrente,
            "conta_destino_id": poupanca,
            "valor_centavos": 20000,
            "data": "2026-03-20",
        },
    )
    assert transferencia.status_code == 201, transferencia.text
    lancar(casal, corrente, "2026-04-02", 10000)

    projecao = futuro(casal)

    passado = {m["mes"]: m["saldo_centavos"] for m in projecao["passado"]}
    assert projecao["passado"][0]["mes"] == "2025-04-01"
    assert len(passado) == 12
    # Antes da primeira abertura não há saldo das contas para mostrar (ADR 0007).
    assert passado["2025-11-01"] is None
    assert passado["2025-12-01"] == 10000
    assert passado["2026-01-01"] == 110000
    assert passado["2026-02-01"] == 130000
    assert passado["2026-03-01"] == 125000
    assert projecao["saldo_hoje_centavos"] == 115000


def test_parcelas_e_recorrencia_caem_cada_uma_no_seu_mes_e_o_pagamento_previsto_nao_repete(
    casal: Casal,
):
    conta, cartao = casal.conta(), novo_cartao(casal)["id"]
    parcelamento = casal.pedir(
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
        },
    )
    assert parcelamento.status_code == 201, parcelamento.text
    recorrencia = casal.pedir(
        "flavio",
        "POST",
        "/api/recorrencias",
        json={
            "id": str(uuid4()),
            "tipo": "despesa",
            "valor_centavos": 5000,
            "tipo_do_valor": "estimado",
            "descricao": "Luz",
            "conta_id": conta,
            "categoria_ids": [casal.categoria("Luz")],
            "inicio": "2026-04-20",
            "a_cada": 1,
            "unidade": "meses",
        },
    )
    assert recorrencia.status_code == 201, recorrencia.text
    # A fatura de abril já conta em abril; o pagamento dela, previsto para maio, não conta de novo.
    pagamento = casal.pedir(
        "flavio",
        "POST",
        "/api/transferencias",
        json={
            "id": str(uuid4()),
            "conta_origem_id": conta,
            "conta_destino_id": cartao,
            "valor_centavos": 10000,
            "data": "2026-05-05",
            "situacao": "previsto",
            "fatura_mes": "2026-04-01",
        },
    )
    assert pagamento.status_code == 201, pagamento.text

    projecao = futuro(casal)

    meses = ["2026-04-01", "2026-05-01", "2026-06-01", "2026-07-01"]
    assert [linha(projecao, "faturas_centavos")[m] for m in meses] == [10000, 10000, 10000, 0]
    assert [linha(projecao, "previstos_centavos")[m] for m in meses] == [-5000] * 4
    assert [linha(projecao, "so_previstos_centavos")[m] for m in meses] == [
        -15000,
        -30000,
        -45000,
        -50000,
    ]


def test_ajuste_de_fatura_sai_na_fatura_e_come_o_que_falta_do_planejamento(casal: Casal):
    # O ajuste saiu do bolso sem item (ADR 0008): como no "ainda dá para gastar", ele diminui o
    # que falta do planejamento, para não sair duas vezes.
    cartao = novo_cartao(casal)["id"]
    alimentacao = casal.categoria("Alimentação")
    planejar(casal, "2026-04", alimentacao, 100000)
    lancar(casal, cartao, "2026-04-02", 20000, categoria=alimentacao)
    ajuste = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/cartoes/{cartao}/faturas/2026-04-01",
        json={"ajuste_centavos": 3000},
    )
    assert ajuste.status_code == 200, ajuste.text

    projecao = futuro(casal)

    assert linha(projecao, "faturas_centavos")["2026-04-01"] == 23000
    assert linha(projecao, "planejamento_centavos")["2026-04-01"] == 77000
    assert linha(projecao, "com_planejamento_centavos")["2026-04-01"] == -100000
