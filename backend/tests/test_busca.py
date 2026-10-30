"""A busca em todo o histórico (ticket 59): texto livre e filtros combinados, período pela data da
compra e filtro Fatura à parte (ADR 0013), compra parcelada numa linha, totais e paginação."""

from datetime import date
from uuid import uuid4

import pytest

from app import busca, lancamentos
from tests.conftest import Casal
from tests.test_cartoes import comprar, novo_cartao
from tests.test_contas import transferencia
from tests.test_estorno_e_ajuste import estornar
from tests.test_lancamentos import lancamento
from tests.test_pagamento_de_fatura import pagamento


@pytest.fixture(autouse=True)
def hoje_e_15_de_outubro(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 10, 15))


def buscar(casal: Casal, **criterios) -> dict:
    resposta = casal.pedir("esposa", "POST", "/api/busca", json=criterios)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def lancar(casal: Casal, conta: str, categorias: list[str], **campos) -> dict:
    resposta = casal.pedir(
        "flavio", "POST", "/api/lancamentos", json=lancamento(conta, categorias, **campos)
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def descricoes(resultado: dict) -> list[str]:
    return [
        (linha["lancamento"] or linha["compra_parcelada"] or linha["transferencia"])["descricao"]
        for linha in resultado["linhas"]
    ]


def test_texto_livre_sem_acento_nem_maiuscula_e_filtros_combinados(casal: Casal):
    conta, mercado, farmacia = (
        casal.conta(),
        casal.categoria("Mercado"),
        casal.categoria("Farmácia"),
    )
    lancar(casal, conta, [mercado], descricao="Pão de Açúcar", data="2026-10-02")
    lancar(casal, conta, [farmacia], descricao="Drogaria do Pão", data="2026-10-03")
    lancar(casal, conta, [mercado], descricao="Carrefour", data="2026-10-04")

    assert descricoes(buscar(casal, texto="pao")) == ["Drogaria do Pão", "Pão de Açúcar"]
    # Entre filtros é E; dentro de um filtro, OU.
    assert descricoes(buscar(casal, texto="PÃO", categoria_ids=[mercado])) == ["Pão de Açúcar"]
    assert descricoes(buscar(casal, categoria_ids=[mercado, farmacia])) == [
        "Carrefour",
        "Drogaria do Pão",
        "Pão de Açúcar",
    ]


def test_tags_sem_tag_conta_pessoa_situacao_tipo_e_valor(casal: Casal):
    corrente, poupanca = casal.conta(), casal.conta("Poupança")
    mercado, salario = casal.categoria("Mercado"), casal.categoria("Salário", "receita")
    lancar(casal, corrente, [mercado], descricao="Feira", tags=["Casa"], valor_centavos=5000)
    lancar(casal, corrente, [mercado], descricao="Padaria", pessoa="esposa", valor_centavos=1500)
    lancar(casal, poupanca, [mercado], descricao="Açougue", tags=["churras"], pessoa="flavio")
    lancar(casal, corrente, [salario], tipo="receita", descricao="Salário", data="2026-10-30")

    assert descricoes(buscar(casal, tags=["casa", "CHURRAS"])) == ["Açougue", "Feira"]
    assert descricoes(buscar(casal, tags=["casa"], sem_tag=True)) == [
        "Salário",
        "Padaria",
        "Feira",
    ]
    assert descricoes(buscar(casal, conta_ids=[poupanca])) == ["Açougue"]
    assert descricoes(buscar(casal, pessoas=["esposa"], conjunto=True)) == [
        "Salário",
        "Padaria",
        "Feira",
    ]
    assert descricoes(buscar(casal, pessoas=["flavio"])) == ["Açougue"]
    assert descricoes(buscar(casal, situacoes=["previsto"])) == ["Salário"]
    assert descricoes(buscar(casal, tipos=["receita"])) == ["Salário"]
    assert descricoes(buscar(casal, valor_minimo_centavos=1500, valor_maximo_centavos=5000)) == [
        "Padaria",
        "Feira",
    ]


def test_periodo_pela_data_da_compra_e_fatura_pelo_mes_da_fatura(casal: Casal):
    nubank = novo_cartao(casal)["id"]
    adicional = casal.pedir(
        "flavio", "POST", "/api/cartoes", json={"nome": "Nubank da esposa", "titular_id": nubank}
    ).json()["id"]
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    # A fatura fecha em 25/04: o mercado de 28/03 é da fatura de abril (ADR 0003).
    comprar(casal, nubank, "2026-03-28", descricao="Mercado de março", categoria_ids=[mercado])
    comprar(casal, adicional, "2026-04-02", descricao="Farmácia", categoria_ids=[mercado])
    lancar(casal, conta, [mercado], descricao="Feira de março", data="2026-03-10")
    lancar(casal, conta, [mercado], descricao="Feira de abril", data="2026-04-10")

    marco = buscar(casal, periodo_de="2026-03-01", periodo_ate="2026-03-31")
    assert descricoes(marco) == ["Mercado de março", "Feira de março"]
    assert marco["linhas"][0]["lancamento"]["fatura_mes"] == "2026-04-01"
    # A fatura do titular traz as compras do adicional.
    fatura_de_abril = {"mes": "2026-04-01", "cartao_id": nubank}
    assert descricoes(buscar(casal, fatura=fatura_de_abril)) == ["Farmácia", "Mercado de março"]
    assert descricoes(buscar(casal, fatura={"mes": "2026-03-01", "cartao_id": nubank})) == []
    # Sem cartão, a fatura é o mês em que cada lançamento conta, como na aba Mês.
    assert descricoes(buscar(casal, fatura={"mes": "2026-04-01"})) == [
        "Feira de abril",
        "Farmácia",
        "Mercado de março",
    ]


def parcelar(casal: Casal, conta: str, categorias: list[str], **campos) -> str:
    novo = {
        "id": str(uuid4()),
        "valor_total_centavos": 250000,
        "parcelas": 10,
        "descricao": "Geladeira",
        "conta_id": conta,
        "categoria_ids": categorias,
        "data": "2026-03-04",
    } | campos
    resposta = casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)
    assert resposta.status_code == 201, resposta.text
    return novo["id"]


