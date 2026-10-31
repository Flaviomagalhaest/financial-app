from datetime import date

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_cartoes import comprar, novo_cartao
from tests.test_lancamentos import lancamento
from tests.test_planejamento import item


@pytest.fixture(autouse=True)
def hoje_e_28_de_outubro(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 10, 28))


def ler(casal: Casal) -> dict:
    resposta = casal.pedir("esposa", "GET", "/api/hoje")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def lancar(casal: Casal, conta: str, categorias: list[str], **campos) -> dict:
    resposta = casal.pedir(
        "flavio", "POST", "/api/lancamentos", json=lancamento(conta, categorias, **campos)
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_hoje_pede_login(client):
    assert client.get("/api/hoje").status_code == 401


def test_hoje_vazio_no_primeiro_dia_do_app(casal: Casal):
    assert ler(casal) == {
        "dia": "2026-10-28",
        "mes": "2026-10",
        "planejado_centavos": 0,
        "ainda_da_para_gastar_centavos": 0,
        "ajustes_de_fatura_centavos": 0,
        "a_escolher": [],
        "lancamentos_a_escolher": [],
        "contas_da_semana": [],
        "transferencias_da_semana": [],
        "faturas_que_vencem": [],
        "itens_em_destaque": [],
    }


def test_ainda_da_para_gastar_vem_do_planejamento_do_mes_de_hoje(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    item(casal, mercado, 100000, mes="2026-10")
    item(casal, mercado, 500000, mes="2026-11")
    lancar(casal, conta, [mercado], valor_centavos=30000, data="2026-10-02")

    hoje = ler(casal)

    assert (hoje["planejado_centavos"], hoje["ainda_da_para_gastar_centavos"]) == (100000, 70000)


def test_itens_a_partir_de_80_por_cento_aparecem_do_mais_cheio_ao_menos(casal: Casal):
    conta = casal.conta()
    mercado, lazer, luz = (casal.categoria(n) for n in ["Mercado", "Lazer", "Luz"])
    for categoria, planejado, gasto in [
        (mercado, 100000, 79400),  # 79%: fora
        (lazer, 100000, 80000),  # 80%: entra
        (luz, 10000, 12000),  # 120%: estourado, vai primeiro
    ]:
        item(casal, categoria, planejado)
        lancar(casal, conta, [categoria], valor_centavos=gasto, data="2026-10-02")

    destaque = ler(casal)["itens_em_destaque"]

    assert [(i["categoria_id"], i["percentual"]) for i in destaque] == [(luz, 120), (lazer, 80)]


def test_a_escolher_traz_o_lancamento_para_a_tela_nomear(casal: Casal):
    conta = casal.conta()
    restaurante, viagem = casal.categoria("Restaurante"), casal.categoria("Viagem")
    item(casal, restaurante, 100000)
    item(casal, viagem, 300000)
    escolhido = lancar(casal, conta, [restaurante, viagem], descricao="Jantar", data="2026-10-03")
    lancar(casal, conta, [restaurante, viagem], valor_centavos=4000, data="2026-10-04")
    lancar(casal, conta, [restaurante, viagem], item_categoria_id=viagem, data="2026-10-05")

    hoje = ler(casal)
    casal.pedir(
        "esposa",
        "PATCH",
        f"/api/lancamentos/{escolhido['id']}",
        json={"versao": escolhido["versao"], "item_categoria_id": viagem},
    )

    assert len(hoje["a_escolher"]) == 2
    assert {l["id"] for l in hoje["lancamentos_a_escolher"]} == {
        a["lancamento_id"] for a in hoje["a_escolher"]
    }
    assert [a["lancamento_id"] for a in ler(casal)["a_escolher"]] == [
        a["lancamento_id"] for a in hoje["a_escolher"] if a["lancamento_id"] != escolhido["id"]
    ]


def test_contas_da_semana_vem_na_mesma_leitura_com_os_atrasados_marcados(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    for descricao, dia in [("Luz", "2026-10-27"), ("Água", "2026-11-04"), ("IPVA", "2026-11-05")]:
        lancar(casal, conta, [luz], descricao=descricao, data=dia, situacao="previsto")

    semana = ler(casal)["contas_da_semana"]

    assert [(l["descricao"], l["atrasado"]) for l in semana] == [("Luz", True), ("Água", False)]


def test_fatura_fechada_que_vence_na_semana_ou_ja_venceu_aparece_ate_ser_paga(casal: Casal):
    # Os dois fecham em 25/10 (fatura de outubro) e hoje é 28/10.
    vence_na_semana = novo_cartao(casal, "Nubank", dia_vencimento=30)["id"]
    ja_venceu = novo_cartao(casal, "Itaú", dia_vencimento=27)["id"]
    vence_depois = novo_cartao(casal, "Inter", dia_vencimento=10)["id"]
    aberta = novo_cartao(casal, "Elo", dia_fechamento=29, dia_vencimento=30)["id"]
    for cartao in [vence_na_semana, ja_venceu, vence_depois, aberta]:
        comprar(casal, cartao, "2026-10-10", valor_centavos=5000)

    faturas = ler(casal)["faturas_que_vencem"]

    assert [(f["cartao_id"], f["vencimento"], f["a_pagar_centavos"]) for f in faturas] == [
        (ja_venceu, "2026-10-27", 5000),
        (vence_na_semana, "2026-10-30", 5000),
    ]


def prever_transferencia(casal: Casal, **campos) -> dict:
    from tests.test_contas import transferencia

    origem, destino = casal.conta("Corrente"), casal.conta("Poupança")
    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/transferencias",
        json=transferencia(origem, destino, situacao="previsto", **campos),
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_transferencia_prevista_entra_nas_contas_da_semana_com_o_atrasado_marcado(casal: Casal):
    atrasada = prever_transferencia(casal, data="2026-10-27")
    da_semana = prever_transferencia(casal, data="2026-11-04")
    prever_transferencia(casal, data="2026-11-05")  # fora da janela de 7 dias
    realizada = prever_transferencia(casal, data="2026-10-20")
    casal.pedir("flavio", "POST", f"/api/transferencias/{realizada['id']}/confirmar", json={})

    semana = ler(casal)["transferencias_da_semana"]

    assert [(t["id"], t["atrasado"]) for t in semana] == [
        (atrasada["id"], True),
        (da_semana["id"], False),
    ]


def test_transferencia_atrasada_so_se_prevista_e_com_data_antes_de_hoje(casal: Casal):
    prevista = prever_transferencia(casal, data="2026-10-28")
    passada = prever_transferencia(casal, data="2026-10-01")

    lista = {
        t["id"]: t["atrasado"] for t in casal.pedir("esposa", "GET", "/api/transferencias").json()
    }

    assert lista == {prevista["id"]: False, passada["id"]: True}


def confirmar(casal: Casal, id: str, **corpo):
    return casal.pedir("esposa", "POST", f"/api/transferencias/{id}/confirmar", json=corpo)


def test_confirmar_transferencia_prevista_ajusta_valor_e_data(casal: Casal):
    t = prever_transferencia(casal, data="2026-10-27")

    resposta = confirmar(casal, t["id"], valor_centavos=25000, data="2026-10-28")

    assert resposta.status_code == 200, resposta.text
    gravada = resposta.json()
    assert (gravada["situacao"], gravada["valor_centavos"], gravada["data"]) == (
        "realizado",
        25000,
        "2026-10-28",
    )
    assert gravada["atrasado"] is False
    assert gravada["alterado_por"] == "esposa"
    assert ler(casal)["transferencias_da_semana"] == []


def test_confirmar_sem_ajuste_mantem_o_previsto(casal: Casal):
    t = prever_transferencia(casal, data="2026-10-27")

    gravada = confirmar(casal, t["id"]).json()

    assert (gravada["situacao"], gravada["valor_centavos"], gravada["data"]) == (
        "realizado",
        t["valor_centavos"],
        "2026-10-27",
    )


def test_reenvio_igual_devolve_o_gravado_e_ajuste_diferente_da_409(casal: Casal):
    t = prever_transferencia(casal, data="2026-10-27")
    primeira = confirmar(casal, t["id"], valor_centavos=25000)

    igual = confirmar(casal, t["id"], valor_centavos=25000)
    sem_ajuste = confirmar(casal, t["id"])
    diferente = confirmar(casal, t["id"], valor_centavos=10000)

    assert igual.status_code == sem_ajuste.status_code == 200
    assert igual.json() == sem_ajuste.json() == primeira.json()
    assert diferente.status_code == 409
    assert "valor_centavos" in diferente.json()["detail"]
    assert casal.pedir("esposa", "GET", "/api/transferencias").json()[0]["valor_centavos"] == 25000


def test_confirmar_transferencia_que_nao_existe_da_404(casal: Casal):
    assert confirmar(casal, "00000000-0000-0000-0000-000000000000").status_code == 404
