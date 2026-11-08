"""A fatura paga não recebe mais eventos; só muda pela correção de fatura (ADR 0021)."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

import psycopg
import pytest

from app import cartoes, lancamentos, recorrencias
from tests.conftest import Casal
from tests.test_cartoes import comprar, lancamento, novo_cartao
from tests.test_contas import nova_conta
from tests.test_pagamento_de_fatura import faturas, numeros, pagamento, pagar
from tests.test_parcelamentos import (
    excluir_parcelamento,
    fazer_tarefa_diaria,
    parcelamento,
    parcelas,
)
from tests.test_recorrencias import gerados, recorrencia

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


def test_correcao_acerta_as_partes_da_compra_junto_com_o_valor(casal: Casal):
    from tests.test_partes_da_compra import compra_com_partes, parte

    with pytest.MonkeyPatch.context() as m:
        m.setattr(lancamentos, "hoje", lambda: date(2026, 5, 10))
        conta = nova_conta(casal)["id"]
        cartao = novo_cartao(casal)["id"]
        roupa, casa = casal.categoria("Roupa"), casal.categoria("Casa")
        partes = [parte([roupa], 60000, descricao="Vestido"), parte([casa], 40000)]
        criada = compra_com_partes(casal, cartao, partes, data="2026-04-10", situacao="realizado")
        assert criada.status_code == 201, criada.text
        compra = criada.json()
        assert (
            pagar(casal, conta, cartao, valor_centavos=60000, data="2026-05-02").status_code == 201
        )

        # Só o valor: as partes deixam de somar a compra e a correção é recusada.
        so_valor = casal.pedir(
            "flavio",
            "POST",
            f"/api/cartoes/{cartao}/faturas/2026-04-01/correcao",
            json={
                "compras_editadas": [
                    {"id": compra["id"], "versao": compra["versao"], "valor_centavos": 90000}
                ]
            },
        )
        assert so_valor.status_code == 422

        # Com a diferença na última parte, a correção passa e as partes somam a compra.
        acertadas = [partes[0], partes[1] | {"valor_centavos": 30000}]
        resposta = casal.pedir(
            "flavio",
            "POST",
            f"/api/cartoes/{cartao}/faturas/2026-04-01/correcao",
            json={
                "compras_editadas": [
                    {
                        "id": compra["id"],
                        "versao": compra["versao"],
                        "valor_centavos": 90000,
                        "partes": acertadas,
                    }
                ]
            },
        )
        assert resposta.status_code == 200, resposta.text
        [vista] = [
            l
            for l in casal.pedir("esposa", "GET", "/api/lancamentos").json()
            if l["id"] == compra["id"]
        ]
        assert vista["valor_centavos"] == 90000
        assert [p["valor_centavos"] for p in vista["partes"]] == [60000, 30000]


def recorrencia_no_cartao(cartao: str, categorias: list[str], dia: str, **campos) -> dict:
    """A recorrência lançada no dia `dia` (a fila que sobe depois), com o início nele."""
    return recorrencia(cartao, categorias, inicio=dia, dia_do_lancamento=dia) | campos


def test_recorrencia_cuja_ocorrencia_do_lancamento_cairia_na_fatura_paga_e_recusada(
    casal: Casal, abril_paga
):
    nova = recorrencia_no_cartao(abril_paga.cartao, [casal.categoria()], "2026-04-20")

    pela_rota = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    pela_fila = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos/lote",
        json={"acoes": [{"acao": "criar_recorrencia", "recorrencia": nova}]},
    ).json()["resultados"][0]

    assert recusado(pela_rota)
    assert (pela_fila["resultado"], pela_fila["motivo"]) == ("recusada", RECUSA)
    assert casal.pedir("esposa", "GET", "/api/recorrencias").json() == []
    assert abril(casal, abril_paga) == ABRIL_PAGA


def test_recorrencia_lancada_depois_do_fechamento_da_paga_entra_na_seguinte(
    casal: Casal, abril_paga
):
    nova = recorrencia_no_cartao(abril_paga.cartao, [casal.categoria()], "2026-04-28")

    criada = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert criada.status_code == 201, criada.text
    [primeira, *_] = gerados(casal, nova["id"])
    assert (primeira["data"], primeira["situacao"]) == ("2026-04-28", "realizado")
    assert abril(casal, abril_paga) == ABRIL_PAGA


def test_alterar_a_recorrencia_deixa_o_atrasado_da_fatura_paga_e_refaz_o_resto(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    # Lançada em 15/04, a luz de 20/04 entrou em abril; em 10/05, abril fechou e foi paga com
    # ela ainda prevista (atrasada).
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 4, 15))
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    nova = recorrencia(cartao, [casal.categoria()], inicio="2026-04-20", vezes=3)
    assert casal.pedir("flavio", "POST", "/api/recorrencias", json=nova).status_code == 201
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 5, 10))
    assert pagar(casal, conta, cartao, valor_centavos=18990, data="2026-05-02").status_code == 201
    antes = numeros(faturas(casal, cartao)["2026-04-01"])

    alterada = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/recorrencias/{nova['id']}",
        json={"a_partir_da_ocorrencia": 1, "valor_centavos": 25000, "descricao": "Energia"},
    )

    assert alterada.status_code == 200, alterada.text
    assert [
        (l["data"], l["valor_centavos"], l["descricao"]) for l in gerados(casal, nova["id"])
    ] == [
        ("2026-04-20", 18990, "Luz"),
        ("2026-05-20", 25000, "Energia"),
        ("2026-06-20", 25000, "Energia"),
    ]
    assert antes == (18990, 0, 18990, 0, "paga")
    assert numeros(faturas(casal, cartao)["2026-04-01"]) == antes


def test_alterar_a_recorrencia_nao_leva_o_atrasado_para_dentro_da_fatura_paga(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    # Abril foi paga com a luz de 20/04; maio fechou sem pagamento com a de 20/05 atrasada.
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 4, 15))
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    nova = recorrencia(cartao, [casal.categoria()], inicio="2026-04-20", vezes=2)
    assert casal.pedir("flavio", "POST", "/api/recorrencias", json=nova).status_code == 201
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 5, 10))
    assert pagar(casal, conta, cartao, valor_centavos=18990, data="2026-05-02").status_code == 201
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))

    # O calendário novo poria a de maio em 22/04, dentro da paga.
    alterada = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/recorrencias/{nova['id']}",
        json={"a_partir_da_ocorrencia": 2, "inicio": "2026-04-22"},
    )

    assert alterada.status_code == 200, alterada.text
    assert [l["data"] for l in gerados(casal, nova["id"])] == ["2026-04-20", "2026-05-20"]
    assert numeros(faturas(casal, cartao)["2026-04-01"]) == (18990, 0, 18990, 0, "paga")


# A correção do parcelamento não mexe na fatura paga (ticket 171).


def tres_faturas_pagas(casal: Casal, monkeypatch: pytest.MonkeyPatch) -> tuple[str, dict]:
    """Hoje é 10/07: 1.000,00 em 10x desde abril, com abril, maio e junho pagas."""
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 7, 10))
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    criado = casal.pedir(
        "flavio",
        "POST",
        "/api/parcelamentos",
        json=parcelamento(cartao, [casal.categoria()], data="2026-03-28", parcelas=10),
    )
    assert criado.status_code == 201, criado.text
    for mes, dia in (
        ("2026-04-01", "2026-05-02"),
        ("2026-05-01", "2026-06-02"),
        ("2026-06-01", "2026-07-02"),
    ):
        pago = pagar(casal, conta, cartao, fatura_mes=mes, valor_centavos=10000, data=dia)
        assert pago.status_code == 201, pago.text
    return cartao, criado.json()


def corrigir_parcelamento(casal: Casal, id: str, **correcao):
    return casal.pedir("flavio", "PATCH", f"/api/parcelamentos/{id}", json=correcao)


def numero_valor_e_fatura(casal: Casal, id: str) -> list[tuple[int, int, str]]:
    return [(p["parcela"], p["valor_centavos"], p["fatura_mes"]) for p in parcelas(casal, id)]


def test_correcao_deixa_intocada_a_parcela_de_fatura_paga(casal: Casal, monkeypatch):
    cartao, criado = tres_faturas_pagas(casal, monkeypatch)
    antes = {m: numeros(f) for m, f in faturas(casal, cartao).items()}

    aviso = corrigir_parcelamento(casal, criado["id"], valor_total_centavos=120000)
    corrigido = corrigir_parcelamento(
        casal, criado["id"], valor_total_centavos=120000, confirmar_realizadas=True
    )

    # Só a 4ª, realizada numa fatura aberta, pede confirmação.
    assert aviso.status_code == 409, aviso.text
    assert [p["parcela"] for p in aviso.json()["parcelas"]] == [4]
    assert corrigido.status_code == 200, corrigido.text
    assert corrigido.json()["parcelas_mantidas"] == 3
    valores = numero_valor_e_fatura(casal, criado["id"])
    assert [v for _, v, _ in valores] == [10000] * 3 + [12000] * 7
    assert sum(v for _, v, _ in valores) == 114000
    assert [f for _, _, f in valores][:3] == ["2026-04-01", "2026-05-01", "2026-06-01"]
    depois = faturas(casal, cartao)
    for mes in ("2026-04-01", "2026-05-01", "2026-06-01"):
        assert numeros(depois[mes]) == antes[mes]


def test_correcao_nao_encolhe_abaixo_da_ultima_parcela_de_fatura_paga(casal: Casal, monkeypatch):
    _, criado = tres_faturas_pagas(casal, monkeypatch)

    encolhido = corrigir_parcelamento(casal, criado["id"], parcelas=2, confirmar_realizadas=True)
    ate_a_ultima = corrigir_parcelamento(casal, criado["id"], parcelas=3, confirmar_realizadas=True)

    assert encolhido.status_code == 422
    assert encolhido.json()["detail"] == (
        "a parcela 3 está numa fatura paga: o parcelamento não fica com menos de 3 parcelas"
        " (para mudá-la, use a correção da fatura)"
    )
    assert ate_a_ultima.status_code == 200, ate_a_ultima.text
    assert [v for _, v, _ in numero_valor_e_fatura(casal, criado["id"])] == [10000] * 3


def test_correcao_que_levaria_parcela_para_a_fatura_paga_e_recusada_antes_de_gravar(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    # Hoje é 10/06: abril fechou sem pagamento e maio, paga, fechou depois dela.
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    from tests.test_alcance_da_mudanca_na_parcela import um_lote_por_parcela

    # Uma parcela por lote: a 2ª, que cairia em maio, só viria no lote seguinte.
    um_lote_por_parcela(monkeypatch)
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=100000)
    comprar(casal, cartao, "2026-05-08", valor_centavos=50000)
    pago = pagar(
        casal, conta, cartao, fatura_mes="2026-05-01", valor_centavos=50000, data="2026-06-05"
    )
    assert pago.status_code == 201, pago.text
    criado = casal.pedir(
        "flavio",
        "POST",
        "/api/parcelamentos",
        json=parcelamento(cartao, [casal.categoria()], data="2026-05-28", parcelas=2),
    ).json()
    antes = numero_valor_e_fatura(casal, criado["id"])

    # A 1ª iria para abril (fechada, sem pagamento); a 2ª, para maio, paga.
    sem_confirmar = corrigir_parcelamento(casal, criado["id"], data="2026-04-20")
    recusada = corrigir_parcelamento(
        casal, criado["id"], data="2026-04-20", confirmar_realizadas=True
    )

    # A recusa vem antes do aviso das realizadas: não adianta confirmar.
    for resposta in (sem_confirmar, recusada):
        assert resposta.status_code == 422, resposta.text
        assert resposta.json()["detail"] == (
            "a fatura de 05/2026 do Nubank está paga: para mudá-la, use a correção da fatura"
        )
    assert numero_valor_e_fatura(casal, criado["id"]) == antes
    [lido] = casal.pedir("flavio", "GET", "/api/parcelamentos").json()
    assert lido["data"] == "2026-05-28"


def test_mudar_o_valor_de_todas_as_parcelas_deixa_as_de_fatura_paga(casal: Casal, monkeypatch):
    from tests.test_alcance_da_mudanca_na_parcela import mudar_parcela

    _, criado = tres_faturas_pagas(casal, monkeypatch)
    quinta = parcelas(casal, criado["id"])[4]

    resposta = mudar_parcela(
        casal, quinta, "todas", valor_centavos=12000, confirmar_realizadas=True
    )

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["parcelas_mantidas"] == 3
    assert [v for _, v, _ in numero_valor_e_fatura(casal, criado["id"])] == (
        [10000] * 3 + [12000] * 7
    )


def test_a_parcela_da_fatura_importada_segue_a_correcao_com_o_aviso(
    casal: Casal, database_url: str, monkeypatch
):
    import psycopg

    _, criado = tres_faturas_pagas(casal, monkeypatch)
    # Abril, sem datas, é a importada do Mobills: paga sem pagamento de fatura.
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "UPDATE faturas SET fechamento = NULL, vencimento = NULL WHERE mes = '2026-04-01'"
        )
        conn.execute("DELETE FROM transferencias WHERE fatura_mes = '2026-04-01'")

    aviso = corrigir_parcelamento(casal, criado["id"], valor_total_centavos=120000)
    corrigido = corrigir_parcelamento(
        casal, criado["id"], valor_total_centavos=120000, confirmar_realizadas=True
    )

    assert [p["parcela"] for p in aviso.json()["parcelas"]] == [1, 4]
    assert corrigido.status_code == 200, corrigido.text
    assert corrigido.json()["parcelas_mantidas"] == 2
    assert [v for _, v, _ in numero_valor_e_fatura(casal, criado["id"])] == (
        [12000] + [10000] * 2 + [12000] * 7
    )


def parcelamento_de_janeiro(casal: Casal, monkeypatch, pagas: list[str], hoje: str) -> tuple:
    """10x de 1.000,00 comprado em 20/01 no cartão que fecha dia 25: a parcela n cai na fatura
    do mês n. Com as parcelas já geradas, o casal paga as faturas de `pagas`, cada uma com o
    valor da parcela, no dia 2 do mês seguinte."""
    monkeypatch.setattr(lancamentos, "hoje", lambda: date.fromisoformat(hoje))
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    novo = parcelamento(
        cartao, [casal.categoria()], data="2026-01-20", parcelas=10, valor_total_centavos=100000
    )
    assert casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo).status_code == 201
    for mes in pagas:
        seguinte = date.fromisoformat(mes).replace(day=2, month=int(mes[5:7]) + 1)
        pago = pagar(
            casal, conta, cartao, fatura_mes=mes, valor_centavos=10000, data=seguinte.isoformat()
        )
        assert pago.status_code == 201, pago.text
    return cartao, novo["id"]


def o_parcelamento(casal: Casal, id: str) -> dict | None:
    lista = casal.pedir("esposa", "GET", "/api/parcelamentos").json()
    return next((p for p in lista if p["id"] == id), None)


def test_excluir_o_parcelamento_deixa_as_parcelas_de_fatura_paga_e_o_encolhe_ate_elas(
    casal: Casal, monkeypatch: pytest.MonkeyPatch, database_url: str
):
    # Hoje é 10/05: janeiro a março estão pagas; abril fechou sem pagamento.
    cartao, id = parcelamento_de_janeiro(
        casal, monkeypatch, ["2026-01-01", "2026-02-01", "2026-03-01"], "2026-05-10"
    )
    antes = {mes: numeros(f) for mes, f in faturas(casal, cartao).items()}

    excluida = excluir_parcelamento(casal, id, confirmar_realizadas=True)
    fazer_tarefa_diaria(database_url)

    assert excluida.status_code == 204, excluida.text
    assert [(l["parcela"], l["fatura_mes"]) for l in parcelas(casal, id)] == [
        (1, "2026-01-01"),
        (2, "2026-02-01"),
        (3, "2026-03-01"),
    ]
    regra = o_parcelamento(casal, id)
    assert (regra["parcelas"], regra["valor_total_centavos"]) == (3, 30000)
    depois = {mes: numeros(f) for mes, f in faturas(casal, cartao).items()}
    for mes in ("2026-01-01", "2026-02-01", "2026-03-01"):
        assert depois[mes] == antes[mes]
    assert depois["2026-04-01"][0] == 0


def test_so_a_primeira_de_fatura_paga_fica_um_2x_sem_a_segunda_que_nao_volta_na_correcao(
    casal: Casal, monkeypatch: pytest.MonkeyPatch, database_url: str
):
    # Hoje é 10/03: só janeiro está paga; fevereiro fechou sem pagamento. O encolhido seria um
    # 1x, que a tabela recusa: fica um 2x com a 2ª excluída uma a uma (decisão do ticket 176).
    _, id = parcelamento_de_janeiro(casal, monkeypatch, ["2026-01-01"], "2026-03-10")

    assert excluir_parcelamento(casal, id, confirmar_realizadas=True).status_code == 204
    fazer_tarefa_diaria(database_url)

    # A que ficou não muda de valor, mesmo com a regra de 2x.
    assert [(l["parcela"], l["valor_centavos"]) for l in parcelas(casal, id)] == [(1, 10000)]
    regra = o_parcelamento(casal, id)
    assert (regra["parcelas"], regra["valor_total_centavos"]) == (2, 10000)

    # A correção parte de 2, como a de qualquer encolhido: não vai a 1x, e a 3x gera a 3ª sem
    # trazer de volta a 2ª nem mexer na da fatura paga.
    um = corrigir_parcelamento(casal, id, parcelas=1, confirmar_realizadas=True)
    tres = corrigir_parcelamento(casal, id, parcelas=3, confirmar_realizadas=True)
    fazer_tarefa_diaria(database_url)

    assert um.status_code == 422
    assert tres.status_code == 200, tres.text
    numeros_e_valores = [(l["parcela"], l["valor_centavos"]) for l in parcelas(casal, id)]
    assert [n for n, _ in numeros_e_valores] == [1, 3]
    assert numeros_e_valores[0] == (1, 10000)


def test_a_parcela_antes_da_ultima_de_fatura_paga_sai_e_o_aviso_diz_quantas_ficam(
    casal: Casal, monkeypatch: pytest.MonkeyPatch, database_url: str
):
    # Hoje é 10/06: janeiro, fevereiro, março e maio estão pagas; abril fechou sem pagamento.
    _, id = parcelamento_de_janeiro(
        casal,
        monkeypatch,
        ["2026-01-01", "2026-02-01", "2026-03-01", "2026-05-01"],
        "2026-06-10",
    )

    aviso = excluir_parcelamento(casal, id)

    assert aviso.status_code == 409
    assert aviso.json() == {
        "motivo": "isto apaga lançamentos já pagos e pode desconfigurar o histórico",
        "parcelas": 6,
        "de_fatura_paga": 0,
        # A de abril, fechada sem pagamento, e a de junho, que entrou na fatura aberta.
        "realizadas": 2,
        "alteradas_a_mao": 0,
        "ficam_de_fatura_paga": 4,
    }
    assert len(parcelas(casal, id)) == 10

    assert excluir_parcelamento(casal, id, confirmar_realizadas=True).status_code == 204
    fazer_tarefa_diaria(database_url)

    # A tarefa diária não divide de novo o total pelas cinco: as da fatura paga ficam como estão.
    assert [(l["parcela"], l["valor_centavos"]) for l in parcelas(casal, id)] == [
        (1, 10000),
        (2, 10000),
        (3, 10000),
        (5, 10000),
    ]
    regra = o_parcelamento(casal, id)
    assert (regra["parcelas"], regra["valor_total_centavos"]) == (5, 40000)
    # Excluir de novo não tira nem pergunta nada: o que ficou é da fatura paga.
    assert excluir_parcelamento(casal, id).status_code == 204
    assert [l["parcela"] for l in parcelas(casal, id)] == [1, 2, 3, 5]


def test_a_parcela_da_fatura_importada_do_mobills_sai_com_o_aviso(
    casal: Casal, monkeypatch: pytest.MonkeyPatch, database_url: str
):
    # Hoje é 10/05: fevereiro está paga pelo pagamento; janeiro é como a importada do Mobills,
    # sem datas, que conta como paga sem pagamento de fatura.
    cartao, id = parcelamento_de_janeiro(casal, monkeypatch, ["2026-02-01"], "2026-05-10")
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "UPDATE faturas SET fechamento = NULL, vencimento = NULL"
            " WHERE cartao_id = %s AND mes = '2026-01-01'",
            (cartao,),
        )

    aviso = excluir_parcelamento(casal, id)

    assert aviso.status_code == 409
    assert {c: aviso.json()[c] for c in ("parcelas", "de_fatura_paga", "ficam_de_fatura_paga")} == {
        "parcelas": 9,
        "de_fatura_paga": 1,
        "ficam_de_fatura_paga": 1,
    }
    assert excluir_parcelamento(casal, id, confirmar_realizadas=True).status_code == 204
    fazer_tarefa_diaria(database_url)
    assert [(l["parcela"], l["valor_centavos"]) for l in parcelas(casal, id)] == [(2, 10000)]
    regra = o_parcelamento(casal, id)
    assert (regra["parcelas"], regra["valor_total_centavos"]) == (2, 10000)
    assert faturas(casal, cartao)["2026-01-01"]["total_centavos"] == 0


def test_sem_parcela_de_fatura_paga_a_exclusao_tira_o_parcelamento(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    # Hoje é 10/05: nenhuma fatura paga; as de janeiro a abril fecharam sem pagamento.
    _, id = parcelamento_de_janeiro(casal, monkeypatch, [], "2026-05-10")

    aviso = excluir_parcelamento(casal, id)
    assert aviso.status_code == 409
    assert (aviso.json()["parcelas"], aviso.json()["ficam_de_fatura_paga"]) == (10, 0)
    assert excluir_parcelamento(casal, id, confirmar_realizadas=True).status_code == 204

    assert parcelas(casal, id) == []
    assert o_parcelamento(casal, id) is None


def test_reenvio_depois_do_pagamento_nao_gera_o_passado_dentro_da_fatura_paga(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    # Hoje é 10/05. A luz lançada em 20/04 foi gravada com abril ainda aberta, mas a geração
    # parou antes do primeiro lote; abril é paga e a fila reenvia (ticket 179).
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 5, 10))
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=100000)
    nova = recorrencia_no_cartao(cartao, [casal.categoria()], "2026-04-20", vezes=3)
    with monkeypatch.context() as queda:
        queda.setattr(recorrencias, "_gerar_um_lote", lambda *_: False)
        criada = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
        assert criada.status_code == 201, criada.text
    assert gerados(casal, nova["id"]) == []
    assert pagar(casal, conta, cartao, valor_centavos=60000, data="2026-05-02").status_code == 201

    reenvio = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos/lote",
        json={"acoes": [{"acao": "criar_recorrencia", "recorrencia": nova}]},
    ).json()["resultados"][0]

    assert reenvio["resultado"] == "aceita", reenvio
    assert [(l["data"], l["situacao"]) for l in gerados(casal, nova["id"])] == [
        ("2026-05-20", "previsto"),
        ("2026-06-20", "previsto"),
    ]
    assert numeros(faturas(casal, cartao)["2026-04-01"]) == (100000, 0, 60000, 0, "paga")


def test_pagamento_entre_os_lotes_nao_leva_o_resto_do_passado_para_a_fatura_paga(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    # Hoje é 10/05. A luz lançada em 20/03 grava uma ocorrência por lote, e a geração para
    # depois do primeiro (a de março); abril é paga e a fila reenvia (ticket 179).
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 5, 10))
    monkeypatch.setattr(recorrencias, "LINHAS_POR_LOTE", 2)
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=100000)
    nova = recorrencia_no_cartao(cartao, [casal.categoria()], "2026-03-20", vezes=3)
    um_lote = recorrencias._gerar_um_lote
    with monkeypatch.context() as queda:
        queda.setattr(recorrencias, "_gerar_um_lote", lambda conn, id: um_lote(conn, id) and False)
        criada = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
        assert criada.status_code == 201, criada.text
    assert [l["data"] for l in gerados(casal, nova["id"])] == ["2026-03-20"]
    pago = pagar(casal, conta, cartao, fatura_mes="2026-04-01", valor_centavos=60000)
    assert pago.status_code == 201, pago.text

    reenvio = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos/lote",
        json={"acoes": [{"acao": "criar_recorrencia", "recorrencia": nova}]},
    ).json()["resultados"][0]

    assert reenvio["resultado"] == "aceita", reenvio
    assert [(l["data"], l["situacao"]) for l in gerados(casal, nova["id"])] == [
        ("2026-03-20", "realizado"),
        ("2026-05-20", "previsto"),
    ]
    assert numeros(faturas(casal, cartao)["2026-04-01"]) == (100000, 0, 60000, 0, "paga")


def a_regra(casal: Casal, id: str) -> dict:
    [regra] = [r for r in casal.pedir("esposa", "GET", "/api/recorrencias").json() if r["id"] == id]
    return regra


def test_a_ocorrencia_pulada_pela_fatura_paga_deixa_o_aviso_na_regra_ate_a_dispensa(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    # Hoje é 10/07. A luz lançada em 20/02 grava uma ocorrência por lote, e cada envio para
    # depois de um lote. Março é paga antes do segundo lote e maio antes do terceiro: as duas
    # ocorrências passam sem virar lançamento e juntam as datas no mesmo aviso (ticket 192).
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 7, 10))
    monkeypatch.setattr(recorrencias, "LINHAS_POR_LOTE", 2)
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-03-10", valor_centavos=100000)
    comprar(casal, cartao, "2026-05-10", valor_centavos=100000)
    nova = recorrencia_no_cartao(cartao, [casal.categoria()], "2026-02-20", vezes=6)
    um_lote = recorrencias._gerar_um_lote

    def reenviar() -> dict:
        return casal.pedir(
            "flavio",
            "POST",
            "/api/lancamentos/lote",
            json={"acoes": [{"acao": "criar_recorrencia", "recorrencia": nova}]},
        ).json()["resultados"][0]

    with monkeypatch.context() as queda:
        # Cada pedido grava um lote e para, como se a conexão caísse depois dele.
        queda.setattr(recorrencias, "_gerar_um_lote", lambda conn, id: um_lote(conn, id) and False)
        criada = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
        assert criada.status_code == 201, criada.text
        assert a_regra(casal, nova["id"])["aviso_da_fatura_paga"] is None
        pago = pagar(casal, conta, cartao, fatura_mes="2026-03-01", valor_centavos=100000)
        assert pago.status_code == 201, pago.text
        assert reenviar()["resultado"] == "aceita"
        assert a_regra(casal, nova["id"])["aviso_da_fatura_paga"] == (
            "Ocorrência não lançada porque a fatura estava paga: 20/03/2026, na fatura de"
            " 03/2026 do Nubank. Lance à mão se precisar."
        )
        pago = pagar(casal, conta, cartao, fatura_mes="2026-05-01", valor_centavos=100000)
        assert pago.status_code == 201, pago.text
        assert reenviar()["resultado"] == "aceita"
    assert reenviar()["resultado"] == "aceita"

    assert [l["data"] for l in gerados(casal, nova["id"])] == [
        "2026-02-20",
        "2026-04-20",
        "2026-06-20",
        "2026-07-20",
    ]
    assert a_regra(casal, nova["id"])["aviso_da_fatura_paga"] == (
        "Ocorrências não lançadas porque a fatura estava paga: 20/03/2026, na fatura de"
        " 03/2026 do Nubank; 20/05/2026, na fatura de 05/2026 do Nubank. Lance à mão se"
        " precisar."
    )

    dispensa = casal.pedir(
        "esposa", "DELETE", f"/api/recorrencias/{nova['id']}/aviso-da-fatura-paga"
    )

    assert dispensa.status_code == 204, dispensa.text
    assert a_regra(casal, nova["id"])["aviso_da_fatura_paga"] is None
    assert [l["data"] for l in gerados(casal, nova["id"])][-1] == "2026-07-20"


def test_dispensar_o_aviso_de_uma_regra_que_nao_existe_e_404(casal: Casal):
    assert (
        casal.pedir("esposa", "DELETE", f"/api/recorrencias/{uuid4()}/aviso-da-fatura-paga")
    ).status_code == 404


def test_a_fatura_paga_no_meio_do_refazer_da_correcao_nao_recebe_a_parcela(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from app import parcelamentos
    from tests.test_alcance_da_mudanca_na_parcela import parcelamento as o_lido
    from tests.test_alcance_da_mudanca_na_parcela import um_lote_por_parcela

    # Hoje é 10/06: as parcelas caem em março, abril e maio, todas fechadas e a pagar.
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    um_lote_por_parcela(monkeypatch)
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    # Abril tem outra compra, para poder ser paga depois que a 2ª sair dela.
    comprar(casal, cartao, "2026-04-10", valor_centavos=10000)
    criado = casal.pedir(
        "flavio",
        "POST",
        "/api/parcelamentos",
        json=parcelamento(
            cartao, [casal.categoria()], data="2026-03-20", parcelas=3, valor_total_centavos=30000
        ),
    )
    assert criado.status_code == 201, criado.text
    id = criado.json()["id"]
    original = parcelamentos._reajustar_um_lote
    lotes = []

    def cai_no_terceiro(*args):
        lotes.append(args)
        if len(lotes) > 2:
            raise RuntimeError("a Lambda caiu")
        return original(*args)

    # A correção leva as parcelas um mês para trás; o pedido cai antes de mexer na 3ª.
    with monkeypatch.context() as queda:
        queda.setattr(parcelamentos, "_reajustar_um_lote", cai_no_terceiro)
        with pytest.raises(RuntimeError):
            corrigir_parcelamento(casal, id, data="2026-02-20", confirmar_realizadas=True)
    # Abril, em que a 3ª entraria, é paga entre o pedido que caiu e a tarefa diária.
    pago = pagar(
        casal, conta, cartao, fatura_mes="2026-04-01", valor_centavos=10000, data="2026-06-05"
    )
    assert pago.status_code == 201, pago.text
    abril_paga = numeros(faturas(casal, cartao)["2026-04-01"])

    fazer_tarefa_diaria(casal.client.app.state.url)

    assert [f for _, _, f in numero_valor_e_fatura(casal, id)] == [
        "2026-02-01",
        "2026-03-01",
        "2026-05-01",
    ]
    assert numeros(faturas(casal, cartao)["2026-04-01"]) == abril_paga
    assert o_lido(casal, id)["mudanca_recusada"] == (
        "a fatura de 04/2026 do Nubank está paga: para mudá-la, use a correção da fatura."
        " A correção do parcelamento parou: da 3ª parcela em diante, as parcelas que faltavam"
        " corrigir ficaram como estavam"
    )

    # A próxima correção, que não leva parcela para abril, tira o aviso.
    corrigido = corrigir_parcelamento(casal, id, data="2026-01-20", confirmar_realizadas=True)
    assert corrigido.status_code == 200, corrigido.text
    assert [f for _, _, f in numero_valor_e_fatura(casal, id)] == [
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
    ]
    assert o_lido(casal, id)["mudanca_recusada"] is None


def test_a_fatura_paga_depois_da_conferencia_para_a_correcao_no_pedido(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from app import parcelamentos
    from tests.test_alcance_da_mudanca_na_parcela import parcelamento as o_lido
    from tests.test_alcance_da_mudanca_na_parcela import um_lote_por_parcela

    # Hoje é 10/06: as parcelas caem em março, abril (paga) e maio.
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    um_lote_por_parcela(monkeypatch)
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=10000)
    criado = casal.pedir(
        "flavio",
        "POST",
        "/api/parcelamentos",
        json=parcelamento(
            cartao, [casal.categoria()], data="2026-03-20", parcelas=3, valor_total_centavos=30000
        ),
    )
    assert criado.status_code == 201, criado.text
    id = criado.json()["id"]
    pago = pagar(
        casal, conta, cartao, fatura_mes="2026-04-01", valor_centavos=20000, data="2026-06-05"
    )
    assert pago.status_code == 201, pago.text
    abril_paga = numeros(faturas(casal, cartao)["2026-04-01"])
    # A conferência de antes de gravar não vê a fatura paga, como se o pagamento viesse depois.
    monkeypatch.setattr(parcelamentos, "_conferir_os_lotes", lambda *_: None)

    resposta = corrigir_parcelamento(casal, id, data="2026-02-20", confirmar_realizadas=True)

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == (
        "a fatura de 04/2026 do Nubank está paga: para mudá-la, use a correção da fatura."
        " A correção foi gravada e as primeiras parcelas mudaram; as que faltavam ficaram como"
        " estavam"
    )
    # A 1ª foi para fevereiro; a 2ª, de abril, fica; a 3ª não entra em abril.
    assert [f for _, _, f in numero_valor_e_fatura(casal, id)] == [
        "2026-02-01",
        "2026-04-01",
        "2026-05-01",
    ]
    assert numeros(faturas(casal, cartao)["2026-04-01"]) == abril_paga
    assert o_lido(casal, id)["mudanca_recusada"].endswith(
        "A correção do parcelamento parou: da 3ª parcela em diante, as parcelas que faltavam"
        " corrigir ficaram como estavam"
    )

    # Sem o pagamento, abril deixa de estar paga (a API não tira o pagamento da paga: só a
    # correção da fatura): a tarefa diária termina a correção e tira a recusa.
    with psycopg.connect(casal.client.app.state.url, autocommit=True) as conn:
        conn.execute("DELETE FROM transferencias WHERE id = %s", (pago.json()["id"],))
    fazer_tarefa_diaria(casal.client.app.state.url)
    assert [f for _, _, f in numero_valor_e_fatura(casal, id)] == [
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
    ]
    assert o_lido(casal, id)["mudanca_recusada"] is None


def test_a_tentativa_diaria_nao_troca_a_recusa_de_uma_mudanca_com_alcance(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from app import parcelamentos
    from tests.test_alcance_da_mudanca_na_parcela import parcelamento as o_lido

    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 6, 10))
    conta = nova_conta(casal)["id"]
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-10", valor_centavos=10000)
    criado = casal.pedir(
        "flavio",
        "POST",
        "/api/parcelamentos",
        json=parcelamento(
            cartao, [casal.categoria()], data="2026-03-20", parcelas=3, valor_total_centavos=30000
        ),
    )
    id = criado.json()["id"]
    pago = pagar(
        casal, conta, cartao, fatura_mes="2026-04-01", valor_centavos=20000, data="2026-06-05"
    )
    assert pago.status_code == 201, pago.text
    monkeypatch.setattr(parcelamentos, "_conferir_os_lotes", lambda *_: None)
    corrigir_parcelamento(casal, id, data="2026-02-20", confirmar_realizadas=True)
    # Uma mudança com alcance, mais nova, recusada depois da correção.
    outra = "a mudança de alcance foi recusada. Da 2ª parcela em diante, ficaram como estavam"
    with psycopg.connect(casal.client.app.state.url, autocommit=True) as conn:
        conn.execute("UPDATE parcelamentos SET mudanca_recusada = %s WHERE id = %s", (outra, id))

    fazer_tarefa_diaria(casal.client.app.state.url)

    assert o_lido(casal, id)["mudanca_recusada"] == outra


def test_credito_avulso_no_mes_seguinte_usa_o_saldo_anterior_da_paga_e_nao_passa_dele(
    casal: Casal, abril_paga
):
    # Abril ficou devendo 400,00, que viram o saldo anterior de maio (ticket 189).
    cria = lambda centavos: casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(abril_paga.cartao, [], data="2026-05-10", valor_centavos=centavos)
        | {"estorno_avulso": True},
    )

    demais = cria(40001)
    cabe = cria(40000)

    assert demais.status_code == 422
    assert cabe.status_code == 201, cabe.text
    maio = numeros(faturas(casal, abril_paga.cartao)["2026-05-01"])
    assert maio[0] == -40000


def test_conferir_sem_gravar_nao_usa_savepoint_nem_deixa_fatura_nascida(
    casal: Casal, abril_paga, monkeypatch: pytest.MonkeyPatch
):
    # O DSQL recusa SAVEPOINT (ticket 201): a conferência não pode abrir transação aninhada.
    from fastapi import HTTPException

    from app import cartoes

    def sem_savepoint(*_a, **_k):
        raise psycopg.errors.FeatureNotSupported("unsupported transaction statement: SAVEPOINT")

    monkeypatch.setattr(psycopg.Connection, "transaction", sem_savepoint)
    with psycopg.connect(casal.client.app.state.url, autocommit=True) as conn:
        titular = UUID(abril_paga.cartao)
        antes = conn.execute("SELECT count(*) FROM faturas").fetchone()[0]

        # Compra em abril paga: recusada, como ao gravar.
        with pytest.raises(HTTPException) as erro:
            cartoes.conferir_sem_gravar(conn, [{(titular, date(2026, 4, 1)): 5000}])
        assert erro.value.detail == RECUSA

        # Compra num mês sem fatura: confere e a fatura simulada não fica gravada.
        cartoes.conferir_sem_gravar(conn, [{(titular, date(2026, 9, 1)): 5000}])
        assert conn.execute("SELECT count(*) FROM faturas").fetchone()[0] == antes


def test_lote_que_toca_a_fatura_paga_e_recusado_e_a_seguinte_entra(casal: Casal, abril_paga):
    acoes = [
        {"acao": "criar", "lancamento": lancamento(abril_paga.cartao, [casal.categoria()], data=d)}
        for d in ("2026-04-20", "2026-05-20")
    ]

    resposta = casal.pedir("flavio", "POST", "/api/lancamentos/lote", json={"acoes": acoes})

    resultados = resposta.json()["resultados"]
    assert [(r["resultado"], r["motivo"]) for r in resultados] == [
        ("recusada", RECUSA),
        ("aceita", None),
    ]


def test_lote_confere_so_a_fatura_do_titular_que_a_acao_toca(
    casal: Casal, abril_paga, monkeypatch: pytest.MonkeyPatch
):
    outro = novo_cartao(casal, "Inter")["id"]
    lidos: list[UUID] = []
    de_verdade = cartoes.faturas_do_titular

    def espiar(conn, titular_id, *args, **kwargs):
        lidos.append(titular_id)
        return de_verdade(conn, titular_id, *args, **kwargs)

    monkeypatch.setattr(cartoes, "faturas_do_titular", espiar)
    nova = lancamento(outro, [casal.categoria()], data="2026-05-12")

    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos/lote",
        json={"acoes": [{"acao": "criar", "lancamento": nova}]},
    )

    assert resposta.json()["resultados"][0]["resultado"] == "aceita"
    assert set(lidos) == {UUID(outro)}
