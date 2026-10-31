"""A leitura da aba Histórico (ticket 57): uma métrica por vez, pelo mês em que cada lançamento
conta, em 12 meses contra os 12 anteriores, por ano e no mesmo mês de cada ano."""

from datetime import date
from uuid import uuid4

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_aba_mes import lancar
from tests.test_cartoes import comprar, novo_cartao
from tests.test_estorno_e_ajuste import ajustar, estornar


@pytest.fixture(autouse=True)
def hoje_e_15_de_outubro(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 10, 15))


def ler_historico(casal: Casal, **parametros) -> dict:
    resposta = casal.pedir("flavio", "GET", "/api/historico", params=parametros)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def por_mes(historico: dict) -> dict[str, tuple[int, int]]:
    return {m["mes"]: (m["centavos"], m["anterior_centavos"]) for m in historico["doze_meses"]}


def test_despesas_em_12_meses_contra_os_12_anteriores(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    lancar(casal, conta, [mercado], valor_centavos=30000, data="2026-10-02")
    lancar(casal, conta, [mercado], valor_centavos=10000, data="2025-10-20")
    lancar(casal, conta, [mercado], valor_centavos=7000, data="2025-11-05")
    lancar(casal, conta, [mercado], valor_centavos=4000, data="2024-11-05")
    # Fora das duas janelas (antes de nov/2024) e depois do mês atual.
    lancar(casal, conta, [mercado], valor_centavos=999, data="2024-10-31")
    lancar(casal, conta, [mercado], valor_centavos=888, data="2026-11-03")

    historico = ler_historico(casal, metrica="despesas")

    assert historico["metrica"] == "despesas"
    meses = [m["mes"] for m in historico["doze_meses"]]
    assert meses == [f"2025-{m:02d}" for m in range(11, 13)] + [
        f"2026-{m:02d}" for m in range(1, 11)
    ]
    valores = por_mes(historico)
    assert valores["2026-10"] == (30000, 10000)
    assert valores["2025-11"] == (7000, 4000)
    assert valores["2026-03"] == (0, 0)
    assert historico["total_centavos"] == 37000
    assert historico["total_anterior_centavos"] == 14000


def test_so_o_realizado_conta_e_o_mes_atual_vai_ate_hoje(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    lancar(casal, conta, [mercado], valor_centavos=30000, data="2026-10-02")
    # Previsto: depois de hoje (15/10), ainda não aconteceu.
    lancar(casal, conta, [mercado], valor_centavos=20000, data="2026-10-20")

    assert por_mes(ler_historico(casal, metrica="despesas"))["2026-10"] == (30000, 0)


def test_compra_no_cartao_conta_no_mes_da_fatura_com_estorno_e_ajuste(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    mercado = casal.categoria("Mercado")
    compra = comprar(casal, cartao, "2026-03-28", valor_centavos=12000, categoria_ids=[mercado])
    estornar(casal, compra, "2026-04-02", valor_centavos=2000)
    ajustar(casal, cartao, "2026-04-01", 350)

    valores = por_mes(ler_historico(casal, metrica="despesas"))

    assert valores["2026-03"] == (0, 0)
    assert valores["2026-04"] == (10350, 0)


def test_fatura_sem_ajuste_nao_atrapalha_a_soma(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-03-28", valor_centavos=12000, categoria_ids=[casal.categoria("M")])

    assert por_mes(ler_historico(casal, metrica="despesas"))["2026-04"] == (12000, 0)


def test_receitas_e_sobra(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    salario = casal.categoria("Salário", "receita")
    lancar(casal, conta, [salario], tipo="receita", valor_centavos=500000, data="2026-09-05")
    lancar(casal, conta, [mercado], valor_centavos=120000, data="2026-09-06")
    lancar(casal, conta, [salario], tipo="receita", valor_centavos=400000, data="2025-09-05")
    lancar(casal, conta, [mercado], valor_centavos=450000, data="2025-09-06")

    assert por_mes(ler_historico(casal, metrica="receitas"))["2026-09"] == (500000, 400000)
    assert por_mes(ler_historico(casal, metrica="despesas"))["2026-09"] == (120000, 450000)
    # A sobra pode ser negativa.
    assert por_mes(ler_historico(casal, metrica="sobra"))["2026-09"] == (380000, -50000)


def test_uma_categoria_conta_o_lancamento_inteiro_e_sem_o_ajuste_de_fatura(casal: Casal):
    conta = casal.conta()
    mercado, viagem = casal.categoria("Mercado"), casal.categoria("Viagem")
    salario = casal.categoria("Salário", "receita")
    lancar(casal, conta, [mercado, viagem], valor_centavos=15000, data="2026-10-03")
    lancar(casal, conta, [mercado], valor_centavos=5000, data="2025-10-03")
    lancar(casal, conta, [salario], tipo="receita", valor_centavos=700000, data="2026-10-05")
    cartao = novo_cartao(casal)["id"]
    ajustar(casal, cartao, "2026-10-01", 999)

    mercado_ = ler_historico(casal, metrica="categoria", categoria_id=mercado)
    viagem_ = ler_historico(casal, metrica="categoria", categoria_id=viagem)
    salario_ = ler_historico(casal, metrica="categoria", categoria_id=salario)

    assert mercado_["categoria_id"] == mercado
    assert por_mes(mercado_)["2026-10"] == (15000, 5000)
    assert por_mes(viagem_)["2026-10"] == (15000, 0)
    # Categoria de receita soma receitas.
    assert por_mes(salario_)["2026-10"] == (700000, 0)


def test_por_ano_desde_o_primeiro_ano_com_lancamento_e_o_ano_corrente_parcial(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    lancar(casal, conta, [mercado], valor_centavos=1000, data="2019-03-02")
    lancar(casal, conta, [mercado], valor_centavos=2000, data="2019-12-02")
    lancar(casal, conta, [mercado], valor_centavos=5000, data="2021-01-02")
    lancar(casal, conta, [mercado], valor_centavos=7000, data="2026-10-02")

    anos = ler_historico(casal, metrica="despesas")["por_ano"]

    assert anos == [
        {"ano": 2019, "centavos": 3000, "parcial": False},
        {"ano": 2020, "centavos": 0, "parcial": False},
        {"ano": 2021, "centavos": 5000, "parcial": False},
        {"ano": 2022, "centavos": 0, "parcial": False},
        {"ano": 2023, "centavos": 0, "parcial": False},
        {"ano": 2024, "centavos": 0, "parcial": False},
        {"ano": 2025, "centavos": 0, "parcial": False},
        {"ano": 2026, "centavos": 7000, "parcial": True},
    ]


def test_mesmo_mes_em_cada_ano_com_o_mes_pedido_ou_o_atual(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    lancar(casal, conta, [mercado], valor_centavos=1000, data="2024-03-02")
    lancar(casal, conta, [mercado], valor_centavos=4000, data="2026-03-02")
    lancar(casal, conta, [mercado], valor_centavos=9000, data="2025-10-02")
    lancar(casal, conta, [mercado], valor_centavos=3000, data="2026-10-02")

    padrao = ler_historico(casal, metrica="despesas")["mesmo_mes"]
    marco = ler_historico(casal, metrica="despesas", mes_do_ano=3)["mesmo_mes"]

    assert padrao["mes_do_ano"] == 10
    assert padrao["anos"] == [
        {"ano": 2024, "centavos": 0},
        {"ano": 2025, "centavos": 9000},
        {"ano": 2026, "centavos": 3000},
    ]
    assert marco["mes_do_ano"] == 3
    # Em 2026 março já passou; o mês de cada ano não depende de o ano ter acabado.
    assert marco["anos"] == [
        {"ano": 2024, "centavos": 1000},
        {"ano": 2025, "centavos": 0},
        {"ano": 2026, "centavos": 4000},
    ]


def test_banco_vazio_devolve_o_ano_corrente_e_12_meses_zerados(casal: Casal):
    historico = ler_historico(casal, metrica="despesas")

    assert len(historico["doze_meses"]) == 12
    assert {m["centavos"] for m in historico["doze_meses"]} == {0}
    assert historico["por_ano"] == [{"ano": 2026, "centavos": 0, "parcial": True}]
    assert historico["mesmo_mes"]["anos"] == [{"ano": 2026, "centavos": 0}]


def test_categoria_exige_o_id_e_o_id_existente(casal: Casal):
    sem_id = casal.pedir("flavio", "GET", "/api/historico", params={"metrica": "categoria"})
    inexistente = casal.pedir(
        "flavio",
        "GET",
        "/api/historico",
        params={"metrica": "categoria", "categoria_id": str(uuid4())},
    )
    com_id_sobrando = casal.pedir(
        "flavio",
        "GET",
        "/api/historico",
        params={"metrica": "despesas", "categoria_id": str(uuid4())},
    )
    mes_ruim = casal.pedir(
        "flavio", "GET", "/api/historico", params={"metrica": "despesas", "mes_do_ano": 13}
    )

    assert sem_id.status_code == 422
    assert inexistente.status_code == 404
    assert com_id_sobrando.status_code == 422
    assert mes_ruim.status_code == 422


def test_exige_login(casal: Casal):
    assert casal.client.get("/api/historico", params={"metrica": "despesas"}).status_code == 401
