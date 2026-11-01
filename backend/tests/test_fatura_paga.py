"""A fatura paga não recebe mais eventos; só muda pela correção de fatura (ADR 0021)."""

from dataclasses import dataclass
from datetime import date
from uuid import uuid4

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_cartoes import comprar, lancamento, novo_cartao
from tests.test_contas import nova_conta
from tests.test_pagamento_de_fatura import faturas, numeros, pagamento, pagar
from tests.test_parcelamentos import parcelamento

RECUSA = "a fatura de 04/2026 do Nubank está paga: para mudá-la, use a correção da fatura"


@dataclass
class AbrilPaga:
    conta: str
    cartao: str
    compra: dict
    pagamento: dict


@pytest.fixture
def abril_paga(casal: Casal, monkeypatch: pytest.MonkeyPatch) -> AbrilPaga:
    """Hoje é 10/05: abril fechou em 25/04 com 1.000,00 e o casal pagou 600,00 em 02/05."""
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 5, 10))
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    compra = comprar(casal, cartao, "2026-04-10", valor_centavos=100000)
    pago = pagar(casal, conta, cartao, valor_centavos=60000, data="2026-05-02")
    assert pago.status_code == 201, pago.text
    return AbrilPaga(conta, cartao, compra, pago.json())


def abril(casal: Casal, abril_paga: AbrilPaga) -> tuple:
    return numeros(faturas(casal, abril_paga.cartao)["2026-04-01"])


ABRIL_PAGA = (100000, 0, 60000, 0, "paga")


def recusado(resposta) -> bool:
    return resposta.status_code == 422 and resposta.json()["detail"] == RECUSA


def test_fatura_paga_recusa_pagamento_novo_realizado_ou_previsto(casal: Casal, abril_paga):
    realizado = pagar(casal, abril_paga.conta, abril_paga.cartao, valor_centavos=10000)
    previsto = pagar(
        casal, abril_paga.conta, abril_paga.cartao, valor_centavos=10000, data="2026-05-20"
    )

    assert recusado(realizado) and recusado(previsto)
    assert abril(casal, abril_paga) == ABRIL_PAGA


def test_pagamento_da_fatura_paga_nao_muda_de_valor_nem_sai_fora_da_correcao(
    casal: Casal, abril_paga
):
    comprar(casal, abril_paga.cartao, "2026-05-08", valor_centavos=100000)
    id = abril_paga.pagamento["id"]
    corpo = pagamento(abril_paga.conta, abril_paga.cartao, id=id, data="2026-05-02")

    outro_valor = casal.pedir(
        "flavio", "PUT", f"/api/transferencias/{id}", json=corpo | {"valor_centavos": 50000}
    )
    outra_fatura = casal.pedir(
        "flavio",
        "PUT",
        f"/api/transferencias/{id}",
        json=corpo | {"valor_centavos": 60000, "fatura_mes": "2026-05-01"},
    )
    so_a_descricao = casal.pedir(
        "flavio",
        "PUT",
        f"/api/transferencias/{id}",
        json=corpo | {"valor_centavos": 60000, "descricao": "Fatura de abril"},
    )
    excluido = casal.pedir("flavio", "DELETE", f"/api/transferencias/{id}")

    assert recusado(outro_valor) and recusado(outra_fatura) and recusado(excluido)
    assert so_a_descricao.status_code == 200, so_a_descricao.text
    assert abril(casal, abril_paga) == ABRIL_PAGA


def test_compra_esquecida_que_cairia_na_fatura_paga_e_recusada(casal: Casal, abril_paga):
    esquecida = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(abril_paga.cartao, [casal.categoria()], data="2026-04-20"),
    )
    pela_fila = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos/lote",
        json={
            "acoes": [
                {
                    "acao": "criar",
                    "lancamento": lancamento(
                        abril_paga.cartao, [casal.categoria()], data="2026-04-20"
                    ),
                }
            ]
        },
    ).json()["resultados"][0]

    assert recusado(esquecida)
    assert (pela_fila["resultado"], pela_fila["motivo"]) == ("recusada", RECUSA)
    assert abril(casal, abril_paga) == ABRIL_PAGA


