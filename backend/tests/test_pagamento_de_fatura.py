from datetime import date
from uuid import uuid4

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_cartoes import comprar, novo_cartao
from tests.test_contas import nova_conta, saldo


@pytest.fixture
def hoje_10_05(monkeypatch: pytest.MonkeyPatch) -> None:
    """Abril fechou em 25/04 e vence em 05/05; maio ainda está aberta."""
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 5, 10))


def pagamento(conta: str, cartao: str, fatura_mes="2026-04-01", **campos) -> dict:
    return {
        "id": str(uuid4()),
        "conta_origem_id": conta,
        "conta_destino_id": cartao,
        "valor_centavos": 10000,
        "data": "2026-05-05",
        "descricao": "Fatura Nubank",
        "fatura_mes": fatura_mes,
    } | campos


def pagar(casal: Casal, conta: str, cartao: str, **campos):
    return casal.pedir(
        "flavio", "POST", "/api/transferencias", json=pagamento(conta, cartao, **campos)
    )


def faturas(casal: Casal, cartao: str) -> dict[str, dict]:
    lista = casal.pedir("esposa", "GET", f"/api/cartoes/{cartao}/faturas").json()
    return {f["mes"]: f for f in lista}


def test_paga_a_fatura_com_uma_transferencia_da_conta_para_o_cartao(casal: Casal, hoje_10_05):
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=10000)

    criado = pagar(casal, conta, cartao)

    assert criado.status_code == 201, criado.text
    corpo = criado.json()
    assert (corpo["conta_destino_id"], corpo["fatura_mes"], corpo["categoria_id"]) == (
        cartao,
        "2026-04-01",
        None,
    )
    assert casal.pedir("esposa", "GET", "/api/transferencias").json() == [corpo]


def test_pagamento_de_fatura_recusa_categoria_fatura_inexistente_e_sem_mes(
    casal: Casal, hoje_10_05
):
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10")
    reserva = casal.categoria("Reserva", "transferencia")

    com_categoria = pagar(casal, conta, cartao, categoria_id=reserva)
    sem_fatura_nascida = pagar(casal, conta, cartao, fatura_mes="2026-07-01")
    sem_mes = pagar(casal, conta, cartao, fatura_mes=None)

    assert com_categoria.status_code == 422
    assert sem_fatura_nascida.status_code == 422
    assert sem_mes.status_code == 422
    assert casal.pedir("esposa", "GET", "/api/transferencias").json() == []


def test_mes_da_fatura_so_vale_com_o_destino_num_cartao(casal: Casal):
    corrente, poupanca = nova_conta(casal)["id"], nova_conta(casal, "Poupança")["id"]

    resposta = pagar(casal, corrente, poupanca)

    assert resposta.status_code == 422


def test_pagamento_recusa_cartao_arquivado_mas_mantem_o_historico(casal: Casal, hoje_10_05):
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)
    comprar(casal, cartao["id"], "2026-04-10")
    existente = pagar(casal, conta, cartao["id"]).json()
    casal.pedir("flavio", "PUT", f"/api/cartoes/{cartao['id']}", json={**cartao, "arquivado": True})

    novo = pagar(casal, conta, cartao["id"])
    editado = casal.pedir(
        "flavio",
        "PUT",
        f"/api/transferencias/{existente['id']}",
        json=pagamento(conta, cartao["id"], id=existente["id"], descricao="Fatura de abril"),
    )

    assert novo.status_code == 422
    assert editado.status_code == 200 and editado.json()["descricao"] == "Fatura de abril"


def test_pagar_o_cartao_adicional_quita_a_fatura_do_titular(casal: Casal, hoje_10_05):
    conta = nova_conta(casal)["id"]
    titular = novo_cartao(casal)["id"]
    adicional = novo_cartao(
        casal, "Nubank adicional", dia_fechamento=None, dia_vencimento=None, titular_id=titular
    )["id"]
    comprar(casal, adicional, "2026-04-10")

    resposta = pagar(casal, conta, adicional)

    assert resposta.status_code == 201, resposta.text


def test_saldo_da_conta_cai_no_dia_do_pagamento_real_e_o_mes_da_fatura_nao_muda(
    casal: Casal, hoje_10_05
):
    conta = nova_conta(casal, saldo_abertura_centavos=100000, data_abertura="2026-04-01")["id"]
    cartao = novo_cartao(casal)["id"]
    compra = comprar(casal, cartao, "2026-04-10", valor_centavos=40000)
    assert saldo(casal, conta) == 100000

    # O vencimento era 05/05; o casal pagou antes, em 02/05.
    pagar(casal, conta, cartao, valor_centavos=40000, data="2026-05-02")

    assert saldo(casal, conta) == 100000 - 40000
    # As compras já eram despesas da fatura: pagar não cria despesa nem muda o mês delas.
    lancamentos_ = casal.pedir("esposa", "GET", "/api/lancamentos").json()
    assert [(l["id"], l["mes"], l["fatura_mes"]) for l in lancamentos_] == [
        (compra["id"], "2026-04-01", "2026-04-01")
    ]


