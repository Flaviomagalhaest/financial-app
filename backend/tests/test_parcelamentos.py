"""Parcelamento: compra ou dívida em N parcelas, cada uma um lançamento (ADR 0004)."""

from datetime import date
from uuid import UUID, uuid4

import pytest

from app import lancamentos
from app.tarefa_diaria import fazer_tarefa_diaria
from tests.conftest import Casal

HOJE = date(2026, 10, 28)


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hoje é 28/10/2026 em São Paulo."""
    monkeypatch.setattr(lancamentos, "hoje", lambda: HOJE)


def parcelamento(conta: str, categorias: list[str], **campos) -> dict:
    return {
        "id": str(uuid4()),
        "valor_total_centavos": 100000,
        "parcelas": 3,
        "descricao": "Empréstimo",
        "conta_id": conta,
        "categoria_ids": categorias,
        "data": "2026-11-10",
    } | campos


def parcelas(casal: Casal, id: str) -> list[dict]:
    return sorted(
        (
            l
            for l in casal.pedir("esposa", "GET", "/api/lancamentos").json()
            if l["parcelamento_id"] == id
        ),
        key=lambda l: l["parcela"],
    )


def test_divida_em_boleto_divide_o_total_com_os_centavos_que_sobram_na_primeira(casal: Casal):
    conta, emprestimo = casal.conta(), casal.categoria("Empréstimo")
    novo = parcelamento(conta, [emprestimo], data="2026-11-30")

    resposta = casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)

    assert resposta.status_code == 201
    # 1.000,00 em 3: 333,33 cada, e o centavo que sobra vai na 1ª.
    assert [
        (l["parcela"], l["parcelas"], l["valor_centavos"], l["data"], l["mes"])
        for l in parcelas(casal, novo["id"])
    ] == [
        (1, 3, 33334, "2026-11-30", "2026-11-01"),
        (2, 3, 33333, "2026-12-30", "2026-12-01"),
        (3, 3, 33333, "2027-01-30", "2027-01-01"),
    ]
    assert {
        (l["situacao"], l["automatico"], l["descricao"], l["conta_id"], tuple(l["categoria_ids"]))
        for l in parcelas(casal, novo["id"])
    } == {("previsto", False, "Empréstimo", conta, (emprestimo,))}


def test_compra_com_juros_pelo_valor_da_parcela_e_reenvio_devolve_o_gravado(casal: Casal):
    conta, eletro = casal.conta(), casal.categoria("Eletrodomésticos")
    novo = parcelamento(
        conta, [eletro], descricao="Geladeira", tags=["casa nova"], pessoa="esposa", parcelas=4
    )
    del novo["valor_total_centavos"]
    novo["valor_da_parcela_centavos"] = 35000

    primeira = casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)
    segunda = casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)

    assert (primeira.status_code, segunda.status_code) == (201, 200)
    assert segunda.json() == primeira.json()
    assert primeira.json() | {"criado_em": None, "alterado_em": None} == {
        "id": novo["id"],
        "tipo": "despesa",
        "valor_total_centavos": 140000,
        "parcelas": 4,
        "data": "2026-11-10",
        "automatico": False,
        "descricao": "Geladeira",
        "conta_id": conta,
        "categoria_ids": [eletro],
        "tags": ["casa nova"],
        "pessoa": "esposa",
        "item_categoria_id": None,
        "criado_por": "flavio",
        "criado_em": None,
        "alterado_por": "flavio",
        "alterado_em": None,
        "parcelas_puladas": 0,
    }
    assert casal.pedir("esposa", "GET", "/api/parcelamentos").json() == [primeira.json()]
    geradas = parcelas(casal, novo["id"])
    assert [l["valor_centavos"] for l in geradas] == [35000] * 4
    assert {(tuple(l["tags"]), l["pessoa"]) for l in geradas} == {(("casa nova",), "esposa")}


def cartao(casal: Casal, **campos) -> str:
    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/cartoes",
        json={"nome": "Nubank", "dia_fechamento": 25, "dia_vencimento": 5} | campos,
    )
    assert resposta.status_code == 201
    return resposta.json()["id"]


def test_no_cartao_cada_parcela_cai_na_fatura_seguinte_com_a_data_da_compra(casal: Casal):
    # Compra em 26/10 no cartão que fecha dia 25: a 1ª parcela cai na fatura de novembro.
    nubank, eletro = cartao(casal), casal.categoria("Eletrodomésticos")
    novo = parcelamento(nubank, [eletro], descricao="Geladeira", data="2026-10-26", parcelas=4)
    novo["valor_total_centavos"] = 400003

    assert casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo).status_code == 201

    assert [
        (l["parcela"], l["valor_centavos"], l["data"], l["fatura_mes"], l["situacao"])
        for l in parcelas(casal, novo["id"])
    ] == [
        (1, 100003, "2026-10-26", "2026-11-01", "realizado"),
        (2, 100000, "2026-10-26", "2026-12-01", "previsto"),
        (3, 100000, "2026-10-26", "2027-01-01", "previsto"),
        (4, 100000, "2026-10-26", "2027-02-01", "previsto"),
    ]
    # O cartão já nasce automático: nada dele pede confirmação.
    assert casal.pedir("flavio", "GET", "/api/parcelamentos").json()[0]["automatico"] is True
    assert all(l["automatico"] and not l["atrasado"] for l in parcelas(casal, novo["id"]))
    assert casal.pedir("esposa", "GET", "/api/hoje").json()["contas_da_semana"] == []
    faturas = casal.pedir("flavio", "GET", f"/api/cartoes/{nubank}/faturas").json()
    assert [f["mes"] for f in faturas] == ["2026-11-01", "2026-12-01", "2027-01-01", "2027-02-01"]


def test_no_cartao_o_parcelamento_nao_pode_pedir_confirmacao(casal: Casal):
    novo = parcelamento(cartao(casal), [casal.categoria()], automatico=False)

    resposta = casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)

    assert resposta.status_code == 422
    assert "automático" in str(resposta.json())
    assert casal.pedir("flavio", "GET", "/api/lancamentos").json() == []


def test_boleto_com_data_no_passado_pula_as_parcelas_que_passaram_e_avisa_quantas(casal: Casal):
    conta, emprestimo = casal.conta(), casal.categoria("Empréstimo")
    novo = parcelamento(conta, [emprestimo], data="2026-08-28", parcelas=5)

    primeira = casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)
    segunda = casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)

    # Agosto e setembro passaram: a 1ª lançada é a 3/5, a de hoje, já realizada.
    assert [
        (l["parcela"], l["parcelas"], l["valor_centavos"], l["data"], l["situacao"])
        for l in parcelas(casal, novo["id"])
    ] == [
        (3, 5, 20000, "2026-10-28", "realizado"),
        (4, 5, 20000, "2026-11-28", "previsto"),
        (5, 5, 20000, "2026-12-28", "previsto"),
    ]
    assert (primeira.status_code, segunda.status_code) == (201, 200)
    assert segunda.json() == primeira.json()
    assert (primeira.json()["valor_total_centavos"], primeira.json()["parcelas_puladas"]) == (
        100000,
        2,
    )
    semana = casal.pedir("esposa", "GET", "/api/hoje").json()["contas_da_semana"]
    assert not any(l["atrasado"] for l in semana)
    [saldo] = [c["saldo_centavos"] for c in casal.pedir("flavio", "GET", "/api/contas").json()]
    assert saldo == -20000


def test_boleto_com_todas_as_parcelas_antes_de_hoje_e_recusado_sem_gravar(casal: Casal):
    conta, emprestimo = casal.conta(), casal.categoria("Empréstimo")
    novo = parcelamento(conta, [emprestimo], data="2026-07-27", parcelas=3)

    resposta = casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "o parcelamento termina antes de hoje"
    assert casal.pedir("flavio", "GET", "/api/parcelamentos").json() == []


def test_boleto_automatico_com_data_no_passado_nao_realiza_o_que_passou(casal: Casal):
    conta, emprestimo = casal.conta(), casal.categoria("Empréstimo")
    consorcio = parcelamento(
        conta, [emprestimo], descricao="Consórcio", data="2026-10-20", automatico=True
    )

    resposta = casal.pedir("flavio", "POST", "/api/parcelamentos", json=consorcio)

    assert resposta.json()["parcelas_puladas"] == 1
    assert [(l["parcela"], l["situacao"]) for l in parcelas(casal, consorcio["id"])] == [
        (2, "previsto"),
        (3, "previsto"),
    ]
    [saldo] = [c["saldo_centavos"] for c in casal.pedir("flavio", "GET", "/api/contas").json()]
    assert saldo == 0


@pytest.mark.parametrize(
    ("mudar", "motivo"),
    [
        (lambda casal: {"valor_da_parcela_centavos": 100}, "um dos dois"),
        (lambda casal: {"valor_total_centavos": None}, "um dos dois"),
        (lambda casal: {"valor_total_centavos": 2}, "um centavo por parcela"),
        (lambda casal: {"parcelas": 1}, "parcelas"),
        (lambda casal: {"parcelas": 421}, "parcelas"),
        (
            lambda casal: {"categoria_ids": [casal.categoria("Salário", "receita")]},
            "categoria de receita",
        ),
        (lambda casal: {"conta_id": str(uuid4())}, "conta não encontrada"),
        (lambda casal: {"pessoa": "vizinho"}, "pessoa não encontrada"),
    ],
)
def test_parcelamento_invalido_e_recusado_sem_gravar(casal: Casal, mudar, motivo):
    novo = parcelamento(casal.conta(), [casal.categoria()]) | mudar(casal)

    resposta = casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)

    assert resposta.status_code == 422
    assert motivo in str(resposta.json())
    assert casal.pedir("flavio", "GET", "/api/parcelamentos").json() == []
    assert casal.pedir("flavio", "GET", "/api/lancamentos").json() == []


def no_dia(monkeypatch: pytest.MonkeyPatch, dia: str) -> None:
    monkeypatch.setattr(lancamentos, "hoje", lambda: date.fromisoformat(dia))


def test_tarefa_diaria_realiza_a_parcela_do_cartao_quando_a_fatura_de_antes_fecha(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    nubank = cartao(casal)
    novo = parcelamento(nubank, [casal.categoria()], descricao="Geladeira", data="2026-10-26")
    casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)

    # A fatura de novembro fecha em 25/11: no dia 24 a 2ª parcela ainda é futura.
    no_dia(monkeypatch, "2026-11-24")
    fazer_tarefa_diaria(database_url)
    assert [l["situacao"] for l in parcelas(casal, novo["id"])] == [
        "realizado",
        "previsto",
        "previsto",
    ]

    no_dia(monkeypatch, "2026-11-25")
    fazer_tarefa_diaria(database_url)
    fazer_tarefa_diaria(database_url)

    [primeira, segunda, terceira] = parcelas(casal, novo["id"])
    assert (segunda["situacao"], segunda["versao"], segunda["alterado_por"]) == (
        "realizado",
        2,
        "flavio",
    )
    assert (primeira["versao"], terceira["situacao"]) == (1, "previsto")
    # Quem mudou a parcela sem internet, sobre a versão de antes, vê que foi a regra.
    resposta = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/lancamentos/{segunda['id']}",
        json={"versao": 1, "situacao": "previsto"},
    )
    assert resposta.status_code == 409
    assert [(c["campo"], c["origem"]) for c in resposta.json()["campos"]] == [
        ("situacao", "o parcelamento Geladeira")
    ]


def test_tarefa_diaria_realiza_a_parcela_automatica_do_boleto_na_data(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta = casal.conta()
    novo = parcelamento(conta, [casal.categoria()], data="2026-11-10", automatico=True)
    casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)

    no_dia(monkeypatch, "2026-12-10")
    fazer_tarefa_diaria(database_url)

    assert [l["situacao"] for l in parcelas(casal, novo["id"])] == [
        "realizado",
        "realizado",
        "previsto",
    ]
    [saldo] = [c["saldo_centavos"] for c in casal.pedir("flavio", "GET", "/api/contas").json()]
    assert saldo == -66667


def test_mudar_o_fechamento_do_cartao_ou_a_data_da_parcela_mantem_cada_parcela_na_sua_fatura(
    casal: Casal,
):
    nubank = cartao(casal)
    novo = parcelamento(nubank, [casal.categoria()], descricao="Geladeira", data="2026-11-24")
    casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)
    assert [l["fatura_mes"] for l in parcelas(casal, novo["id"])] == [
        "2026-11-01",
        "2026-12-01",
        "2027-01-01",
    ]

    # Fechando no dia 20, a compra de 24/11 passa para a fatura de dezembro, e as outras atrás.
    casal.pedir(
        "flavio",
        "PUT",
        f"/api/cartoes/{nubank}",
        json={"nome": "Nubank", "dia_fechamento": 20, "dia_vencimento": 5},
    )
    assert [l["fatura_mes"] for l in parcelas(casal, novo["id"])] == [
        "2026-12-01",
        "2027-01-01",
        "2027-02-01",
    ]

    # A data da compra corrigida numa parcela só: ela segue sendo a 3ª fatura da compra.
    terceira = parcelas(casal, novo["id"])[2]
    resposta = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{terceira['id']}",
        json={"versao": terceira["versao"], "data": "2026-11-19"},
    )
    assert resposta.status_code == 200
    assert (resposta.json()["fatura_mes"], resposta.json()["mes"]) == ("2027-01-01", "2027-01-01")


def test_parcelamento_longo_com_muitas_categorias_e_tags_gera_em_mais_de_uma_transacao(
    casal: Casal,
):
    # 1 parcela + 5 categorias + 5 tags (+ a fatura, no cartão) = 12 linhas: 83 parcelas por lote.
    conta = casal.conta()
    categorias = [casal.categoria(f"Categoria {n}") for n in range(5)]
    novo = parcelamento(
        conta,
        categorias,
        tags=[f"tag {n}" for n in range(5)],
        parcelas=420,
        valor_total_centavos=42000000,
        data="2026-11-05",
    )

    assert casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo).status_code == 201

    geradas = parcelas(casal, novo["id"])
    assert [l["parcela"] for l in geradas] == list(range(1, 421))
    assert geradas[-1]["data"] == "2061-10-05"
    assert sum(l["valor_centavos"] for l in geradas) == 42000000


def test_sem_internet_o_parcelamento_sobe_no_lote_como_um_pedido_so(casal: Casal):
    conta, eletro = casal.conta(), casal.categoria("Eletrodomésticos")
    geladeira = parcelamento(conta, [eletro], descricao="Geladeira", parcelas=10)
    sem_conta = parcelamento(str(uuid4()), [eletro], descricao="Fogão")
    avulso = {
        "id": str(uuid4()),
        "tipo": "despesa",
        "valor_centavos": 1500,
        "data": "2026-10-28",
        "conta_id": conta,
        "categoria_ids": [eletro],
    }
    lote = {
        "acoes": [
            {"acao": "criar_parcelamento", "parcelamento": geladeira},
            {"acao": "criar_parcelamento", "parcelamento": sem_conta},
            {"acao": "criar", "lancamento": avulso},
        ]
    }

    primeiro = casal.pedir("esposa", "POST", "/api/lancamentos/lote", json=lote)
    # A fila repete o lote que ficou sem resposta.
    segundo = casal.pedir("esposa", "POST", "/api/lancamentos/lote", json=lote)

    assert primeiro.status_code == 200
    [aceita, recusada, criada] = primeiro.json()["resultados"]
    assert (aceita["resultado"], aceita["parcelamento"]["id"]) == ("aceita", geladeira["id"])
    assert aceita["parcelamento"]["criado_por"] == "esposa"
    assert recusada["resultado"] == "recusada"
    assert recusada["motivo"] == "conta não encontrada"
    assert criada["resultado"] == "aceita"
    assert [r["resultado"] for r in segundo.json()["resultados"]] == [
        "aceita",
        "recusada",
        "aceita",
    ]
    assert len(parcelas(casal, geladeira["id"])) == 10
    assert len(casal.pedir("esposa", "GET", "/api/lancamentos").json()) == 11


def test_cartao_sem_dia_de_fechamento_recusa_o_parcelamento_sem_gravar_nada(
    casal: Casal, database_url: str
):
    # O cartão do histórico, sem dias padrão: não há como escolher a fatura da 1ª parcela.
    antigo = cartao(casal, dia_fechamento=None, dia_vencimento=None)
    novo = parcelamento(antigo, [casal.categoria()])

    resposta = casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)

    assert resposta.status_code == 422
    assert "fechamento" in resposta.json()["detail"]
    assert casal.pedir("flavio", "GET", "/api/parcelamentos").json() == []
    assert fazer_tarefa_diaria(database_url)["parcelamentos"] == 0


def total(casal: Casal, id: str, situacao: str | None = None) -> int:
    return sum(
        l["valor_centavos"]
        for l in parcelas(casal, id)
        if situacao is None or l["situacao"] == situacao
    )


def test_antecipar_parcelas_do_fim_com_desconto_no_boleto(casal: Casal):
    conta, emprestimo = casal.conta(), casal.categoria("Empréstimo")
    novo = parcelamento(conta, [emprestimo], parcelas=4, valor_total_centavos=400000)
    casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)
    assert total(casal, novo["id"]) == 400000

    # As duas últimas (R$ 2.000,00) saem por R$ 1.800,00, pagas hoje.
    resposta = casal.pedir(
        "flavio",
        "POST",
        f"/api/parcelamentos/{novo['id']}/antecipacoes",
        json={"parcelas": 2, "valor_total_centavos": 180001},
    )

    assert resposta.status_code == 200
    assert [(l["parcela"], l["valor_centavos"]) for l in resposta.json()] == [
        (3, 90001),
        (4, 90000),
    ]
    assert [
        (l["parcela"], l["valor_centavos"], l["situacao"], l["data"], l["mes"])
        for l in parcelas(casal, novo["id"])
    ] == [
        (1, 100000, "previsto", "2026-11-10", "2026-11-01"),
        (2, 100000, "previsto", "2026-12-10", "2026-12-01"),
        (3, 90001, "realizado", "2026-10-28", "2026-10-01"),
        (4, 90000, "realizado", "2026-10-28", "2026-10-01"),
    ]
    # Antes 400.000; depois 200.000 por vir e 180.001 pagos (o desconto de 19.999 abate).
    assert total(casal, novo["id"]) == 200000 + 180001
    assert total(casal, novo["id"], "previsto") == 200000
    assert total(casal, novo["id"], "realizado") == 180001
    [saldo] = [c["saldo_centavos"] for c in casal.pedir("flavio", "GET", "/api/contas").json()]
    assert saldo == -180001


def test_antecipar_na_outra_data_e_no_cartao_conta_na_fatura_em_que_foi_paga(casal: Casal):
    nubank, eletro = cartao(casal), casal.categoria("Eletrodomésticos")
    novo = parcelamento(
        nubank, [eletro], data="2026-10-26", parcelas=4, valor_total_centavos=400000
    )
    casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)

    # Pagas em 26/10, depois do fechamento de 25/10: contam na fatura de novembro, com a 1ª.
    resposta = casal.pedir(
        "flavio",
        "POST",
        f"/api/parcelamentos/{novo['id']}/antecipacoes",
        json={"parcelas": 2, "data": "2026-10-26", "valor_total_centavos": 150000},
    )

    assert resposta.status_code == 200
    assert [
        (l["parcela"], l["valor_centavos"], l["situacao"], l["fatura_mes"])
        for l in parcelas(casal, novo["id"])
    ] == [
        (1, 100000, "realizado", "2026-11-01"),
        (2, 100000, "previsto", "2026-12-01"),
        (3, 75000, "realizado", "2026-11-01"),
        (4, 75000, "realizado", "2026-11-01"),
    ]
    faturas = casal.pedir("flavio", "GET", f"/api/cartoes/{nubank}/faturas").json()
    assert [(f["mes"], f["compras_centavos"]) for f in faturas] == [
        ("2026-11-01", 250000),
        ("2026-12-01", 100000),
        ("2027-01-01", 0),
        ("2027-02-01", 0),
    ]
    # A troca de fatura fica à mão: redistribuir pelas datas do cartão não a desfaz.
    casal.pedir(
        "flavio",
        "PUT",
        f"/api/cartoes/{nubank}",
        json={"nome": "Nubank", "dia_fechamento": 20, "dia_vencimento": 5},
    )
    assert [l["fatura_mes"] for l in parcelas(casal, novo["id"])][2:] == [
        "2026-11-01",
        "2026-11-01",
    ]


def test_quitar_o_restante_de_uma_vez(casal: Casal):
    conta, emprestimo = casal.conta(), casal.categoria("Empréstimo")
    novo = parcelamento(conta, [emprestimo], parcelas=4, valor_total_centavos=400000)
    casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)
    primeira = parcelas(casal, novo["id"])[0]
    casal.pedir(
        "flavio",
        "POST",
        f"/api/lancamentos/{primeira['id']}/confirmar",
        json={"versao": primeira["versao"]},
    )

    resposta = casal.pedir(
        "flavio",
        "POST",
        f"/api/parcelamentos/{novo['id']}/quitacao",
        json={"valor_total_centavos": 270000},
    )

    assert resposta.status_code == 200
    assert [(l["parcela"], l["valor_centavos"]) for l in resposta.json()] == [
        (2, 90000),
        (3, 90000),
        (4, 90000),
    ]
    assert total(casal, novo["id"], "previsto") == 0
    assert total(casal, novo["id"], "realizado") == 100000 + 270000
    # Sem valor informado, quita pelo que faltava.
    outro = parcelamento(conta, [emprestimo], parcelas=3, valor_total_centavos=300000)
    casal.pedir("flavio", "POST", "/api/parcelamentos", json=outro)
    sem_valor = casal.pedir("flavio", "POST", f"/api/parcelamentos/{outro['id']}/quitacao", json={})
    assert sem_valor.status_code == 200
    assert total(casal, outro["id"], "realizado") == 300000


@pytest.mark.parametrize(
    "corpo",
    [
        {"parcelas": 4},  # só há 3 previstas
        {"parcelas": 0},
        {"parcelas": 1, "valor_total_centavos": 0},
        {"parcelas": 1, "data": "2026-10-29"},  # data futura
    ],
)
def test_antecipacao_invalida_e_recusada_sem_mexer_nas_parcelas(casal: Casal, corpo):
    conta, emprestimo = casal.conta(), casal.categoria("Empréstimo")
    novo = parcelamento(conta, [emprestimo])
    casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)
    antes = parcelas(casal, novo["id"])

    resposta = casal.pedir(
        "flavio", "POST", f"/api/parcelamentos/{novo['id']}/antecipacoes", json=corpo
    )

    assert resposta.status_code == 422
    assert parcelas(casal, novo["id"]) == antes


def test_antecipar_parcelamento_que_nao_existe_e_404(casal: Casal):
    resposta = casal.pedir(
        "flavio", "POST", f"/api/parcelamentos/{uuid4()}/antecipacoes", json={"parcelas": 1}
    )
    assert resposta.status_code == 404


def test_quitar_no_cartao_junta_o_restante_na_fatura_do_pagamento_e_a_tarefa_diaria_nao_mexe(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    nubank, eletro = cartao(casal), casal.categoria("Eletrodomésticos")
    novo = parcelamento(
        nubank, [eletro], data="2026-10-26", parcelas=4, valor_total_centavos=400000
    )
    casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)

    resposta = casal.pedir("flavio", "POST", f"/api/parcelamentos/{novo['id']}/quitacao", json={})

    assert resposta.status_code == 200
    assert [(l["parcela"], l["valor_centavos"]) for l in resposta.json()] == [
        (2, 100000),
        (3, 100000),
        (4, 100000),
    ]
    faturas = casal.pedir("flavio", "GET", f"/api/cartoes/{nubank}/faturas").json()
    assert [(f["mes"], f["compras_centavos"]) for f in faturas if f["compras_centavos"]] == [
        ("2026-11-01", 400000)
    ]
    # Meses depois a tarefa diária não tem o que realizar nem desfaz o pagamento.
    no_dia(monkeypatch, "2027-03-01")
    fazer_tarefa_diaria(database_url)
    assert [(l["situacao"], l["valor_centavos"]) for l in parcelas(casal, novo["id"])] == [
        ("realizado", 100000)
    ] * 4


def mudar(casal: Casal, id: str, quem: str = "flavio", **campos):
    return casal.pedir(quem, "PATCH", f"/api/parcelamentos/{id}", json=campos)


def criar_geladeira(casal: Casal, conta: str, lancada_em: str | None = None, **campos) -> dict:
    """Com `lancada_em`, o casal lançou a geladeira naquele dia: as parcelas de antes de hoje
    existem, e as automáticas que chegaram desde então estão realizadas, como a tarefa diária
    as deixaria."""
    novo = parcelamento(
        conta, [casal.categoria("Eletrodomésticos")], descricao="Geladeria", **campos
    )
    with pytest.MonkeyPatch.context() as naquele_dia:
        if lancada_em:
            no_dia(naquele_dia, lancada_em)
        assert casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo).status_code == 201
    if lancada_em:
        fazer_tarefa_diaria(casal.client.app.state.url)
    return novo


def test_corrigir_descricao_tags_e_pessoa_vale_para_todas_as_parcelas_inclusive_as_realizadas(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    conta, casa = casal.conta(), casal.categoria("Casa")
    novo = criar_geladeira(
        casal, conta, lancada_em="2026-10-10", data="2026-10-10", automatico=True, tags=["velha"]
    )
    # Hoje é 28/10: a 1ª parcela (10/10) já é realizada, as outras são previstas.
    assert [l["situacao"] for l in parcelas(casal, novo["id"])] == [
        "realizado",
        "previsto",
        "previsto",
    ]

    resposta = mudar(
        casal,
        novo["id"],
        descricao="Geladeira",
        tags=["casa nova", "Eletro"],
        pessoa="esposa",
        categoria_ids=[casa],
    )

    assert resposta.status_code == 200
    assert resposta.json()["descricao"] == "Geladeira"
    # A ordem das tags é a do collation do banco: compara como conjunto.
    assert (set(resposta.json()["tags"]), resposta.json()["pessoa"]) == (
        {"Eletro", "casa nova"},
        "esposa",
    )
    assert resposta.json()["alterado_por"] == "flavio"
    for l in parcelas(casal, novo["id"]):
        assert (l["descricao"], set(l["tags"]), l["pessoa"], l["categoria_ids"]) == (
            "Geladeira",
            {"Eletro", "casa nova"},
            "esposa",
            [casa],
        )
        assert l["versao"] == 2
    # Quem estava editando a parcela sem internet, sobre a versão de antes, vê que foi a regra.
    [primeira, *_] = parcelas(casal, novo["id"])
    conflito = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/lancamentos/{primeira['id']}",
        json={"versao": 1, "descricao": "Outra"},
    )
    assert conflito.status_code == 409
    assert [(c["campo"], c["origem"]) for c in conflito.json()["campos"]] == [
        ("descricao", "o parcelamento Geladeira")
    ]


def test_corrigir_o_parcelamento_que_nao_existe_ou_com_item_fora_das_categorias_e_recusado(
    casal: Casal,
):
    conta = casal.conta()
    novo = criar_geladeira(casal, conta)

    assert mudar(casal, str(uuid4()), descricao="x").status_code == 404
    fora = mudar(casal, novo["id"], item_categoria_id=str(uuid4()))
    assert fora.status_code == 422
    assert [l["versao"] for l in parcelas(casal, novo["id"])] == [1, 1, 1]


def valores(casal: Casal, id: str) -> list[tuple]:
    return [
        (l["parcela"], l["valor_centavos"], l["data"], l["situacao"]) for l in parcelas(casal, id)
    ]


def test_corrigir_o_valor_refaz_as_parcelas_e_so_avisa_quando_uma_realizada_muda(casal: Casal):
    # 10/10 já passou: a 1ª parcela, automática, é realizada; as outras, previstas.
    novo = criar_geladeira(
        casal,
        casal.conta(),
        lancada_em="2026-10-10",
        data="2026-10-10",
        automatico=True,
        valor_total_centavos=100000,
    )
    assert valores(casal, novo["id"]) == [
        (1, 33334, "2026-10-10", "realizado"),
        (2, 33333, "2026-11-10", "previsto"),
        (3, 33333, "2026-12-10", "previsto"),
    ]

    aviso = mudar(casal, novo["id"], valor_total_centavos=90000)

    assert aviso.status_code == 409
    [afetada] = aviso.json()["parcelas"]
    assert afetada | {"id": None} == {
        "id": None,
        "parcela": 1,
        "valor_centavos": 33334,
        "valor_novo_centavos": 30000,
        "data": "2026-10-10",
        "data_nova": "2026-10-10",
        "sai": False,
    }
    # O aviso não gravou nada: nem o parcelamento, nem as parcelas.
    assert (
        casal.pedir("flavio", "GET", "/api/parcelamentos").json()[0]["valor_total_centavos"]
        == 100000
    )
    assert [l["versao"] for l in parcelas(casal, novo["id"])] == [1, 1, 1]

    feito = mudar(casal, novo["id"], valor_total_centavos=90000, confirmar_realizadas=True)

    assert feito.status_code == 200
    assert feito.json()["valor_total_centavos"] == 90000
    assert valores(casal, novo["id"]) == [
        (1, 30000, "2026-10-10", "realizado"),
        (2, 30000, "2026-11-10", "previsto"),
        (3, 30000, "2026-12-10", "previsto"),
    ]
    # Quem corrige sem internet a parcela sobre a versão de antes vê que foi o parcelamento.
    [primeira, *_] = parcelas(casal, novo["id"])
    conflito = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/lancamentos/{primeira['id']}",
        json={"versao": 1, "valor_centavos": 1},
    )
    assert [(c["campo"], c["origem"]) for c in conflito.json()["campos"]] == [
        ("valor_centavos", "o parcelamento Geladeria")
    ]


def test_corrigir_o_que_so_tem_previstas_nao_pede_confirmacao_e_o_valor_da_parcela_vale_n_vezes(
    casal: Casal,
):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", parcelas=4)

    resposta = mudar(casal, novo["id"], valor_da_parcela_centavos=35000, data="2026-11-30")

    assert resposta.status_code == 200
    assert resposta.json()["valor_total_centavos"] == 140000
    assert valores(casal, novo["id"]) == [
        (1, 35000, "2026-11-30", "previsto"),
        (2, 35000, "2026-12-30", "previsto"),
        (3, 35000, "2027-01-30", "previsto"),
        (4, 35000, "2027-02-28", "previsto"),
    ]
    assert {l["mes"] for l in parcelas(casal, novo["id"])} == {
        "2026-11-01",
        "2026-12-01",
        "2027-01-01",
        "2027-02-01",
    }
    # Repetir o mesmo pedido não muda mais nada.
    assert (
        mudar(casal, novo["id"], valor_da_parcela_centavos=35000, data="2026-11-30").status_code
        == 200
    )
    assert {l["versao"] for l in parcelas(casal, novo["id"])} == {2}


def test_corrigir_o_numero_de_parcelas_mantem_o_total_gera_as_que_faltam_e_tira_as_que_sobram(
    casal: Casal,
):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", valor_total_centavos=100000)

    mais = mudar(casal, novo["id"], parcelas=5, valor_total_centavos=100001)
    assert mais.status_code == 200
    assert valores(casal, novo["id"]) == [
        (1, 20001, "2026-11-10", "previsto"),
        (2, 20000, "2026-12-10", "previsto"),
        (3, 20000, "2027-01-10", "previsto"),
        (4, 20000, "2027-02-10", "previsto"),
        (5, 20000, "2027-03-10", "previsto"),
    ]
    assert {l["parcelas"] for l in parcelas(casal, novo["id"])} == {5}

    # Só o número: o total fica e as parcelas se dividem de novo.
    menos = mudar(casal, novo["id"], parcelas=2)
    assert menos.status_code == 200
    assert valores(casal, novo["id"]) == [
        (1, 50001, "2026-11-10", "previsto"),
        (2, 50000, "2026-12-10", "previsto"),
    ]
    assert [l["parcelas"] for l in parcelas(casal, novo["id"])] == [2, 2]
    # As parcelas que saíram não aparecem em lugar nenhum.
    assert len(casal.pedir("flavio", "GET", "/api/lancamentos").json()) == 2

    # Voltando a 4, as que tinham saído voltam como parcelas do parcelamento.
    de_volta = mudar(casal, novo["id"], parcelas=4)
    assert de_volta.status_code == 200
    assert valores(casal, novo["id"]) == [
        (1, 25001, "2026-11-10", "previsto"),
        (2, 25000, "2026-12-10", "previsto"),
        (3, 25000, "2027-01-10", "previsto"),
        (4, 25000, "2027-02-10", "previsto"),
    ]
    assert len(casal.pedir("flavio", "GET", "/api/lancamentos").json()) == 4


def test_tirar_uma_parcela_realizada_pede_confirmacao_e_diz_que_ela_sai(casal: Casal):
    novo = criar_geladeira(
        casal,
        casal.conta(),
        lancada_em="2026-08-10",
        data="2026-08-10",
        automatico=True,
        valor_total_centavos=90000,
    )
    assert [l["situacao"] for l in parcelas(casal, novo["id"])] == ["realizado"] * 3

    aviso = mudar(casal, novo["id"], parcelas=2, valor_total_centavos=60000)

    assert aviso.status_code == 409
    [afetada] = aviso.json()["parcelas"]
    assert (afetada["parcela"], afetada["sai"], afetada["valor_novo_centavos"]) == (3, True, None)
    assert len(parcelas(casal, novo["id"])) == 3

    sai = mudar(
        casal, novo["id"], parcelas=2, valor_total_centavos=60000, confirmar_realizadas=True
    )

    assert sai.status_code == 200
    assert valores(casal, novo["id"]) == [
        (1, 30000, "2026-08-10", "realizado"),
        (2, 30000, "2026-09-10", "realizado"),
    ]
    # O saldo da conta já não conta a parcela que saiu.
    [conta] = casal.pedir("flavio", "GET", "/api/contas").json()
    assert conta["saldo_centavos"] == -60000


def test_parcela_editada_a_mao_fica_marcada_e_a_correcao_a_preserva(casal: Casal):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", parcelas=4)
    [_, segunda, *_] = parcelas(casal, novo["id"])
    assert segunda["alterada_a_mao"] is False
    editada = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{segunda['id']}",
        json={"versao": 1, "valor_centavos": 12345},
    )
    assert editada.json()["alterada_a_mao"] is True

    resposta = mudar(casal, novo["id"], valor_total_centavos=200000, descricao="Geladeira")

    assert resposta.status_code == 200
    assert valores(casal, novo["id"]) == [
        (1, 50000, "2026-11-10", "previsto"),
        (2, 12345, "2026-12-10", "previsto"),
        (3, 50000, "2027-01-10", "previsto"),
        (4, 50000, "2027-02-10", "previsto"),
    ]
    # A classificação vale para todas, inclusive a editada à mão; a marca continua nela.
    assert {l["descricao"] for l in parcelas(casal, novo["id"])} == {"Geladeira"}
    assert [l["alterada_a_mao"] for l in parcelas(casal, novo["id"])] == [False, True, False, False]


def test_nao_se_tira_a_parcela_editada_a_mao_nem_se_informa_valor_demais(casal: Casal):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", parcelas=4)
    [*_, quarta] = parcelas(casal, novo["id"])
    casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{quarta['id']}",
        json={"versao": 1, "valor_centavos": 1000},
    )

    recusada = mudar(casal, novo["id"], parcelas=3)

    assert recusada.status_code == 422
    assert "parcela 4" in recusada.json()["detail"]
    assert len(parcelas(casal, novo["id"])) == 4
    ambos = mudar(casal, novo["id"], valor_total_centavos=1000, valor_da_parcela_centavos=100)
    assert ambos.status_code == 422
    pouco = mudar(casal, novo["id"], valor_total_centavos=3)
    assert pouco.status_code == 422
    assert mudar(casal, novo["id"], parcelas=1).status_code == 422


def test_corrigir_a_data_da_compra_no_cartao_mantem_cada_parcela_n_faturas_depois(casal: Casal):
    nubank = cartao(casal)
    novo = criar_geladeira(casal, nubank, data="2026-11-10", valor_total_centavos=90000)
    assert [
        (l["parcela"], l["fatura_mes"], l["situacao"]) for l in parcelas(casal, novo["id"])
    ] == [
        (1, "2026-11-01", "previsto"),
        (2, "2026-12-01", "previsto"),
        (3, "2027-01-01", "previsto"),
    ]

    # A compra foi no dia 27, depois do fechamento do dia 25: tudo cai uma fatura depois.
    resposta = mudar(casal, novo["id"], data="2026-11-27")

    assert resposta.status_code == 200
    assert [
        (l["parcela"], l["data"], l["fatura_mes"], l["mes"]) for l in parcelas(casal, novo["id"])
    ] == [
        (1, "2026-11-27", "2026-12-01", "2026-12-01"),
        (2, "2026-11-27", "2027-01-01", "2027-01-01"),
        (3, "2026-11-27", "2027-02-01", "2027-02-01"),
    ]
    faturas = casal.pedir("flavio", "GET", f"/api/cartoes/{nubank}/faturas").json()
    assert {"2027-02-01", "2026-12-01"} <= {f["mes"] for f in faturas}
    # Quem edita a parcela sem internet, sobre a versão de antes, vê a fatura como mudança do
    # parcelamento.
    [primeira, *_] = parcelas(casal, novo["id"])
    conflito = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/lancamentos/{primeira['id']}",
        json={"versao": 1, "fatura_mes": "2026-11-01"},
    )
    assert conflito.status_code == 409
    assert {(c["campo"], c["origem"]) for c in conflito.json()["campos"]} == {
        ("fatura_mes", "o parcelamento Geladeria")
    }


def test_corrigir_a_data_de_um_cartao_com_parcela_realizada_pede_confirmacao(casal: Casal):
    nubank = cartao(casal)
    # Compra em 26/10: a 1ª parcela (fatura de novembro) já é realizada.
    novo = criar_geladeira(casal, nubank, data="2026-10-26")
    assert parcelas(casal, novo["id"])[0]["situacao"] == "realizado"

    aviso = mudar(casal, novo["id"], data="2026-10-20")

    assert aviso.status_code == 409
    assert [(p["parcela"], p["data"], p["data_nova"]) for p in aviso.json()["parcelas"]] == [
        (1, "2026-10-26", "2026-10-20")
    ]
    assert mudar(casal, novo["id"], data="2026-10-20", confirmar_realizadas=True).status_code == 200
    assert {l["data"] for l in parcelas(casal, novo["id"])} == {"2026-10-20"}


def test_corrigir_a_data_para_o_passado_pula_as_parcelas_que_passaram_sem_realizar_e_elas_voltam(
    casal: Casal,
):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", automatico=True)
    assert [l["situacao"] for l in parcelas(casal, novo["id"])] == ["previsto"] * 3

    para_tras = mudar(casal, novo["id"], data="2026-09-10")

    # Setembro e outubro passaram: saem como puladas, nada vira realizado (ticket 87).
    assert para_tras.status_code == 200
    assert para_tras.json()["parcelas_puladas"] == 2
    assert valores(casal, novo["id"]) == [(3, 33333, "2026-11-10", "previsto")]
    [conta] = casal.pedir("flavio", "GET", "/api/contas").json()
    assert conta["saldo_centavos"] == 0

    para_frente = mudar(casal, novo["id"], data="2026-11-10")

    assert para_frente.json()["parcelas_puladas"] == 0
    assert valores(casal, novo["id"]) == [
        (1, 33334, "2026-11-10", "previsto"),
        (2, 33333, "2026-12-10", "previsto"),
        (3, 33333, "2027-01-10", "previsto"),
    ]


def test_corrigir_a_data_do_boleto_para_frente_cria_as_parcelas_puladas_menos_a_excluida(
    casal: Casal,
):
    # Lançado hoje (28/10) com a 1ª em 10/08: as parcelas 1 a 3 foram puladas.
    novo = criar_geladeira(casal, casal.conta(), data="2026-08-10", parcelas=6, automatico=True)
    quinta = parcelas(casal, novo["id"])[1]
    assert quinta["parcela"] == 5
    assert (
        casal.pedir("flavio", "DELETE", f"/api/lancamentos/{quinta['id']}?versao=1").status_code
        == 204
    )

    resposta = mudar(casal, novo["id"], data="2026-12-10")

    assert resposta.status_code == 200
    assert resposta.json()["parcelas_puladas"] == 0
    assert valores(casal, novo["id"]) == [
        (1, 16670, "2026-12-10", "previsto"),
        (2, 16666, "2027-01-10", "previsto"),
        (3, 16666, "2027-02-10", "previsto"),
        (4, 16666, "2027-03-10", "previsto"),
        (6, 16666, "2027-05-10", "previsto"),
    ]


def test_a_parcela_atrasada_que_a_correcao_move_continua_prevista(casal: Casal):
    novo = criar_geladeira(casal, casal.conta(), lancada_em="2026-09-01", data="2026-09-10")

    assert mudar(casal, novo["id"], data="2026-09-05").status_code == 200

    # Setembro e outubro já estavam atrasados: a data muda, e eles seguem esperando o casal.
    assert valores(casal, novo["id"]) == [
        (1, 33334, "2026-09-05", "previsto"),
        (2, 33333, "2026-10-05", "previsto"),
        (3, 33333, "2026-11-05", "previsto"),
    ]


def test_a_parcela_excluida_uma_a_uma_nao_volta_com_a_correcao(casal: Casal):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", parcelas=4)
    [_, segunda, *_] = parcelas(casal, novo["id"])
    assert (
        casal.pedir("flavio", "DELETE", f"/api/lancamentos/{segunda['id']}?versao=1").status_code
        == 204
    )

    assert mudar(casal, novo["id"], valor_total_centavos=40000).status_code == 200

    assert [(p, v) for p, v, *_ in valores(casal, novo["id"])] == [
        (1, 10000),
        (3, 10000),
        (4, 10000),
    ]


def test_corrigir_um_parcelamento_longo_refaz_as_parcelas_em_mais_de_uma_transacao(casal: Casal):
    conta = casal.conta()
    categorias = [casal.categoria(f"Categoria {n}") for n in range(5)]
    novo = parcelamento(
        conta,
        categorias,
        tags=[f"tag {n}" for n in range(5)],
        parcelas=300,
        valor_total_centavos=30000000,
        data="2026-11-05",
    )
    assert casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo).status_code == 201

    # 20 linhas por parcela: 150 por lote, então a correção toma três lotes de refazer.
    resposta = mudar(
        casal, novo["id"], valor_total_centavos=60000000, data="2026-12-05", descricao="Outra"
    )

    assert resposta.status_code == 200
    refeitas = parcelas(casal, novo["id"])
    assert [l["parcela"] for l in refeitas] == list(range(1, 301))
    assert {(l["valor_centavos"], l["descricao"]) for l in refeitas} == {(200000, "Outra")}
    assert (refeitas[0]["data"], refeitas[-1]["data"]) == ("2026-12-05", "2051-11-05")
    assert {l["versao"] for l in refeitas} == {2}


def test_excluir_o_parcelamento_exclui_todas_as_parcelas_e_nao_volta(
    casal: Casal, database_url: str
):
    conta = casal.conta()
    novo = criar_geladeira(
        casal, conta, lancada_em="2026-10-10", data="2026-10-10", automatico=True, parcelas=4
    )
    avulso = {
        "id": str(uuid4()),
        "tipo": "despesa",
        "valor_centavos": 1500,
        "data": "2026-10-28",
        "conta_id": conta,
        "categoria_ids": [casal.categoria("Mercado")],
    }
    casal.pedir("flavio", "POST", "/api/lancamentos", json=avulso)
    assert parcelas(casal, novo["id"])[0]["situacao"] == "realizado"

    resposta = casal.pedir("flavio", "DELETE", f"/api/parcelamentos/{novo['id']}")
    de_novo = casal.pedir("esposa", "DELETE", f"/api/parcelamentos/{novo['id']}")

    assert (resposta.status_code, de_novo.status_code) == (204, 204)
    assert casal.pedir("flavio", "GET", "/api/parcelamentos").json() == []
    assert [l["id"] for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()] == [
        avulso["id"]
    ]
    [saldo] = [c["saldo_centavos"] for c in casal.pedir("flavio", "GET", "/api/contas").json()]
    assert saldo == -1500
    # A tarefa diária não gera nem realiza nada dele.
    assert fazer_tarefa_diaria(database_url)["parcelamentos"] == 0
    assert len(casal.pedir("flavio", "GET", "/api/lancamentos").json()) == 1
    # O parcelamento não existe mais.
    assert mudar(casal, novo["id"], descricao="x").status_code == 404


def test_excluir_um_parcelamento_longo_exclui_em_mais_de_uma_transacao(casal: Casal):
    conta = casal.conta()
    categorias = [casal.categoria(f"Categoria {n}") for n in range(5)]
    novo = parcelamento(
        conta, categorias, tags=[f"tag {n}" for n in range(5)], parcelas=300, data="2026-11-05"
    )
    casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)

    assert casal.pedir("flavio", "DELETE", f"/api/parcelamentos/{novo['id']}").status_code == 204

    assert parcelas(casal, novo["id"]) == []


def test_a_correcao_so_refaz_a_classificacao_que_o_pedido_trouxe(casal: Casal):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", parcelas=3)
    [_, segunda, _] = parcelas(casal, novo["id"])
    casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{segunda['id']}",
        json={"versao": 1, "descricao": "Geladeira, entrada", "tags": ["extra"]},
    )

    # Corrigir só o valor não desfaz o que uma pessoa mudou numa parcela só.
    assert mudar(casal, novo["id"], valor_total_centavos=60000).status_code == 200
    assert [(l["descricao"], l["tags"]) for l in parcelas(casal, novo["id"])] == [
        ("Geladeria", []),
        ("Geladeira, entrada", ["extra"]),
        ("Geladeria", []),
    ]

    # Corrigir a descrição vale para todas (história 101).
    assert mudar(casal, novo["id"], descricao="Geladeira").status_code == 200
    assert [(l["descricao"], l["tags"]) for l in parcelas(casal, novo["id"])] == [
        ("Geladeira", []),
        ("Geladeira", ["extra"]),
        ("Geladeira", []),
    ]


def test_gerar_as_parcelas_de_um_parcelamento_excluido_no_meio_nao_falha(
    casal: Casal, database_url: str
):
    from app import parcelamentos

    parcelamentos.gerar_as_parcelas(database_url, uuid4())


def test_a_parcela_antecipada_conta_como_editada_a_mao_e_a_correcao_a_preserva(casal: Casal):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", parcelas=4)
    antecipada = casal.pedir(
        "flavio",
        "POST",
        f"/api/parcelamentos/{novo['id']}/antecipacoes",
        json={"parcelas": 1, "valor_total_centavos": 20000},
    )
    assert antecipada.status_code == 200
    assert antecipada.json()[0]["alterada_a_mao"] is True

    assert mudar(casal, novo["id"], valor_total_centavos=200000).status_code == 200
    assert [(p, v, s) for p, v, _, s in valores(casal, novo["id"])] == [
        (1, 50000, "previsto"),
        (2, 50000, "previsto"),
        (3, 50000, "previsto"),
        (4, 20000, "realizado"),
    ]
    assert mudar(casal, novo["id"], parcelas=3).status_code == 422


def interromper_o_refazer(monkeypatch: pytest.MonkeyPatch) -> None:
    """A correção grava o parcelamento e cai antes de refazer as parcelas (timeout, queda)."""
    from app import parcelamentos

    def cai(*_):
        raise RuntimeError("a Lambda caiu")

    monkeypatch.setattr(parcelamentos, "_reajustar_um_lote", cai)


def test_a_tarefa_diaria_refaz_as_parcelas_de_uma_correcao_que_parou_no_meio(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", valor_total_centavos=90000)
    with monkeypatch.context() as queda:
        interromper_o_refazer(queda)
        with pytest.raises(RuntimeError):
            mudar(casal, novo["id"], valor_total_centavos=60000, data="2026-12-10")
    assert [v[1] for v in valores(casal, novo["id"])] == [30000, 30000, 30000]

    feito = fazer_tarefa_diaria(database_url)

    assert feito["parcelamentos"] == 1
    assert valores(casal, novo["id"]) == [
        (1, 20000, "2026-12-10", "previsto"),
        (2, 20000, "2027-01-10", "previsto"),
        (3, 20000, "2027-02-10", "previsto"),
    ]
    assert fazer_tarefa_diaria(database_url)["parcelamentos"] == 0


def test_a_tarefa_diaria_refaz_a_classificacao_de_uma_correcao_que_parou_no_meio(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10")
    segunda = parcelas(casal, novo["id"])[1]
    assert (
        casal.pedir(
            "flavio",
            "PATCH",
            f"/api/lancamentos/{segunda['id']}",
            json={"versao": 1, "tags": ["extra"]},
        ).status_code
        == 200
    )
    with monkeypatch.context() as queda:
        interromper_o_refazer(queda)
        with pytest.raises(RuntimeError):
            mudar(casal, novo["id"], descricao="Geladeira")
    assert [l["descricao"] for l in parcelas(casal, novo["id"])] == ["Geladeria"] * 3

    assert fazer_tarefa_diaria(database_url)["parcelamentos"] == 1

    # Todas ganham a descrição que o pedido trouxe; a tag que uma pessoa pôs numa só fica.
    assert [(l["descricao"], l["tags"]) for l in parcelas(casal, novo["id"])] == [
        ("Geladeira", []),
        ("Geladeira", ["extra"]),
        ("Geladeira", []),
    ]
    assert fazer_tarefa_diaria(database_url)["parcelamentos"] == 0


def test_depois_de_concluida_a_correcao_a_tarefa_diaria_nao_desfaz_a_descricao_de_uma_parcela(
    casal: Casal, database_url: str
):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10")
    assert mudar(casal, novo["id"], descricao="Geladeira").status_code == 200
    segunda = parcelas(casal, novo["id"])[1]
    assert (
        casal.pedir(
            "flavio",
            "PATCH",
            f"/api/lancamentos/{segunda['id']}",
            json={"versao": segunda["versao"], "descricao": "Geladeira, entrada"},
        ).status_code
        == 200
    )

    fazer_tarefa_diaria(database_url)

    assert [l["descricao"] for l in parcelas(casal, novo["id"])] == [
        "Geladeira",
        "Geladeira, entrada",
        "Geladeira",
    ]


def test_o_valor_corrigido_depois_de_uma_correcao_de_classificacao_interrompida_nao_perde_a_classificacao(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10")
    with monkeypatch.context() as queda:
        interromper_o_refazer(queda)
        with pytest.raises(RuntimeError):
            mudar(casal, novo["id"], descricao="Geladeira")

    # Um PATCH só de valor termina o que ficou pendente.
    assert mudar(casal, novo["id"], valor_total_centavos=60000).status_code == 200

    assert [l["descricao"] for l in parcelas(casal, novo["id"])] == ["Geladeira"] * 3


def test_gerar_as_parcelas_entre_o_crescer_e_o_refazer_revive_as_que_a_correcao_tirou(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    from app import parcelamentos

    novo = criar_geladeira(casal, casal.conta(), data="2026-11-10", parcelas=4)
    assert mudar(casal, novo["id"], parcelas=2).status_code == 200
    with monkeypatch.context() as queda:
        interromper_o_refazer(queda)
        with pytest.raises(RuntimeError):
            mudar(casal, novo["id"], parcelas=4)

    # A tarefa diária gera antes de o pedido refazer: as parcelas 3 e 4 não ficam excluídas.
    parcelamentos.gerar_as_parcelas(database_url, UUID(novo["id"]))

    assert valores(casal, novo["id"])[2:] == [
        (3, 25000, "2027-01-10", "previsto"),
        (4, 25000, "2027-02-10", "previsto"),
    ]


def test_excluir_o_parcelamento_no_meio_do_refazer_da_correcao_nao_deixa_parcela_nem_da_erro(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    from app import parcelamentos

    conta = casal.conta()
    novo = parcelamento(
        conta,
        [casal.categoria(f"Categoria {n}") for n in range(5)],
        tags=[f"tag {n}" for n in range(5)],
        parcelas=300,
        valor_total_centavos=30000000,
        data="2026-11-05",
        automatico=True,
    )
    assert casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo).status_code == 201
    em_transacao = parcelamentos.em_transacao
    transacoes = []

    def apaga_depois_do_primeiro_lote(url, fazer):
        feito = em_transacao(url, fazer)
        transacoes.append(feito)
        if len(transacoes) == 2:  # a correção e o primeiro lote do refazer
            # Outra sessão exclui o parcelamento entre dois lotes.
            casal.pedir("esposa", "DELETE", f"/api/parcelamentos/{novo['id']}")
        return feito

    monkeypatch.setattr(parcelamentos, "em_transacao", apaga_depois_do_primeiro_lote)

    resposta = mudar(casal, novo["id"], valor_total_centavos=60000000)

    assert resposta.status_code == 404
    assert casal.pedir("flavio", "GET", "/api/lancamentos").json() == []
    assert casal.pedir("flavio", "GET", "/api/parcelamentos").json() == []


def test_o_aviso_de_realizadas_olha_o_que_falta_refazer_e_a_tarefa_diaria_termina_o_que_foi_confirmado(
    casal: Casal, database_url: str, monkeypatch: pytest.MonkeyPatch
):
    # 10/10 já passou: a 1ª parcela, automática, é realizada; as outras, previstas.
    novo = criar_geladeira(
        casal,
        casal.conta(),
        lancada_em="2026-10-10",
        data="2026-10-10",
        automatico=True,
        valor_total_centavos=90000,
    )
    with monkeypatch.context() as queda:
        interromper_o_refazer(queda)
        with pytest.raises(RuntimeError):
            mudar(casal, novo["id"], valor_total_centavos=60000, confirmar_realizadas=True)

    # A mudança já está gravada, mas a realizada ainda não mudou: repetir sem confirmar avisa só
    # dela, e as previstas que faltam não entram no aviso.
    repetido = mudar(casal, novo["id"], valor_total_centavos=60000)
    assert repetido.status_code == 409
    assert [
        (p["parcela"], p["valor_centavos"], p["valor_novo_centavos"])
        for p in repetido.json()["parcelas"]
    ] == [(1, 30000, 20000)]

    # A tarefa diária termina o que o dono já confirmou.
    fazer_tarefa_diaria(database_url)
    assert [v[1] for v in valores(casal, novo["id"])] == [20000, 20000, 20000]
    assert mudar(casal, novo["id"], valor_total_centavos=60000).status_code == 200


def test_a_tarefa_diaria_e_os_automaticos_com_o_parcelamento_excluido_nao_fazem_nada(
    casal: Casal, database_url: str
):
    from app import automaticos

    novo = criar_geladeira(
        casal, casal.conta(), lancada_em="2026-10-10", data="2026-10-10", automatico=True
    )
    assert casal.pedir("flavio", "DELETE", f"/api/parcelamentos/{novo['id']}").status_code == 204

    assert automaticos.realizar_automaticos(database_url, UUID(novo["id"])) == 0
    assert fazer_tarefa_diaria(database_url)["parcelamentos"] == 0
    assert casal.pedir("flavio", "GET", "/api/lancamentos").json() == []
