"""A leitura da aba Mês (ticket 54): o mês já somado no servidor, pelo mês em que cada lançamento
conta (no cartão, o da fatura; ADR 0003)."""

from datetime import date
from uuid import uuid4

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_cartoes import comprar, novo_cartao
from tests.test_contas import transferencia
from tests.test_estorno_e_ajuste import ajustar, estornar
from tests.test_lancamentos import lancamento


@pytest.fixture(autouse=True)
def hoje_e_15_de_outubro(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 10, 15))


def ler_mes(casal: Casal, mes: str) -> dict:
    resposta = casal.pedir("flavio", "GET", f"/api/meses/{mes}")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def lancar(casal: Casal, conta: str, categorias: list[str], **campos) -> dict:
    resposta = casal.pedir(
        "flavio", "POST", "/api/lancamentos", json=lancamento(conta, categorias, **campos)
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def planejar(casal: Casal, mes: str, categoria: str, centavos: int) -> None:
    resposta = casal.pedir(
        "flavio",
        "POST",
        f"/api/planejamento/{mes}/itens",
        json={"id": str(uuid4()), "categoria_id": categoria, "valor_centavos": centavos},
    )
    assert resposta.status_code == 201, resposta.text


def test_mes_atual_mostra_despesas_contra_o_planejado_e_receitas_recebidas_e_previstas(
    casal: Casal,
):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    salario = casal.categoria("Salário", "receita")
    planejar(casal, "2026-10", mercado, 100000)
    lancar(casal, conta, [mercado], valor_centavos=30000, data="2026-10-02")
    lancar(casal, conta, [mercado], valor_centavos=20000, data="2026-10-20")
    lancar(casal, conta, [salario], tipo="receita", valor_centavos=500000, data="2026-10-05")
    lancar(casal, conta, [salario], tipo="receita", valor_centavos=80000, data="2026-10-25")

    outubro = ler_mes(casal, "2026-10")

    assert outubro["situacao"] == "atual"
    assert outubro["despesas"] == {
        "realizado_centavos": 30000,
        "previsto_centavos": 20000,
        "planejado_centavos": 100000,
        "livre_centavos": 50000,
    }
    assert outubro["receitas"] == {"realizado_centavos": 500000, "previsto_centavos": 80000}


def test_compra_no_cartao_conta_no_mes_da_fatura_com_o_estorno_e_o_ajuste(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    mercado = casal.categoria("Mercado")
    # A compra de 28/03 numa fatura que fecha em 25/04 é "mercado de abril".
    compra = comprar(casal, cartao, "2026-03-28", valor_centavos=12000, categoria_ids=[mercado])
    estornar(casal, compra, "2026-04-02", valor_centavos=2000)
    ajustar(casal, cartao, "2026-04-01", 350)

    assert ler_mes(casal, "2026-03")["despesas"]["realizado_centavos"] == 0
    abril = ler_mes(casal, "2026-04")
    assert abril["situacao"] == "passado"
    assert abril["despesas"]["realizado_centavos"] == 10350


def test_comparacao_por_categoria_com_o_mes_anterior_e_o_mesmo_mes_do_ano_passado(casal: Casal):
    conta = casal.conta()
    mercado, viagem, farmacia = (
        casal.categoria("Mercado"),
        casal.categoria("Viagem"),
        casal.categoria("Farmácia"),
    )
    lancar(casal, conta, [mercado], valor_centavos=40000, data="2026-10-02")
    # O jantar em Ilhabela tem duas categorias: conta inteiro em cada linha e uma vez no total.
    lancar(casal, conta, [mercado, viagem], valor_centavos=10000, data="2026-10-03")
    lancar(casal, conta, [mercado], valor_centavos=30000, data="2026-09-10")
    lancar(casal, conta, [farmacia], valor_centavos=5000, data="2026-09-11")
    lancar(casal, conta, [mercado], valor_centavos=25000, data="2025-10-20")
    lancar(casal, casal.conta("Poupança"), [mercado], valor_centavos=999, data="2025-11-01")

    comparacao = ler_mes(casal, "2026-10")["comparacao"]

    assert comparacao["anterior"] == "2026-09"
    assert comparacao["ano_passado"] == "2025-10"
    assert comparacao["linhas"] == [
        {
            "categoria_id": mercado,
            "mes_centavos": 50000,
            "anterior_centavos": 30000,
            "ano_passado_centavos": 25000,
        },
        {
            "categoria_id": viagem,
            "mes_centavos": 10000,
            "anterior_centavos": 0,
            "ano_passado_centavos": 0,
        },
        {
            "categoria_id": farmacia,
            "mes_centavos": 0,
            "anterior_centavos": 5000,
            "ano_passado_centavos": 0,
        },
    ]
    assert comparacao["total"] == {
        "mes_centavos": 50000,
        "anterior_centavos": 35000,
        "ano_passado_centavos": 25000,
    }


def test_ranking_por_categoria_tag_e_pessoa_traz_os_lancamentos_de_cada_linha(casal: Casal):
    conta = casal.conta()
    mercado, viagem = casal.categoria("Mercado"), casal.categoria("Viagem")
    salario = casal.categoria("Salário", "receita")
    feira = lancar(casal, conta, [mercado], valor_centavos=8000, data="2026-10-02", pessoa="esposa")
    jantar = lancar(
        casal,
        conta,
        [mercado, viagem],
        valor_centavos=15000,
        data="2026-10-03",
        tags=["ilhabela", "férias"],
        pessoa="flavio",
    )
    hotel = lancar(
        casal, conta, [viagem], valor_centavos=40000, data="2026-10-04", tags=["ilhabela"]
    )
    # Receita e lançamento de outro mês ficam de fora.
    lancar(casal, conta, [salario], tipo="receita", valor_centavos=500000, data="2026-10-05")
    lancar(casal, conta, [mercado], valor_centavos=3000, data="2026-11-01")

    ranking = ler_mes(casal, "2026-10")["ranking"]

    assert ranking["por_categoria"] == [
        {"chave": viagem, "centavos": 55000, "lancamento_ids": [jantar["id"], hotel["id"]]},
        {"chave": mercado, "centavos": 23000, "lancamento_ids": [feira["id"], jantar["id"]]},
    ]
    assert ranking["por_tag"] == [
        {"chave": "ilhabela", "centavos": 55000, "lancamento_ids": [jantar["id"], hotel["id"]]},
        {"chave": "férias", "centavos": 15000, "lancamento_ids": [jantar["id"]]},
    ]
    # Sem pessoa, o lançamento é do conjunto (`chave` vazia).
    assert ranking["por_pessoa"] == [
        {"chave": None, "centavos": 40000, "lancamento_ids": [hotel["id"]]},
        {"chave": "flavio", "centavos": 15000, "lancamento_ids": [jantar["id"]]},
        {"chave": "esposa", "centavos": 8000, "lancamento_ids": [feira["id"]]},
    ]


def transferir(casal: Casal, origem: str, destino: str, **campos) -> None:
    resposta = casal.pedir(
        "flavio", "POST", "/api/transferencias", json=transferencia(origem, destino, **campos)
    )
    assert resposta.status_code == 201, resposta.text


def test_fechamento_do_mes_passado_resume_sobra_guardado_itens_estourados_e_variacoes(
    casal: Casal,
):
    corrente, poupanca = casal.conta(), casal.conta("Poupança", "poupanca")
    mercado, lazer = casal.categoria("Mercado"), casal.categoria("Lazer")
    salario = casal.categoria("Salário", "receita")
    reserva = casal.categoria("Reserva", "transferencia")
    planejar(casal, "2026-09", mercado, 50000)
    planejar(casal, "2026-09", lazer, 30000)
    planejar(casal, "2026-09", salario, 400000)
    lancar(casal, corrente, [salario], tipo="receita", valor_centavos=500000, data="2026-09-05")
    lancar(casal, corrente, [mercado], valor_centavos=62000, data="2026-09-06")
    lancar(casal, corrente, [lazer], valor_centavos=18000, data="2026-09-07")
    lancar(casal, corrente, [lazer], valor_centavos=20000, data="2026-09-08")
    # Guardar na reserva é transferência com categoria; sem categoria, só move o saldo.
    transferir(
        casal, corrente, poupanca, categoria_id=reserva, valor_centavos=100000, data="2026-09-10"
    )
    transferir(casal, corrente, poupanca, valor_centavos=7000, data="2026-09-11")
    lancar(casal, corrente, [mercado], valor_centavos=80000, data="2026-08-06")
    lancar(casal, corrente, [mercado], valor_centavos=125000, data="2025-09-06")

    setembro = ler_mes(casal, "2026-09")

    assert setembro["situacao"] == "passado"
    assert setembro["fechamento"] == {
        "receitas_centavos": 500000,
        "despesas_centavos": 100000,
        "sobra_centavos": 400000,
        "sobra_percentual": 80,
        "guardado_centavos": 100000,
        "previstos": 0,
        "itens_acima": [
            {"categoria_id": mercado, "passou_centavos": 12000},
            {"categoria_id": lazer, "passou_centavos": 8000},
        ],
        "itens_de_despesa": 2,
        "variacao_anterior_percentual": 25,
        "variacao_ano_passado_percentual": -20,
    }
    assert ler_mes(casal, "2026-10")["fechamento"] is None


def test_fechamento_sem_receitas_nem_mes_de_comparacao_nao_inventa_porcentagem(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    lancar(casal, conta, [mercado], valor_centavos=10000, data="2026-09-06")
    # O previsto que ninguém confirmou continua no mês, e o fechamento diz quantos são.
    lancar(casal, conta, [mercado], valor_centavos=500, data="2026-09-07", situacao="previsto")

    fechamento = ler_mes(casal, "2026-09")["fechamento"]

    assert fechamento["despesas_centavos"] == 10500
    assert fechamento["sobra_centavos"] == -10500
    assert fechamento["sobra_percentual"] is None
    assert fechamento["previstos"] == 1
    assert fechamento["variacao_anterior_percentual"] is None
    assert fechamento["variacao_ano_passado_percentual"] is None


def test_a_lista_a_escolher_vem_na_leitura_e_sai_dela_com_a_escolha(casal: Casal):
    conta = casal.conta()
    restaurante, viagem = casal.categoria("Restaurante"), casal.categoria("Viagem")
    planejar(casal, "2026-10", restaurante, 60000)
    planejar(casal, "2026-10", viagem, 200000)
    jantar = lancar(casal, conta, [restaurante, viagem], valor_centavos=25000, data="2026-10-03")

    [a_escolher] = ler_mes(casal, "2026-10")["planejamento"]["a_escolher"]
    assert a_escolher["lancamento_id"] == jantar["id"]
    escolha = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/lancamentos/{jantar['id']}",
        json={"versao": jantar["versao"], "item_categoria_id": viagem},
    )
    assert escolha.status_code == 200, escolha.text

    planejamento = ler_mes(casal, "2026-10")["planejamento"]
    assert planejamento["a_escolher"] == []
    assert {i["categoria_id"]: i["realizado_centavos"] for i in planejamento["itens"]} == {
        restaurante: 0,
        viagem: 25000,
    }


def test_mes_futuro_sem_nada_lancado_vem_zerado(casal: Casal):
    dezembro = ler_mes(casal, "2026-12")

    assert dezembro["situacao"] == "futuro"
    assert dezembro["despesas"] == {
        "realizado_centavos": 0,
        "previsto_centavos": 0,
        "planejado_centavos": 0,
        "livre_centavos": 0,
    }
    assert dezembro["ranking"] == {"por_categoria": [], "por_tag": [], "por_pessoa": []}
    assert dezembro["comparacao"]["linhas"] == []
    assert dezembro["fechamento"] is None
