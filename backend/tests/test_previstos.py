"""Previsto, realizado, confirmação e contas da semana (ADR 0004)."""

from datetime import date

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_lancamentos import lancamento

HOJE = date(2026, 10, 28)


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hoje é 28/10/2026 em São Paulo, para as datas dos exemplos não envelhecerem."""
    monkeypatch.setattr(lancamentos, "hoje", lambda: HOJE)


def test_previsto_com_data_passada_fica_atrasado_e_continua_previsto(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    datas = ["2026-10-27", "2026-10-28", "2026-10-29"]
    for dia in datas:
        previsto = lancamento(conta, [luz], data=dia, situacao="previsto")
        casal.pedir("flavio", "POST", "/api/lancamentos", json=previsto)
    casal.pedir(
        "flavio", "POST", "/api/lancamentos", json=lancamento(conta, [luz], data="2026-10-20")
    )

    vistos = casal.pedir("esposa", "GET", "/api/lancamentos").json()

    assert [(l["data"], l["situacao"], l["atrasado"]) for l in vistos] == [
        ("2026-10-29", "previsto", False),
        ("2026-10-28", "previsto", False),
        ("2026-10-27", "previsto", True),
        ("2026-10-20", "realizado", False),
    ]


def test_confirmar_sem_ajuste_realiza_o_previsto_como_estava(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    previsto = lancamento(conta, [luz], data="2026-10-27", situacao="previsto")
    casal.pedir("flavio", "POST", "/api/lancamentos", json=previsto)

    resposta = casal.pedir(
        "esposa", "POST", f"/api/lancamentos/{previsto['id']}/confirmar", json={}
    )

    assert resposta.status_code == 200
    [visto] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert visto == resposta.json()
    assert (visto["situacao"], visto["atrasado"]) == ("realizado", False)
    assert (visto["valor_centavos"], visto["data"], visto["conta_id"]) == (
        12035,
        "2026-10-27",
        conta,
    )
    assert (visto["criado_por"], visto["alterado_por"]) == ("flavio", "esposa")


def test_confirmar_ajusta_valor_data_e_conta(casal: Casal):
    corrente, poupanca = casal.conta(), casal.conta("Poupança", "poupanca")
    salario = casal.categoria("Salário", "receita")
    previsto = lancamento(
        corrente,
        [salario],
        tipo="receita",
        valor_centavos=500000,
        data="2026-11-05",
        situacao="previsto",
    )
    casal.pedir("flavio", "POST", "/api/lancamentos", json=previsto)

    resposta = casal.pedir(
        "flavio",
        "POST",
        f"/api/lancamentos/{previsto['id']}/confirmar",
        json={"valor_centavos": 512345, "data": "2026-10-28", "conta_id": poupanca},
    )

    assert resposta.status_code == 200
    [visto] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert (visto["situacao"], visto["valor_centavos"], visto["data"], visto["conta_id"]) == (
        "realizado",
        512345,
        "2026-10-28",
        poupanca,
    )
    assert (visto["tipo"], visto["descricao"], visto["categoria_ids"]) == (
        "receita",
        "Mercado",
        [salario],
    )


@pytest.mark.parametrize(
    "ajuste",
    [
        pytest.param({"valor_centavos": 0}, id="valor zero"),
        pytest.param(
            {"conta_id": "00000000-0000-4000-8000-000000000000"}, id="conta que não existe"
        ),
    ],
)
def test_confirmacao_invalida_e_recusada_e_o_previsto_fica(casal: Casal, ajuste: dict):
    conta, luz = casal.conta(), casal.categoria("Luz")
    previsto = lancamento(conta, [luz], data="2026-10-27", situacao="previsto")
    casal.pedir("flavio", "POST", "/api/lancamentos", json=previsto)

    resposta = casal.pedir(
        "flavio", "POST", f"/api/lancamentos/{previsto['id']}/confirmar", json=ajuste
    )

    assert resposta.status_code == 422
    [visto] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert (visto["situacao"], visto["valor_centavos"], visto["conta_id"]) == (
        "previsto",
        12035,
        conta,
    )


def test_confirmar_um_lancamento_que_nao_existe_e_404(casal: Casal):
    resposta = casal.pedir(
        "flavio", "POST", "/api/lancamentos/00000000-0000-4000-8000-000000000000/confirmar", json={}
    )

    assert resposta.status_code == 404


def test_confirmar_de_novo_igual_devolve_o_gravado(casal: Casal):
    """A fila reenvia, ou a outra pessoa confirmou em um toque: nada se perde."""
    conta, luz = casal.conta(), casal.categoria("Luz")
    previsto = lancamento(conta, [luz], data="2026-10-27", situacao="previsto")
    casal.pedir("flavio", "POST", "/api/lancamentos", json=previsto)
    caminho = f"/api/lancamentos/{previsto['id']}/confirmar"
    primeira = casal.pedir("flavio", "POST", caminho, json={"valor_centavos": 13000})

    reenvio = casal.pedir("flavio", "POST", caminho, json={"valor_centavos": 13000})
    um_toque = casal.pedir("esposa", "POST", caminho, json={})

    assert (reenvio.status_code, um_toque.status_code) == (200, 200)
    assert reenvio.json() == um_toque.json() == primeira.json()


def test_confirmar_de_novo_com_outro_ajuste_e_recusado_sem_perder_o_primeiro(casal: Casal):
    """Ajuste diferente sobre um já confirmado não some em silêncio (ADR 0011)."""
    conta, luz = casal.conta(), casal.categoria("Luz")
    previsto = lancamento(conta, [luz], data="2026-10-27", situacao="previsto")
    casal.pedir("flavio", "POST", "/api/lancamentos", json=previsto)
    caminho = f"/api/lancamentos/{previsto['id']}/confirmar"
    primeira = casal.pedir("flavio", "POST", caminho, json={"valor_centavos": 13000})

    segunda = casal.pedir("esposa", "POST", caminho, json={"valor_centavos": 99999})

    assert segunda.status_code == 409
    [visto] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert visto == primeira.json()


def test_contas_da_semana_traz_atrasados_e_previstos_dos_proximos_7_dias_em_ordem_de_data(
    casal: Casal,
):
    conta = casal.conta()
    luz, salario = casal.categoria("Luz"), casal.categoria("Salário", "receita")
    exemplos = [
        ("Salário", "receita", salario, "2026-11-04", "previsto"),  # hoje + 7: entra
        ("IPVA", "despesa", luz, "2026-11-05", "previsto"),  # hoje + 8: fica de fora
        ("Luz de setembro", "despesa", luz, "2026-09-10", "previsto"),  # atrasado há tempo
        ("Água", "despesa", luz, "2026-10-28", "previsto"),  # data de hoje
        ("Mercado", "despesa", luz, "2026-10-30", "realizado"),  # já realizado: fora
        ("Luz", "despesa", luz, "2026-10-27", "previsto"),  # atrasado
    ]
    for descricao, tipo, categoria, dia, situacao in exemplos:
        casal.pedir(
            "flavio",
            "POST",
            "/api/lancamentos",
            json=lancamento(
                conta, [categoria], descricao=descricao, tipo=tipo, data=dia, situacao=situacao
            ),
        )

    resposta = casal.pedir("esposa", "GET", "/api/hoje")

    assert resposta.status_code == 200
    assert [
        (l["descricao"], l["data"], l["atrasado"]) for l in resposta.json()["contas_da_semana"]
    ] == [
        ("Luz de setembro", "2026-09-10", True),
        ("Luz", "2026-10-27", True),
        ("Água", "2026-10-28", False),
        ("Salário", "2026-11-04", False),
    ]


def test_confirmado_sai_das_contas_da_semana(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    previsto = lancamento(conta, [luz], data="2026-10-27", situacao="previsto")
    casal.pedir("flavio", "POST", "/api/lancamentos", json=previsto)
    antes = casal.pedir("flavio", "GET", "/api/hoje").json()["contas_da_semana"]

    casal.pedir("flavio", "POST", f"/api/lancamentos/{previsto['id']}/confirmar", json={})

    assert [l["id"] for l in antes] == [previsto["id"]]
    assert casal.pedir("flavio", "GET", "/api/hoje").json()["contas_da_semana"] == []


def test_so_o_realizado_mexe_no_saldo_e_a_confirmacao_o_traz_para_dentro(casal: Casal):
    corrente, poupanca = casal.conta(), casal.conta("Poupança", "poupanca")
    luz, salario = casal.categoria("Luz"), casal.categoria("Salário", "receita")
    receita = lancamento(corrente, [salario], tipo="receita", valor_centavos=500000)
    despesa = lancamento(corrente, [luz], valor_centavos=10000)
    previsto = lancamento(corrente, [luz], valor_centavos=25000, data="2026-11-02")
    atrasado = lancamento(
        corrente, [luz], valor_centavos=7000, data="2026-10-01", situacao="previsto"
    )
    for corpo in (receita, despesa, previsto, atrasado):
        casal.pedir("flavio", "POST", "/api/lancamentos", json=corpo)

    def saldos() -> dict[str, int]:
        contas = casal.pedir("esposa", "GET", "/api/contas").json()
        return {c["id"]: c["saldo_centavos"] for c in contas}

    antes = saldos()
    casal.pedir(
        "esposa",
        "POST",
        f"/api/lancamentos/{previsto['id']}/confirmar",
        json={"valor_centavos": 26000, "conta_id": poupanca},
    )
    depois = saldos()

    assert antes == {corrente: 490000, poupanca: 0}
    assert depois == {corrente: 490000, poupanca: -26000}


def test_confirmar_nao_leva_o_previsto_para_uma_conta_arquivada(casal: Casal):
    conta, antiga, luz = casal.conta(), casal.conta("Antiga"), casal.categoria("Luz")
    casal.pedir(
        "flavio",
        "PUT",
        f"/api/contas/{antiga}",
        json={"nome": "Antiga", "tipo": "corrente", "arquivada": True},
    )
    previsto = lancamento(conta, [luz], data="2026-10-27", situacao="previsto")
    casal.pedir("flavio", "POST", "/api/lancamentos", json=previsto)

    resposta = casal.pedir(
        "flavio", "POST", f"/api/lancamentos/{previsto['id']}/confirmar", json={"conta_id": antiga}
    )

    assert resposta.status_code == 422
    [visto] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert (visto["situacao"], visto["conta_id"]) == ("previsto", conta)