def test_compra_da_fatura_paga_nao_muda_de_valor_de_fatura_nem_sai(casal: Casal, abril_paga):
    compra = abril_paga.compra
    caminho = f"/api/lancamentos/{compra['id']}"

    def editar(**campos):
        return casal.pedir("flavio", "PATCH", caminho, json={"versao": compra["versao"]} | campos)

    outro_valor = editar(valor_centavos=90000)
    outra_fatura = editar(fatura_mes="2026-05-01")
    excluida = casal.pedir("flavio", "DELETE", caminho)
    so_a_descricao = editar(descricao="Mercado do mês")

    assert recusado(outro_valor) and recusado(outra_fatura) and recusado(excluida)
    assert so_a_descricao.status_code == 200, so_a_descricao.text
    assert abril(casal, abril_paga) == ABRIL_PAGA


def test_compra_de_outra_fatura_nao_e_trocada_para_a_paga(casal: Casal, abril_paga):
    maio = comprar(casal, abril_paga.cartao, "2026-05-08", valor_centavos=5000)

    trocada = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{maio['id']}",
        json={"versao": maio["versao"], "data": "2026-04-20"},
    )

    assert recusado(trocada)


def test_estorno_que_cairia_na_fatura_paga_e_recusado_e_o_de_depois_entra(casal: Casal, abril_paga):
    compra = abril_paga.compra

    def estornar(data: str):
        return casal.pedir(
            "flavio",
            "POST",
            "/api/lancamentos",
            json=lancamento(
                abril_paga.cartao,
                compra["categoria_ids"],
                data=data,
                valor_centavos=10000,
                estorno_de=compra["id"],
            ),
        )

    em_abril = estornar("2026-04-20")
    em_maio = estornar("2026-05-08")

    assert recusado(em_abril)
    assert em_maio.status_code == 201, em_maio.text
    assert numeros(faturas(casal, abril_paga.cartao)["2026-05-01"]) == (
        -10000,
        40000,
        0,
        30000,
        "aberta",
    )


def test_ajuste_e_datas_da_fatura_paga_so_mudam_pela_correcao(casal: Casal, abril_paga):
    caminho = f"/api/cartoes/{abril_paga.cartao}/faturas/2026-04-01"

    ajuste = casal.pedir("flavio", "PATCH", caminho, json={"ajuste_centavos": 500})
    fechamento = casal.pedir("flavio", "PATCH", caminho, json={"fechamento": "2026-04-22"})

    assert recusado(ajuste) and recusado(fechamento)
    assert abril(casal, abril_paga) == ABRIL_PAGA


def test_parcelamento_que_cairia_na_fatura_paga_e_recusado(casal: Casal, abril_paga):
    na_paga = casal.pedir(
        "flavio",
        "POST",
        "/api/parcelamentos",
        json=parcelamento(abril_paga.cartao, [casal.categoria()], data="2026-04-20"),
    )

    assert recusado(na_paga)
    assert casal.pedir("esposa", "GET", "/api/parcelamentos").json() == []
    assert abril(casal, abril_paga) == ABRIL_PAGA


def test_parcela_futura_que_cairia_numa_fatura_paga_recusa_o_parcelamento(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    # Hoje é 10/06: abril fechou sem pagamento e maio, paga, fechou depois dela.
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=100000)
    comprar(casal, cartao, "2026-05-08", valor_centavos=50000)
    pagar(casal, conta, cartao, fatura_mes="2026-05-01", valor_centavos=50000, data="2026-06-05")

    # A 1ª parcela cai em abril (fechada, sem pagamento); a 2ª cairia em maio, paga.
    novo = parcelamento(cartao, [casal.categoria()], data="2026-04-20", parcelas=2)
    resposta = casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == (
        "a fatura de 05/2026 do Nubank está paga: para mudá-la, use a correção da fatura"
    )


