"""Filtros salvos (ticket 60): buscas com nome, compartilhadas pelo casal."""

from datetime import date
from uuid import uuid4

import pytest

from app import filtros_salvos
from app.filtros_salvos import periodo_de
from tests.conftest import Casal
from tests.test_lancamentos import lancamento


@pytest.fixture(autouse=True)
def hoje_e_15_de_outubro(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(filtros_salvos, "hoje", lambda: date(2026, 10, 15))


def filtro(**campos) -> dict:
    return {
        "id": str(uuid4()),
        "nome": "Mercado do mês",
        "criterios": {"texto": "mercado", "tags": ["Rotina"]},
        "ordem": "valor",
        "periodo_relativo": None,
    } | campos


def listar(casal: Casal, quem: str = "esposa") -> list[dict]:
    resposta = casal.pedir(quem, "GET", "/api/filtros-salvos")
    assert resposta.status_code == 200
    return resposta.json()


def test_o_filtro_salvo_por_um_aparece_para_o_outro_com_criterios_e_ordem(casal: Casal):
    novo = filtro(criterios={"texto": "mercado", "valor_minimo_centavos": 5000})

    criado = casal.pedir("flavio", "POST", "/api/filtros-salvos", json=novo)

    assert criado.status_code == 201
    [visto] = listar(casal)
    assert visto["id"] == novo["id"]
    assert visto["nome"] == "Mercado do mês"
    assert visto["ordem"] == "valor"
    assert visto["criterios"]["texto"] == "mercado"
    assert visto["criterios"]["valor_minimo_centavos"] == 5000
    assert visto["pedido"]["texto"] == "mercado"
    assert visto["pedido"]["ordem"] == "valor"


def test_reenviar_o_mesmo_id_devolve_o_gravado_sem_duplicar(casal: Casal):
    novo = filtro()
    casal.pedir("flavio", "POST", "/api/filtros-salvos", json=novo)

    de_novo = casal.pedir("flavio", "POST", "/api/filtros-salvos", json=novo | {"nome": "Outro"})

    assert de_novo.status_code == 200
    assert [f["nome"] for f in listar(casal)] == ["Mercado do mês"]


def test_o_periodo_fixo_fica_nos_criterios(casal: Casal):
    novo = filtro(criterios={"periodo_de": "2026-01-01", "periodo_ate": "2026-03-31"})

    casal.pedir("flavio", "POST", "/api/filtros-salvos", json=novo)

    [visto] = listar(casal)
    assert visto["periodo_relativo"] is None
    assert (visto["pedido"]["periodo_de"], visto["pedido"]["periodo_ate"]) == (
        "2026-01-01",
        "2026-03-31",
    )


def test_o_periodo_relativo_e_resolvido_na_leitura_e_manda_no_fixo(casal: Casal):
    novo = filtro(
        criterios={"periodo_de": "2019-01-01", "periodo_ate": "2019-01-31"},
        periodo_relativo="este_mes",
    )

    casal.pedir("flavio", "POST", "/api/filtros-salvos", json=novo)

    [visto] = listar(casal)
    assert visto["periodo_relativo"] == "este_mes"
    assert visto["criterios"]["periodo_de"] is None
    assert (visto["pedido"]["periodo_de"], visto["pedido"]["periodo_ate"]) == (
        "2026-10-01",
        "2026-10-31",
    )


@pytest.mark.parametrize(
    ("relativo", "dia", "esperado"),
    [
        ("este_mes", date(2026, 2, 10), (date(2026, 2, 1), date(2026, 2, 28))),
        ("este_mes", date(2028, 2, 10), (date(2028, 2, 1), date(2028, 2, 29))),
        ("mes_passado", date(2026, 1, 15), (date(2025, 12, 1), date(2025, 12, 31))),
        ("mes_passado", date(2026, 3, 31), (date(2026, 2, 1), date(2026, 2, 28))),
        ("este_ano", date(2026, 7, 4), (date(2026, 1, 1), date(2026, 12, 31))),
        ("ultimos_30_dias", date(2026, 3, 30), (date(2026, 3, 1), date(2026, 3, 30))),
    ],
)
def test_periodos_relativos(relativo, dia, esperado):
    assert periodo_de(relativo, dia) == esperado


def test_renomear_vale_para_o_casal_e_mantem_o_resto(casal: Casal):
    novo = filtro()
    casal.pedir("flavio", "POST", "/api/filtros-salvos", json=novo)

    resposta = casal.pedir(
        "esposa", "PUT", f"/api/filtros-salvos/{novo['id']}", json={"nome": "  Compras  "}
    )

    assert resposta.status_code == 200
    [visto] = listar(casal, "flavio")
    assert visto["nome"] == "Compras"
    assert visto["criterios"]["texto"] == "mercado"


def test_renomear_um_que_nao_existe_da_404(casal: Casal):
    resposta = casal.pedir("flavio", "PUT", f"/api/filtros-salvos/{uuid4()}", json={"nome": "x"})

    assert resposta.status_code == 404


def test_nome_vazio_e_recusado(casal: Casal):
    assert (
        casal.pedir("flavio", "POST", "/api/filtros-salvos", json=filtro(nome="   ")).status_code
        == 422
    )
    novo = filtro()
    casal.pedir("flavio", "POST", "/api/filtros-salvos", json=novo)
    assert (
        casal.pedir(
            "flavio", "PUT", f"/api/filtros-salvos/{novo['id']}", json={"nome": " "}
        ).status_code
        == 422
    )


def test_excluir_e_idempotente(casal: Casal):
    novo = filtro()
    casal.pedir("flavio", "POST", "/api/filtros-salvos", json=novo)

    assert casal.pedir("esposa", "DELETE", f"/api/filtros-salvos/{novo['id']}").status_code == 204
    assert casal.pedir("esposa", "DELETE", f"/api/filtros-salvos/{novo['id']}").status_code == 204
    assert listar(casal) == []


def test_a_lista_vem_em_ordem_alfabetica(casal: Casal):
    for nome in ["viagem", "Aluguel", "mercado"]:
        casal.pedir("flavio", "POST", "/api/filtros-salvos", json=filtro(nome=nome))

    assert [f["nome"] for f in listar(casal)] == ["Aluguel", "mercado", "viagem"]


def test_o_pedido_devolvido_roda_na_busca(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(conta, [mercado], descricao="Mercado da esquina", data="2026-10-03"),
    )
    casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(conta, [mercado], descricao="Mercado velho", data="2026-08-03"),
    )
    casal.pedir(
        "flavio",
        "POST",
        "/api/filtros-salvos",
        json=filtro(criterios={"texto": "mercado"}, periodo_relativo="este_mes"),
    )
    [salvo] = listar(casal)

    resultado = casal.pedir("esposa", "POST", "/api/busca", json=salvo["pedido"])

    assert resultado.json()["totais"]["quantidade"] == 1