def test_adiantar_com_a_fatura_aberta_mexe_so_no_saldo_da_conta(casal: Casal, hoje_10_05):
    conta = nova_conta(casal, saldo_abertura_centavos=100000, data_abertura="2026-04-01")["id"]
    cartao = novo_cartao(casal)["id"]
    # Hoje é 10/05: a fatura de maio fecha em 25/05 e ainda está aberta.
    compra = comprar(casal, cartao, "2026-05-08", valor_centavos=25000)
    assert compra["fatura_mes"] == "2026-05-01"

    pagar(casal, conta, cartao, fatura_mes="2026-05-01", valor_centavos=25000, data="2026-05-10")

    assert saldo(casal, conta) == 100000 - 25000
    fatura = faturas(casal, cartao)["2026-05-01"]
    assert fatura["situacao"] == "aberta"
    atual = casal.pedir("esposa", "GET", "/api/lancamentos").json()[0]
    assert (atual["mes"], atual["fatura_mes"]) == ("2026-05-01", "2026-05-01")


def test_pagamento_previsto_ainda_nao_mexe_no_saldo(casal: Casal, hoje_10_05):
    conta = nova_conta(casal, saldo_abertura_centavos=100000, data_abertura="2026-04-01")["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=40000)

    pagar(casal, conta, cartao, valor_centavos=40000, data="2026-05-20")

    assert saldo(casal, conta) == 100000


def lancamento_no_cartao(cartao: str, categoria: str, valor: int, data: str, **campos) -> dict:
    return {
        "id": str(uuid4()),
        "tipo": "despesa",
        "valor_centavos": valor,
        "data": data,
        "descricao": "Compra",
        "conta_id": cartao,
        "categoria_ids": [categoria],
    } | campos


def numeros(fatura: dict) -> tuple:
    return tuple(
        fatura[campo]
        for campo in (
            "total_centavos",
            "saldo_anterior_centavos",
            "pago_centavos",
            "a_pagar_centavos",
            "situacao",
        )
    )


def test_pagamento_em_parte_deixa_a_fatura_paga_e_a_sobra_vira_saldo_anterior_da_seguinte(
    casal: Casal, hoje_10_05
):
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=100000)
    comprar(casal, cartao, "2026-05-08", valor_centavos=50000)

    pagar(casal, conta, cartao, valor_centavos=60000, data="2026-05-02")

    assert {mes: numeros(f) for mes, f in faturas(casal, cartao).items()} == {
        # total, saldo anterior, pago, a pagar, situação
        "2026-04-01": (100000, 0, 60000, 0, "paga"),
        "2026-05-01": (50000, 40000, 0, 90000, "aberta"),
    }
    # Abril paga em parte não fica vencida na Hoje.
    hoje = casal.pedir("esposa", "GET", "/api/hoje").json()
    assert hoje["faturas_que_vencem"] == []


def test_fatura_fechada_sem_pagamento_continua_devendo_e_nao_passa_saldo_anterior(
    casal: Casal, hoje_10_05
):
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=100000)
    comprar(casal, cartao, "2026-05-08", valor_centavos=50000)

    assert {mes: numeros(f) for mes, f in faturas(casal, cartao).items()} == {
        "2026-04-01": (100000, 0, 0, 100000, "fechada"),
        "2026-05-01": (50000, 0, 0, 50000, "aberta"),
    }
    hoje = casal.pedir("esposa", "GET", "/api/hoje").json()
    assert [(f["mes"], f["a_pagar_centavos"]) for f in hoje["faturas_que_vencem"]] == [
        ("2026-04-01", 100000)
    ]


def test_pagar_o_total_da_seguinte_com_o_saldo_anterior_dentro_deixa_as_duas_pagas(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 5, 10))
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=100000)
    comprar(casal, cartao, "2026-05-08", valor_centavos=50000)
    pagar(casal, conta, cartao, valor_centavos=60000, data="2026-05-02")

    # Maio fecha em 25/05; em 05/06 o casal paga os 900,00 dela, os 400,00 de abril dentro.
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 5))
    pagar(casal, conta, cartao, fatura_mes="2026-05-01", valor_centavos=90000, data="2026-06-05")

    assert {mes: numeros(f) for mes, f in faturas(casal, cartao).items()} == {
        "2026-04-01": (100000, 0, 60000, 0, "paga"),
        "2026-05-01": (50000, 40000, 90000, 0, "paga"),
    }
    assert casal.pedir("esposa", "GET", "/api/hoje").json()["faturas_que_vencem"] == []


def test_pagamento_lancado_depois_de_a_seguinte_fechar_tambem_passa_a_sobra(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=100000)
    comprar(casal, cartao, "2026-05-08", valor_centavos=50000)

    # Abril e maio já fecharam; o pagamento de abril é lançado só agora.
    pagar(casal, conta, cartao, valor_centavos=60000, data="2026-05-02")

    assert numeros(faturas(casal, cartao)["2026-05-01"]) == (50000, 40000, 0, 90000, "fechada")