def test_compra_parcelada_numa_linha_com_o_total_e_parcela_por_linha_no_filtro_fatura(
    casal: Casal,
):
    nubank, eletro = novo_cartao(casal)["id"], casal.categoria("Eletrodomésticos")
    geladeira = parcelar(casal, nubank, [eletro])
    lancar(casal, casal.conta(), [eletro], descricao="Liquidificador", data="2026-03-05")

    resultado = buscar(casal, valor_minimo_centavos=100000)

    # A compra conta pelo valor total, uma vez, e o filtro de valor olha o total.
    assert len(resultado["linhas"]) == 1
    compra = resultado["linhas"][0]["compra_parcelada"]
    assert {k: compra[k] for k in ("parcelamento_id", "descricao", "data", "parcelas")} == {
        "parcelamento_id": geladeira,
        "descricao": "Geladeira",
        "data": "2026-03-04",
        "parcelas": 10,
    }
    assert compra["valor_centavos"] == 250000
    assert [(p["parcela"], p["fatura_mes"]) for p in compra["lancamentos"]][:3] == [
        (1, "2026-03-01"),
        (2, "2026-04-01"),
        (3, "2026-05-01"),
    ]
    assert len(compra["lancamentos"]) == 10
    # No filtro Fatura, cada parcela é uma linha, com o valor dela.
    maio = buscar(casal, fatura={"mes": "2026-05-01", "cartao_id": nubank})
    assert [
        (l["lancamento"]["parcela"], l["lancamento"]["valor_centavos"]) for l in maio["linhas"]
    ] == [(3, 25000)]
    assert buscar(casal, fatura={"mes": "2026-05-01"}, valor_minimo_centavos=100000)["linhas"] == []


def test_periodo_da_compra_parcelada_no_boleto_e_o_da_primeira_parcela(casal: Casal):
    conta, emprestimo = casal.conta(), casal.categoria("Empréstimo")
    parcelar(casal, conta, [emprestimo], parcelas=3, data="2026-11-10", descricao="Empréstimo")

    novembro = buscar(casal, periodo_de="2026-11-01", periodo_ate="2026-11-30")
    assert [p["parcela"] for p in novembro["linhas"][0]["compra_parcelada"]["lancamentos"]] == [
        1,
        2,
        3,
    ]
    assert buscar(casal, periodo_de="2026-12-01", periodo_ate="2026-12-31")["linhas"] == []