def test_a_paga_recebe_o_previsto_que_vira_realizado_sem_mudar(casal: Casal, abril_paga):
    """Confirmar uma compra prevista não muda o total da fatura: a paga aceita."""
    prevista = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(
            abril_paga.cartao, [casal.categoria()], data="2026-05-08", situacao="previsto"
        ),
    ).json()

    confirmada = casal.pedir(
        "flavio", "POST", f"/api/lancamentos/{prevista['id']}/confirmar", json={}
    )

    assert confirmada.status_code == 200, confirmada.text


def test_fatura_nao_paga_continua_recebendo_a_compra_esquecida(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 5, 10))
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=100000)

    esquecida = comprar(casal, cartao, "2026-04-20", valor_centavos=2000)

    assert esquecida["fatura_mes"] == "2026-04-01"


def corrigir(casal: Casal, abril_paga: AbrilPaga, mes="2026-04-01", **correcao):
    return casal.pedir(
        "flavio", "POST", f"/api/cartoes/{abril_paga.cartao}/faturas/{mes}/correcao", json=correcao
    )


def o_pagamento(abril_paga: AbrilPaga, **campos) -> dict:
    return {
        "id": abril_paga.pagamento["id"],
        "conta_origem_id": abril_paga.conta,
        "valor_centavos": 60000,
        "data": "2026-05-02",
    } | campos


def test_correcao_muda_pagamento_compra_e_ajuste_de_uma_vez_e_refaz_o_saldo_anterior(
    casal: Casal, abril_paga
):
    comprar(casal, abril_paga.cartao, "2026-05-08", valor_centavos=50000)
    compra = abril_paga.compra
    esquecida = lancamento(
        abril_paga.cartao, [casal.categoria()], data="2026-04-20", valor_centavos=5000
    )

    resposta = corrigir(
        casal,
        abril_paga,
        ajuste_centavos=-1000,
        pagamentos=[o_pagamento(abril_paga, valor_centavos=70000)],
        compras_novas=[esquecida],
        compras_editadas=[
            {"id": compra["id"], "versao": compra["versao"], "valor_centavos": 90000}
        ],
    )

    assert resposta.status_code == 200, resposta.text
    # Compras 900 + 50 esquecidos, ajuste -10: 940,00; pagou 700,00; 240,00 vão para maio.
    assert numeros(resposta.json()) == (94000, 0, 70000, 0, "paga")
    assert {mes: numeros(f) for mes, f in faturas(casal, abril_paga.cartao).items()} == {
        "2026-04-01": (94000, 0, 70000, 0, "paga"),
        "2026-05-01": (50000, 24000, 0, 74000, "aberta"),
    }
    [pago] = [
        t
        for t in casal.pedir("esposa", "GET", "/api/transferencias").json()
        if t["id"] == abril_paga.pagamento["id"]
    ]
    assert (pago["valor_centavos"], pago["situacao"]) == (70000, "realizado")


def test_correcao_troca_os_pagamentos_e_exclui_a_compra(casal: Casal, abril_paga):
    poupanca = nova_conta(casal, "Poupança")["id"]
    engano = lancamento(
        abril_paga.cartao, [casal.categoria()], data="2026-04-20", valor_centavos=20000
    )
    corrigir(casal, abril_paga, compras_novas=[engano])
    compra = abril_paga.compra
    outro_pagamento = {
        "id": str(uuid4()),
        "conta_origem_id": poupanca,
        "valor_centavos": 20000,
        "data": "2026-05-03",
        "descricao": "Resto da fatura",
    }

    # A compra de 1.000,00 era de 800,00, paga com 600,00 da conta e 200,00 da poupança; o
    # engano sai e o pagamento da conta é refeito.
    resposta = corrigir(
        casal,
        abril_paga,
        pagamentos=[o_pagamento(abril_paga), outro_pagamento],
        compras_editadas=[
            {"id": compra["id"], "versao": compra["versao"], "valor_centavos": 80000}
        ],
        compras_excluidas=[{"id": engano["id"]}],
    )

    assert resposta.status_code == 200, resposta.text
    assert numeros(resposta.json()) == (80000, 0, 80000, 0, "paga")
    pagamentos = {
        t["id"]: (t["conta_origem_id"], t["valor_centavos"], t["fatura_mes"])
        for t in casal.pedir("esposa", "GET", "/api/transferencias").json()
    }
    assert pagamentos == {
        abril_paga.pagamento["id"]: (abril_paga.conta, 60000, "2026-04-01"),
        outro_pagamento["id"]: (poupanca, 20000, "2026-04-01"),
    }


