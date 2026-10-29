"""Recorrência: regra que gera previstos a cada N semanas ou N meses (ADR 0004)."""

from datetime import date
from uuid import uuid4

import pytest

from app import lancamentos
from app.tarefa_diaria import fazer_tarefa_diaria
from tests.conftest import Casal

HOJE = date(2026, 10, 28)


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hoje é 28/10/2026 em São Paulo; o horizonte de 24 meses vai até 28/10/2028."""
    monkeypatch.setattr(lancamentos, "hoje", lambda: HOJE)


def recorrencia(conta: str, categorias: list[str], **campos) -> dict:
    return {
        "id": str(uuid4()),
        "tipo": "despesa",
        "valor_centavos": 18990,
        "tipo_do_valor": "estimado",
        "descricao": "Luz",
        "conta_id": conta,
        "categoria_ids": categorias,
        "inicio": "2026-11-10",
        "a_cada": 1,
        "unidade": "meses",
    } | campos


def gerados(casal: Casal, id: str) -> list[dict]:
    return [
        l
        for l in casal.pedir("esposa", "GET", "/api/lancamentos").json()
        if l["recorrencia_id"] == id
    ][::-1]


def test_recorrencia_mensal_sem_fim_gera_previstos_ate_o_horizonte_com_31_no_ultimo_dia(
    casal: Casal,
):
    conta, aluguel = casal.conta(), casal.categoria("Aluguel")
    nova = recorrencia(conta, [aluguel], descricao="Aluguel", inicio="2026-10-31")

    resposta = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert resposta.status_code == 201
    previstos = gerados(casal, nova["id"])
    assert [l["data"] for l in previstos[:6]] == [
        "2026-10-31",
        "2026-11-30",
        "2026-12-31",
        "2027-01-31",
        "2027-02-28",
        "2027-03-31",
    ]
    # Fevereiro de 2028 tem 29 dias; o último antes do horizonte (28/10/2028) é o de setembro.
    assert [l["data"] for l in previstos[-9:-6]] == ["2028-01-31", "2028-02-29", "2028-03-31"]
    assert previstos[-1]["data"] == "2028-09-30"
    assert len(previstos) == 24
    assert {
        (l["situacao"], l["valor_centavos"], l["descricao"], l["conta_id"], l["criado_por"])
        for l in previstos
    } == {("previsto", 18990, "Aluguel", conta, "flavio")}
    assert {tuple(l["categoria_ids"]) for l in previstos} == {(aluguel,)}
    assert [l["ocorrencia"] for l in previstos] == list(range(1, 25))


def test_recorrencia_a_cada_duas_semanas_termina_na_data_de_fim(casal: Casal):
    conta, diarista = casal.conta(), casal.categoria("Diarista")
    nova = recorrencia(conta, [diarista], inicio="2026-11-02", a_cada=2, unidade="semanas")
    nova |= {"ate": "2026-12-28"}

    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    # 28/12 fica a 8 semanas de 02/11: a data de fim entra.
    assert [l["data"] for l in gerados(casal, nova["id"])] == [
        "2026-11-02",
        "2026-11-16",
        "2026-11-30",
        "2026-12-14",
        "2026-12-28",
    ]


def test_recorrencia_por_tres_vezes_para_na_terceira_mesmo_com_horizonte_sobrando(casal: Casal):
    conta, seguro = casal.conta(), casal.categoria("Seguro")
    nova = recorrencia(conta, [seguro], inicio="2026-11-15", a_cada=6, vezes=3)

    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert [l["data"] for l in gerados(casal, nova["id"])] == [
        "2026-11-15",
        "2027-05-15",
        "2027-11-15",
    ]


def test_automatico_de_valor_fixo_ja_realiza_o_que_passou_e_nao_pede_confirmacao(casal: Casal):
    conta, assinatura = casal.conta(), casal.categoria("Assinaturas")
    nova = recorrencia(
        conta,
        [assinatura],
        descricao="Spotify",
        valor_centavos=2190,
        tipo_do_valor="fixo",
        automatico=True,
        inicio="2026-10-05",
    )
    luz = recorrencia(conta, [assinatura], inicio="2026-10-27")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=luz)

    spotify = gerados(casal, nova["id"])
    assert [(l["data"], l["situacao"], l["automatico"]) for l in spotify[:2]] == [
        ("2026-10-05", "realizado", True),
        ("2026-11-05", "previsto", True),
    ]
    # Só o estimado pede confirmação: a luz de ontem fica atrasada, o Spotify nunca.
    semana = casal.pedir("esposa", "GET", "/api/contas-da-semana").json()["lancamentos"]
    assert [(l["descricao"], l["data"], l["atrasado"]) for l in semana] == [
        ("Luz", "2026-10-27", True)
    ]
    assert not any(l["atrasado"] for l in spotify)
    [saldo] = [c["saldo_centavos"] for c in casal.pedir("flavio", "GET", "/api/contas").json()]
    assert saldo == -2190


def test_recorrencia_de_valor_estimado_nao_pode_ser_automatica(casal: Casal):
    conta, salario = casal.conta(), casal.categoria("Salário", "receita")
    nova = recorrencia(conta, [salario], tipo="receita", tipo_do_valor="estimado", automatico=True)

    resposta = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert resposta.status_code == 422
    assert "valor fixo" in str(resposta.json())
    assert casal.pedir("flavio", "GET", "/api/recorrencias").json() == []


def test_reenviar_a_mesma_recorrencia_devolve_a_gravada_sem_gerar_de_novo(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(
        conta, [luz], tags=["casa nova"], pessoa="esposa", inicio="2026-11-10", vezes=3
    )

    primeira = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    segunda = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert (primeira.status_code, segunda.status_code) == (201, 200)
    assert segunda.json() == primeira.json()
    assert primeira.json() | {"criado_em": None, "alterado_em": None} == nova | {
        "automatico": False,
        "ate": None,
        "criado_por": "flavio",
        "alterado_por": "flavio",
        "criado_em": None,
        "alterado_em": None,
    }
    assert casal.pedir("esposa", "GET", "/api/recorrencias").json() == [primeira.json()]
    previstos = gerados(casal, nova["id"])
    assert len(previstos) == 3
    assert {(tuple(l["tags"]), l["pessoa"]) for l in previstos} == {(("casa nova",), "esposa")}


@pytest.mark.parametrize(
    ("mudar", "motivo"),
    [
        (
            lambda casal, conta: {"categoria_ids": [casal.categoria("Salário", "receita")]},
            "categoria de receita",
        ),
        (lambda casal, conta: {"conta_id": str(uuid4())}, "conta não encontrada"),
        (lambda casal, conta: {"pessoa": "vizinho"}, "pessoa não encontrada"),
        (lambda casal, conta: {"ate": "2026-11-01", "vezes": 2}, "não nos dois"),
        (lambda casal, conta: {"ate": "2026-11-01"}, "antes do início"),
        (lambda casal, conta: {"a_cada": 0}, "a_cada"),
    ],
)
def test_recorrencia_com_regra_ou_ligacao_invalida_e_recusada_sem_gravar(
    casal: Casal, mudar, motivo
):
    conta, luz = casal.conta(), casal.categoria("Luz")
    nova = recorrencia(conta, [luz]) | mudar(casal, conta)

    resposta = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert resposta.status_code == 422
    assert motivo in str(resposta.json())
    assert casal.pedir("flavio", "GET", "/api/recorrencias").json() == []
    assert casal.pedir("flavio", "GET", "/api/lancamentos").json() == []


def no_dia(monkeypatch: pytest.MonkeyPatch, dia: str) -> None:
    monkeypatch.setattr(lancamentos, "hoje", lambda: date.fromisoformat(dia))


def test_tarefa_diaria_estende_o_horizonte_das_recorrencias(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta, luz, seguro = casal.conta(), casal.categoria("Luz"), casal.categoria("Seguro")
    mensal = recorrencia(conta, [luz], inicio="2026-11-10")
    anual = recorrencia(
        conta, [seguro], descricao="Seguro", inicio="2027-02-28", a_cada=12, vezes=3
    )
    casal.pedir("flavio", "POST", "/api/recorrencias", json=mensal)
    casal.pedir("flavio", "POST", "/api/recorrencias", json=anual)
    assert gerados(casal, mensal["id"])[-1]["data"] == "2028-10-10"
    assert [l["data"] for l in gerados(casal, anual["id"])] == ["2027-02-28", "2028-02-28"]

    no_dia(monkeypatch, "2027-03-01")
    fazer_tarefa_diaria(database_url)
    fazer_tarefa_diaria(database_url)

    # Horizonte em 01/03/2029: a luz chega a 10/02/2029 e o seguro, à terceira vez.
    assert gerados(casal, mensal["id"])[-1]["data"] == "2029-02-10"
    assert len(gerados(casal, mensal["id"])) == 28
    assert [l["data"] for l in gerados(casal, anual["id"])] == [
        "2027-02-28",
        "2028-02-28",
        "2029-02-28",
    ]


def test_tarefa_diaria_realiza_o_automatico_na_data_e_deixa_o_estimado_pedindo_confirmacao(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta, assinatura = casal.conta(), casal.categoria("Assinaturas")
    spotify = recorrencia(
        conta,
        [assinatura],
        descricao="Spotify",
        valor_centavos=2190,
        tipo_do_valor="fixo",
        automatico=True,
        inicio="2026-11-05",
    )
    luz = recorrencia(conta, [assinatura], inicio="2026-11-05")
    casal.pedir("flavio", "POST", "/api/recorrencias", json=spotify)
    casal.pedir("esposa", "POST", "/api/recorrencias", json=luz)

    no_dia(monkeypatch, "2026-11-06")
    fazer_tarefa_diaria(database_url)

    [spotify_de_novembro, spotify_de_dezembro] = gerados(casal, spotify["id"])[:2]
    assert (spotify_de_novembro["situacao"], spotify_de_novembro["versao"]) == ("realizado", 2)
    assert spotify_de_novembro["alterado_por"] == "flavio"
    assert spotify_de_dezembro["situacao"] == "previsto"
    [luz_de_novembro] = gerados(casal, luz["id"])[:1]
    assert (luz_de_novembro["situacao"], luz_de_novembro["atrasado"]) == ("previsto", True)
    [saldo] = [c["saldo_centavos"] for c in casal.pedir("flavio", "GET", "/api/contas").json()]
    assert saldo == -2190
    # Quem mudou a situação sem internet, sobre a versão de antes, vê que foi a regra.
    resposta = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/lancamentos/{spotify_de_novembro['id']}",
        json={"versao": 1, "situacao": "previsto"},
    )
    assert resposta.status_code == 409
    assert [(c["campo"], c["origem"]) for c in resposta.json()["campos"]] == [
        ("situacao", "a recorrência Spotify")
    ]


def test_tarefa_diaria_nao_traz_de_volta_nem_realiza_o_previsto_excluido(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta, assinatura = casal.conta(), casal.categoria("Assinaturas")
    spotify = recorrencia(
        conta, [assinatura], tipo_do_valor="fixo", automatico=True, inicio="2026-11-05", vezes=2
    )
    casal.pedir("flavio", "POST", "/api/recorrencias", json=spotify)
    novembro = gerados(casal, spotify["id"])[0]
    casal.pedir("esposa", "DELETE", f"/api/lancamentos/{novembro['id']}")

    no_dia(monkeypatch, "2026-12-05")
    fazer_tarefa_diaria(database_url)

    assert [(l["data"], l["situacao"]) for l in gerados(casal, spotify["id"])] == [
        ("2026-12-05", "realizado")
    ]


def test_recorrencia_semanal_com_muitas_categorias_e_tags_gera_em_mais_de_uma_transacao(
    casal: Casal,
):
    # 1 lançamento + 5 categorias + 5 tags = 11 linhas por previsto: 90 cabem num lote de 1.000,
    # e 24 meses de semanas são 105.
    conta = casal.conta()
    categorias = [casal.categoria(f"Categoria {n}") for n in range(5)]
    nova = recorrencia(
        conta,
        categorias,
        tags=[f"tag {n}" for n in range(5)],
        inicio="2026-10-29",
        unidade="semanas",
    )

    casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    previstos = gerados(casal, nova["id"])
    assert len(previstos) == 105
    assert previstos[-1]["data"] == "2028-10-26"
    assert [l["ocorrencia"] for l in previstos] == list(range(1, 106))


def test_recorrencia_no_cartao_conta_cada_previsto_no_mes_da_fatura(casal: Casal):
    # O Spotify no cartão que fecha no dia 25: o do dia 26 cai na fatura do mês seguinte.
    cartao = casal.pedir(
        "flavio",
        "POST",
        "/api/cartoes",
        json={"nome": "Nubank", "dia_fechamento": 25, "dia_vencimento": 5},
    ).json()["id"]
    nova = recorrencia(
        cartao, [casal.categoria("Assinaturas")], inicio="2026-11-26", vezes=2, descricao="Spotify"
    )

    assert casal.pedir("flavio", "POST", "/api/recorrencias", json=nova).status_code == 201

    assert [(l["data"], l["mes"], l["fatura_mes"]) for l in gerados(casal, nova["id"])] == [
        ("2026-11-26", "2026-12-01", "2026-12-01"),
        ("2026-12-26", "2027-01-01", "2027-01-01"),
    ]