def test_totais_no_topo_com_previstos_a_parte_e_o_estorno_diminuindo(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    salario = casal.categoria("Salário", "receita")
    lancar(casal, conta, [mercado], valor_centavos=10000, data="2026-10-02")
    lancar(casal, conta, [mercado], valor_centavos=3000, data="2026-10-20")
    lancar(casal, conta, [salario], tipo="receita", valor_centavos=50000, data="2026-10-05")
    lancar(casal, conta, [salario], tipo="receita", valor_centavos=8000, data="2026-10-30")
    nubank = novo_cartao(casal)["id"]
    compra = comprar(casal, nubank, "2026-10-05", valor_centavos=2000, categoria_ids=[mercado])
    estornar(casal, compra, "2026-10-06", valor_centavos=500)

    assert buscar(casal)["totais"] == {
        "quantidade": 6,
        "despesas": {"realizado_centavos": 11500, "previsto_centavos": 3000},
        "receitas": {"realizado_centavos": 50000, "previsto_centavos": 8000},
        "saldo": {"realizado_centavos": 38500, "previsto_centavos": 5000},
    }


def test_compra_parcelada_conta_o_total_uma_vez_e_a_parcela_no_filtro_fatura(casal: Casal):
    nubank, eletro = novo_cartao(casal)["id"], casal.categoria("Eletrodomésticos")
    parcelar(casal, nubank, [eletro], data="2026-09-04", parcelas=4, valor_total_centavos=100000)

    # Hoje é 15/10: as parcelas das faturas de setembro e outubro já entraram na fatura aberta.
    assert buscar(casal)["totais"]["quantidade"] == 1
    assert buscar(casal)["totais"]["despesas"] == {
        "realizado_centavos": 50000,
        "previsto_centavos": 50000,
    }
    novembro = buscar(casal, fatura={"mes": "2026-11-01", "cartao_id": nubank})["totais"]
    assert (novembro["quantidade"], novembro["despesas"]["previsto_centavos"]) == (1, 25000)


def test_ordena_por_mais_recente_ou_por_valor_em_paginas_sem_teto(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(busca, "POR_PAGINA", 2)
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    for dia, valor in (("01", 300), ("02", 100), ("03", 500), ("04", 200), ("05", 400)):
        lancar(casal, conta, [mercado], descricao=dia, data=f"2026-10-{dia}", valor_centavos=valor)

    paginas = [buscar(casal, pagina=n) for n in range(3)]
    assert [descricoes(p) for p in paginas] == [["05", "04"], ["03", "02"], ["01"]]
    assert [p["tem_mais"] for p in paginas] == [True, True, False]
    # Os totais são do resultado inteiro, em qualquer página.
    assert paginas[2]["totais"]["quantidade"] == 5
    por_valor = [descricoes(buscar(casal, ordem="valor", pagina=n)) for n in range(3)]
    assert por_valor == [["03", "05"], ["01", "04"], ["02"]]


def transferir(casal: Casal, corpo: dict) -> None:
    resposta = casal.pedir("flavio", "POST", "/api/transferencias", json=corpo)
    assert resposta.status_code == 201, resposta.text


def test_transferencia_aparece_fora_dos_totais_e_o_pagamento_de_fatura_so_pelo_tipo(casal: Casal):
    corrente, poupanca = casal.conta(), casal.conta("Poupança")
    reserva = casal.categoria("Reserva", "transferencia")
    mercado, nubank = casal.categoria("Mercado"), novo_cartao(casal)["id"]
    lancar(casal, corrente, [mercado], descricao="Feira", valor_centavos=5000, data="2026-10-01")
    comprar(casal, nubank, "2026-09-28", descricao="Cinema", valor_centavos=2000)
    transferir(casal, transferencia(corrente, poupanca, data="2026-10-03", categoria_id=reserva))
    transferir(casal, pagamento(corrente, nubank, data="2026-10-05", fatura_mes="2026-10-01"))

    tudo = buscar(casal)
    assert descricoes(tudo) == ["Guardar na reserva", "Feira", "Cinema"]
    assert tudo["linhas"][0]["transferencia"]["conta_destino_id"] == poupanca
    assert tudo["totais"]["quantidade"] == 3
    assert tudo["totais"]["despesas"]["realizado_centavos"] == 7000
    assert tudo["totais"]["saldo"]["realizado_centavos"] == -7000
    assert descricoes(buscar(casal, tipos=["transferencia"])) == [
        "Fatura Nubank",
        "Guardar na reserva",
    ]
    assert descricoes(buscar(casal, tipos=["transferencia"], conta_ids=[poupanca])) == [
        "Guardar na reserva"
    ]
    assert descricoes(buscar(casal, categoria_ids=[reserva])) == ["Guardar na reserva"]
    assert descricoes(buscar(casal, tipos=["transferencia"], sem_categoria=True)) == [
        "Fatura Nubank"
    ]
    assert descricoes(buscar(casal, tags=["casa"])) == []
    fatura = {"mes": "2026-10-01", "cartao_id": nubank}
    assert descricoes(buscar(casal, tipos=["transferencia"], fatura=fatura)) == ["Fatura Nubank"]


def test_curinga_no_texto_e_literal_e_o_excluido_nao_aparece(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    lancar(casal, conta, [mercado], descricao="Desconto de 50% na farmácia")
    lancar(casal, conta, [mercado], descricao="Farmácia")
    excluido = lancar(casal, conta, [mercado], descricao="Farmácia de novo")
    resposta = casal.pedir("flavio", "DELETE", f"/api/lancamentos/{excluido['id']}?versao=1")
    assert resposta.status_code == 204, resposta.text

    assert descricoes(buscar(casal, texto="%")) == ["Desconto de 50% na farmácia"]
    assert descricoes(buscar(casal, texto="farmacia")) == [
        "Farmácia",
        "Desconto de 50% na farmácia",
    ]