def test_a_sobra_pula_os_meses_sem_fatura(casal: Casal, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 7, 10))
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=100000)
    comprar(casal, cartao, "2026-06-08", valor_centavos=50000)

    pagar(casal, conta, cartao, valor_centavos=60000, data="2026-05-02")

    assert numeros(faturas(casal, cartao)["2026-06-01"]) == (50000, 40000, 0, 90000, "fechada")


def test_pagamento_previsto_nao_deixa_a_fatura_paga(casal: Casal, hoje_10_05):
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=10000)
    comprar(casal, cartao, "2026-05-08", valor_centavos=5000)

    pagar(casal, conta, cartao, valor_centavos=10000, data="2026-05-20")

    assert {mes: numeros(f) for mes, f in faturas(casal, cartao).items()} == {
        "2026-04-01": (10000, 0, 0, 10000, "fechada"),
        "2026-05-01": (5000, 0, 0, 5000, "aberta"),
    }


def test_fatura_fechada_de_total_zero_sem_pagamento_fica_fechada(casal: Casal, hoje_10_05):
    cartao = novo_cartao(casal)["id"]
    compra = comprar(casal, cartao, "2026-04-10", valor_centavos=10000)
    casal.pedir("flavio", "DELETE", f"/api/lancamentos/{compra['id']}")

    assert numeros(faturas(casal, cartao)["2026-04-01"]) == (0, 0, 0, 0, "fechada")


def test_pagamento_acima_do_devido_e_recusado(casal: Casal, hoje_10_05):
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=10000)

    a_mais = pagar(casal, conta, cartao, valor_centavos=12000)

    assert a_mais.status_code == 422
    assert a_mais.json()["detail"] == "o pagamento passa do valor da fatura"
    assert numeros(faturas(casal, cartao)["2026-04-01"]) == (10000, 0, 0, 10000, "fechada")


def test_so_a_fatura_fechada_passa_o_que_sobrou_para_a_seguinte(casal: Casal, hoje_10_05):
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-05-08", valor_centavos=5000)
    comprar(casal, cartao, "2026-06-08", valor_centavos=7000)

    # Maio (fecha 25/05) e junho (fecha 25/06) estão abertas: maio ainda pode receber compras.
    assert {mes: numeros(f) for mes, f in faturas(casal, cartao).items()} == {
        "2026-05-01": (5000, 0, 0, 5000, "aberta"),
        "2026-06-01": (7000, 0, 0, 7000, "aberta"),
    }


def test_pagamento_do_adicional_conta_na_fatura_do_titular(casal: Casal, hoje_10_05):
    conta = nova_conta(casal)["id"]
    titular = novo_cartao(casal)["id"]
    adicional = novo_cartao(
        casal, "Adicional", titular_id=titular, dia_fechamento=None, dia_vencimento=None
    )["id"]
    comprar(casal, titular, "2026-04-10", valor_centavos=10000)

    pagar(casal, conta, adicional, valor_centavos=10000)

    assert numeros(faturas(casal, titular)["2026-04-01"]) == (10000, 0, 10000, 0, "paga")


def test_juros_e_iof_do_rotativo_entram_na_fatura_seguinte_e_o_saldo_anterior_nao_conta_de_novo(
    casal: Casal, hoje_10_05
):
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    alimentacao = casal.categoria("Alimentação")
    juros = casal.categoria("Juros e IOF")
    for categoria, valor in [(alimentacao, 100000), (juros, 5000)]:
        casal.pedir(
            "flavio",
            "POST",
            "/api/planejamento/2026-05/itens",
            json={"id": str(uuid4()), "categoria_id": categoria, "valor_centavos": valor},
        )
    mercado = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento_no_cartao(cartao, alimentacao, 10000, "2026-04-10"),
    )
    assert mercado.status_code == 201
    pagar(casal, conta, cartao, valor_centavos=4000)

    # O banco cobra juros e IOF do que ficou no rotativo: lançamentos novos, de 26/04 em diante.
    for valor, descricao in [(300, "Juros do rotativo"), (50, "IOF do rotativo")]:
        casal.pedir(
            "flavio",
            "POST",
            "/api/lancamentos",
            json=lancamento_no_cartao(cartao, juros, valor, "2026-04-26", descricao=descricao),
        )

    maio = faturas(casal, cartao)["2026-05-01"]
    assert numeros(maio) == (350, 6000, 0, 6350, "aberta")
    plano = casal.pedir("esposa", "GET", "/api/planejamento/2026-05").json()["itens"]
    realizado = {i["categoria_id"]: i["realizado_centavos"] for i in plano}
    # Os 60,00 do saldo anterior não são alimentação de maio nem de abril de novo.
    assert realizado == {alimentacao: 0, juros: 350}


def test_a_sobra_da_ultima_fatura_faz_nascer_a_seguinte(casal: Casal, hoje_10_05):
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=100000)

    pagar(casal, conta, cartao, valor_centavos=60000, data="2026-05-02")

    assert {mes: numeros(f) for mes, f in faturas(casal, cartao).items()} == {
        "2026-04-01": (100000, 0, 60000, 0, "paga"),
        "2026-05-01": (0, 40000, 0, 40000, "aberta"),
    }