def test_correcao_tira_o_pagamento_que_nao_vem_na_lista(casal: Casal, abril_paga):
    novo = o_pagamento(abril_paga, id=str(uuid4()), valor_centavos=50000)

    resposta = corrigir(casal, abril_paga, pagamentos=[novo])

    assert resposta.status_code == 200, resposta.text
    ids = [t["id"] for t in casal.pedir("esposa", "GET", "/api/transferencias").json()]
    assert ids == [novo["id"]]
    assert numeros(resposta.json()) == (100000, 0, 50000, 0, "paga")


def test_correcao_que_deixaria_o_pago_acima_do_total_e_recusada_inteira(casal: Casal, abril_paga):
    compra = abril_paga.compra

    resposta = corrigir(
        casal,
        abril_paga,
        ajuste_centavos=-500,
        compras_editadas=[
            {"id": compra["id"], "versao": compra["versao"], "valor_centavos": 50000}
        ],
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "o pagamento passa do valor da fatura"
    assert abril(casal, abril_paga) == ABRIL_PAGA
    assert faturas(casal, abril_paga.cartao)["2026-04-01"]["ajuste_centavos"] == 0


def test_correcao_e_so_da_fatura_paga_e_nao_tira_todos_os_pagamentos(casal: Casal, abril_paga):
    comprar(casal, abril_paga.cartao, "2026-05-08", valor_centavos=5000)

    aberta = corrigir(casal, abril_paga, mes="2026-05-01", ajuste_centavos=100)
    sem_pagamento = corrigir(casal, abril_paga, pagamentos=[])

    assert aberta.status_code == 422
    assert aberta.json()["detail"] == "só a fatura paga se corrige"
    assert sem_pagamento.status_code == 422
    assert abril(casal, abril_paga) == ABRIL_PAGA


def test_correcao_de_uma_fatura_nao_muda_outra_paga(casal: Casal, monkeypatch):
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=100000)
    maio = comprar(casal, cartao, "2026-05-08", valor_centavos=50000)
    pagar(casal, conta, cartao, valor_centavos=100000, data="2026-05-02")
    pagar(casal, conta, cartao, fatura_mes="2026-05-01", valor_centavos=50000, data="2026-06-05")

    # A correção de abril não serve para mexer na compra de maio, que também está paga.
    resposta = casal.pedir(
        "flavio",
        "POST",
        f"/api/cartoes/{cartao}/faturas/2026-04-01/correcao",
        json={
            "compras_editadas": [
                {"id": maio["id"], "versao": maio["versao"], "valor_centavos": 40000}
            ]
        },
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == (
        "a fatura de 05/2026 do Nubank está paga: para mudá-la, use a correção da fatura"
    )


def test_correcao_nao_reabre_a_fatura(casal: Casal, abril_paga):
    comprar(casal, abril_paga.cartao, "2026-05-08", valor_centavos=5000)

    # Um fechamento depois de hoje (10/05) faria abril voltar a ser aberta.
    resposta = corrigir(casal, abril_paga, fechamento="2026-05-12", vencimento="2026-05-20")

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "a correção não reabre a fatura: ela continua paga"
    assert abril(casal, abril_paga) == ABRIL_PAGA


def test_estorno_avulso_na_fatura_paga_e_recusado_e_o_de_depois_entra(casal: Casal, abril_paga):
    def creditar(data: str):
        return casal.pedir(
            "flavio",
            "POST",
            "/api/lancamentos",
            json=lancamento(
                abril_paga.cartao, [], data=data, valor_centavos=37, estorno_avulso=True
            ),
        )

    em_abril = creditar("2026-04-20")
    em_maio = creditar("2026-05-08")

    assert recusado(em_abril)
    assert em_maio.status_code == 201, em_maio.text
    assert abril(casal, abril_paga) == ABRIL_PAGA
