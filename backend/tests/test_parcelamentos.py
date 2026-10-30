"""Parcelamento: compra ou dívida em N parcelas, cada uma um lançamento (ADR 0004)."""

from datetime import date
from uuid import uuid4

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
    assert casal.pedir("esposa", "GET", "/api/contas-da-semana").json()["lancamentos"] == []
    faturas = casal.pedir("flavio", "GET", f"/api/cartoes/{nubank}/faturas").json()
    assert [f["mes"] for f in faturas] == ["2026-11-01", "2026-12-01", "2027-01-01", "2027-02-01"]


def test_no_cartao_o_parcelamento_nao_pode_pedir_confirmacao(casal: Casal):
    novo = parcelamento(cartao(casal), [casal.categoria()], automatico=False)

    resposta = casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo)

    assert resposta.status_code == 422
    assert "automático" in str(resposta.json())
    assert casal.pedir("flavio", "GET", "/api/lancamentos").json() == []


def test_boleto_pede_confirmacao_de_cada_parcela_e_o_automatico_nao(casal: Casal):
    conta, emprestimo = casal.conta(), casal.categoria("Empréstimo")
    acordo = parcelamento(conta, [emprestimo], descricao="Acordo", data="2026-10-27")
    consorcio = parcelamento(
        conta, [emprestimo], descricao="Consórcio", data="2026-10-20", automatico=True
    )
    casal.pedir("flavio", "POST", "/api/parcelamentos", json=acordo)
    casal.pedir("flavio", "POST", "/api/parcelamentos", json=consorcio)

    # A parcela de ontem do acordo fica atrasada; a do consórcio já nasce realizada.
    semana = casal.pedir("esposa", "GET", "/api/contas-da-semana").json()["lancamentos"]
    assert [(l["descricao"], l["parcela"], l["atrasado"]) for l in semana] == [("Acordo", 1, True)]
    assert [l["situacao"] for l in parcelas(casal, consorcio["id"])] == [
        "realizado",
        "previsto",
        "previsto",
    ]
    [saldo] = [c["saldo_centavos"] for c in casal.pedir("flavio", "GET", "/api/contas").json()]
    assert saldo == -33334


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
