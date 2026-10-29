from datetime import date
from uuid import uuid4

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_lancamentos import lancamento


@pytest.fixture(autouse=True)
def hoje_e_15_de_outubro(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 10, 15))


def item(casal: Casal, categoria: str, valor: int, mes="2026-10") -> dict:
    resposta = casal.pedir(
        "flavio",
        "POST",
        f"/api/planejamento/{mes}/itens",
        json={"id": str(uuid4()), "categoria_id": categoria, "valor_centavos": valor},
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def ler(casal: Casal, mes="2026-10") -> dict:
    resposta = casal.pedir("esposa", "GET", f"/api/planejamento/{mes}")
    assert resposta.status_code == 200
    return resposta.json()


def test_item_planejado_aparece_no_mes_com_realizado_previsto_e_percentual(casal: Casal):
    conta, alimentacao = casal.conta(), casal.categoria("Alimentação")
    criado = item(casal, alimentacao, 100000)
    for valor, data in [(30000, "2026-10-02"), (20000, "2026-10-10"), (25000, "2026-10-25")]:
        casal.pedir(
            "flavio",
            "POST",
            "/api/lancamentos",
            json=lancamento(conta, [alimentacao], valor_centavos=valor, data=data),
        )

    assert ler(casal) == {
        "mes": "2026-10",
        "ainda_da_para_gastar_centavos": 25000,
        "ajustes_de_fatura_centavos": 0,
        "itens": [
            {
                "id": criado["id"],
                "categoria_id": alimentacao,
                "planejado_centavos": 100000,
                "realizado_centavos": 50000,
                "previsto_centavos": 25000,
                "percentual": 75,
                "ainda_da_para_gastar_centavos": 25000,
            }
        ],
    }


def lancar(casal: Casal, conta: str, categorias: list[str], valor: int, data: str, **campos):
    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(conta, categorias, valor_centavos=valor, data=data, **campos),
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_ainda_da_para_gastar_do_mes_soma_o_que_falta_sem_compensar_item_estourado(casal: Casal):
    conta = casal.conta()
    mercado, lazer = casal.categoria("Mercado"), casal.categoria("Lazer")
    item(casal, mercado, 100000)
    item(casal, lazer, 20000)
    lancar(casal, conta, [mercado], 30000, "2026-10-03")
    lancar(casal, conta, [lazer], 35000, "2026-10-04")

    plano = ler(casal)

    mercado_lido, lazer_lido = plano["itens"]
    assert mercado_lido["ainda_da_para_gastar_centavos"] == 70000
    assert lazer_lido["ainda_da_para_gastar_centavos"] == -15000
    assert lazer_lido["percentual"] == 175
    # 70.000 + 0: a sobra do mercado não paga o estouro do lazer, nem o estouro a abate.
    assert plano["ainda_da_para_gastar_centavos"] == 70000


def test_previsto_atrasado_conta_ate_ser_confirmado_ou_excluido(casal: Casal):
    conta, luz = casal.conta(), casal.categoria("Luz")
    item(casal, luz, 50000)
    atrasada = lancar(casal, conta, [luz], 18000, "2026-10-05")  # antes de hoje (15/10)
    assert casal.pedir("flavio", "GET", "/api/lancamentos").json()[0]["atrasado"] is False
    prevista = lancar(casal, conta, [luz], 18000, "2026-10-05", situacao="previsto")
    futura = lancar(casal, conta, [luz], 7000, "2026-10-28")

    antes = ler(casal)["itens"][0]
    assert (antes["realizado_centavos"], antes["previsto_centavos"]) == (18000, 25000)
    assert antes["ainda_da_para_gastar_centavos"] == 7000

    casal.pedir("flavio", "POST", f"/api/lancamentos/{prevista['id']}/confirmar", json={})
    casal.pedir("flavio", "DELETE", f"/api/lancamentos/{futura['id']}?versao=1")
    depois = ler(casal)["itens"][0]
    assert (depois["realizado_centavos"], depois["previsto_centavos"]) == (36000, 0)
    assert atrasada["id"] != prevista["id"]


def test_so_conta_no_item_o_lancamento_do_mes_ainda_nao_excluido_e_so_com_uma_categoria_com_item(
    casal: Casal,
):
    conta = casal.conta()
    mercado, viagem, extra = (casal.categoria(n) for n in ("Mercado", "Viagem", "Extra"))
    item(casal, mercado, 100000)
    lancar(casal, conta, [mercado, extra], 1000, "2026-10-01")  # só o mercado tem item
    lancar(casal, conta, [mercado], 2000, "2026-10-15")
    lancar(casal, conta, [mercado], 4000, "2026-09-30")  # outro mês
    lancar(casal, conta, [mercado], 8000, "2026-11-01")  # outro mês
    excluido = lancar(casal, conta, [mercado], 16000, "2026-10-10")
    casal.pedir("flavio", "DELETE", f"/api/lancamentos/{excluido['id']}?versao=1")
    item(casal, viagem, 50000)
    lancar(casal, conta, [mercado, viagem], 32000, "2026-10-12")  # dois itens: escolha é do 51

    [mercado_lido, viagem_lido] = ler(casal)["itens"]

    assert mercado_lido["realizado_centavos"] == 3000
    assert viagem_lido["realizado_centavos"] == 0


def test_transferencia_com_categoria_conta_no_item_para_planejar_o_que_guardar(casal: Casal):
    origem, reserva = casal.conta("Corrente"), casal.conta("Poupança", "poupanca")
    guardar = casal.categoria("Reserva", "transferencia")
    item(casal, guardar, 100000)
    for valor, data in [(60000, "2026-10-05"), (40000, "2026-10-20")]:
        resposta = casal.pedir(
            "flavio",
            "POST",
            "/api/transferencias",
            json={
                "id": str(uuid4()),
                "conta_origem_id": origem,
                "conta_destino_id": reserva,
                "valor_centavos": valor,
                "data": data,
                "categoria_id": guardar,
            },
        )
        assert resposta.status_code == 201

    [lido] = ler(casal)["itens"]

    assert (lido["realizado_centavos"], lido["previsto_centavos"], lido["percentual"]) == (
        60000,
        40000,
        100,
    )
    assert lido["ainda_da_para_gastar_centavos"] == 0


def test_mes_sem_itens_vem_vazio_e_mes_invalido_e_recusado(casal: Casal):
    assert ler(casal, "2027-01") == {
        "mes": "2027-01",
        "itens": [],
        "ainda_da_para_gastar_centavos": 0,
        "ajustes_de_fatura_centavos": 0,
    }
    assert casal.pedir("flavio", "GET", "/api/planejamento/2026-13").status_code == 422
    assert casal.pedir("flavio", "GET", "/api/planejamento/outubro").status_code == 422


def test_criar_item_recusa_categoria_inexistente_ou_repetida_no_mes_e_reenvio_devolve_o_gravado(
    casal: Casal,
):
    mercado = casal.categoria("Mercado")
    primeiro = item(casal, mercado, 100000)

    reenvio = casal.pedir(
        "flavio",
        "POST",
        "/api/planejamento/2026-10/itens",
        json={"id": primeiro["id"], "categoria_id": mercado, "valor_centavos": 100000},
    )
    repetida = casal.pedir(
        "flavio",
        "POST",
        "/api/planejamento/2026-10/itens",
        json={"id": str(uuid4()), "categoria_id": mercado, "valor_centavos": 5000},
    )
    inexistente = casal.pedir(
        "flavio",
        "POST",
        "/api/planejamento/2026-10/itens",
        json={"id": str(uuid4()), "categoria_id": str(uuid4()), "valor_centavos": 5000},
    )
    sem_valor = casal.pedir(
        "flavio",
        "POST",
        "/api/planejamento/2026-10/itens",
        json={"id": str(uuid4()), "categoria_id": mercado, "valor_centavos": 0},
    )
    outro_mes = item(casal, mercado, 90000, mes="2026-11")

    assert (reenvio.status_code, reenvio.json()) == (200, primeiro)
    assert repetida.status_code == 409
    assert inexistente.status_code == 422
    assert sem_valor.status_code == 422
    assert outro_mes["planejado_centavos"] == 90000
    assert len(ler(casal)["itens"]) == 1


def test_muda_o_valor_do_item_e_exclui_o_item_sem_mexer_nos_lancamentos(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    criado = item(casal, mercado, 100000)
    lancar(casal, conta, [mercado], 25000, "2026-10-03")

    mudado = casal.pedir(
        "esposa", "PATCH", f"/api/planejamento/itens/{criado['id']}", json={"valor_centavos": 50000}
    )
    inexistente = casal.pedir(
        "esposa", "PATCH", f"/api/planejamento/itens/{uuid4()}", json={"valor_centavos": 1}
    )
    excluir = casal.pedir("flavio", "DELETE", f"/api/planejamento/itens/{criado['id']}")
    de_novo = casal.pedir("flavio", "DELETE", f"/api/planejamento/itens/{criado['id']}")

    assert mudado.status_code == 200
    assert (mudado.json()["planejado_centavos"], mudado.json()["percentual"]) == (50000, 50)
    assert inexistente.status_code == 404
    assert (excluir.status_code, de_novo.status_code) == (204, 204)
    assert ler(casal)["itens"] == []
    assert len(casal.pedir("flavio", "GET", "/api/lancamentos").json()) == 1


def test_juntar_categorias_move_os_itens_e_soma_quando_os_dois_tem_item_no_mes(casal: Casal):
    conta = casal.conta()
    mercado, feira, padaria = (casal.categoria(n) for n in ("Mercado", "Feira", "Padaria"))
    item(casal, feira, 30000)
    item(casal, mercado, 70000)
    item(casal, feira, 20000, mes="2026-11")  # só a origem tem item em novembro
    item(casal, padaria, 5000)
    lancar(casal, conta, [feira], 10000, "2026-10-03")

    juncao = casal.pedir(
        "flavio", "POST", f"/api/categorias/{feira}/juntar", json={"destino_id": mercado}
    )

    assert juncao.status_code == 200
    [unico] = ler(casal)["itens"][:1]
    outubro = {i["categoria_id"]: i for i in ler(casal)["itens"]}
    assert outubro[mercado]["planejado_centavos"] == 100000
    assert outubro[mercado]["realizado_centavos"] == 10000
    assert feira not in outubro and padaria in outubro
    assert unico["categoria_id"] == mercado
    [novembro] = ler(casal, "2026-11")["itens"]
    assert (novembro["categoria_id"], novembro["planejado_centavos"]) == (mercado, 20000)


def test_excluir_categoria_com_item_do_planejamento_e_recusado(casal: Casal):
    mercado = casal.categoria("Mercado")
    criado = item(casal, mercado, 100000)

    recusada = casal.pedir("flavio", "DELETE", f"/api/categorias/{mercado}")
    casal.pedir("flavio", "DELETE", f"/api/planejamento/itens/{criado['id']}")
    aceita = casal.pedir("flavio", "DELETE", f"/api/categorias/{mercado}")

    assert recusada.status_code == 409
    assert "planejamento" in recusada.json()["detail"]
    assert aceita.status_code == 204


def test_juntar_categorias_de_transferencia_leva_as_transferencias_junto(casal: Casal):
    origem, reserva = casal.conta("Corrente"), casal.conta("Poupança", "poupanca")
    guardar, poupar = (
        casal.categoria("Guardar", "transferencia"),
        casal.categoria("Poupar", "transferencia"),
    )
    nova = {
        "id": str(uuid4()),
        "conta_origem_id": origem,
        "conta_destino_id": reserva,
        "valor_centavos": 40000,
        "data": "2026-10-05",
        "categoria_id": guardar,
    }
    casal.pedir("flavio", "POST", "/api/transferencias", json=nova)

    casal.pedir("flavio", "POST", f"/api/categorias/{guardar}/juntar", json={"destino_id": poupar})

    [movida] = casal.pedir("flavio", "GET", "/api/transferencias").json()
    assert movida["categoria_id"] == poupar


def test_excluir_categoria_de_transferencia_com_transferencia_e_recusado(casal: Casal):
    origem, reserva = casal.conta("Corrente"), casal.conta("Poupança", "poupanca")
    guardar = casal.categoria("Guardar", "transferencia")
    casal.pedir(
        "flavio",
        "POST",
        "/api/transferencias",
        json={
            "id": str(uuid4()),
            "conta_origem_id": origem,
            "conta_destino_id": reserva,
            "valor_centavos": 1000,
            "data": "2026-10-05",
            "categoria_id": guardar,
        },
    )

    assert casal.pedir("flavio", "DELETE", f"/api/categorias/{guardar}").status_code == 409


def test_compra_no_cartao_conta_no_item_do_mes_da_fatura(casal: Casal):
    # "Alimentação de abril" é o débito de abril mais o cartão de 26/03 a 25/04 (ADR 0003).
    conta, alimentacao = casal.conta(), casal.categoria("Alimentação")
    cartao = casal.pedir(
        "flavio",
        "POST",
        "/api/cartoes",
        json={"nome": "Nubank", "dia_fechamento": 25, "dia_vencimento": 5},
    ).json()["id"]
    item(casal, alimentacao, 100000, mes="2026-04")
    item(casal, alimentacao, 100000, mes="2026-03")
    lancar(casal, cartao, [alimentacao], 12000, "2026-03-28")
    lancar(casal, conta, [alimentacao], 3000, "2026-04-02")
    lancar(casal, cartao, [alimentacao], 5000, "2026-04-26")  # fatura de maio

    [abril] = ler(casal, "2026-04")["itens"]
    [marco] = ler(casal, "2026-03")["itens"]

    assert abril["realizado_centavos"] == 15000
    assert marco["realizado_centavos"] == 0


def test_copia_o_planejamento_do_mes_anterior_para_um_mes_vazio(casal: Casal):
    alimentacao, lazer = casal.categoria("Alimentação"), casal.categoria("Lazer")
    item(casal, alimentacao, 100000, mes="2026-09")
    item(casal, lazer, 30000, mes="2026-09")

    resposta = casal.pedir(
        "flavio", "POST", "/api/planejamento/2026-10/copiar", json={"de": "2026-09"}
    )

    assert resposta.status_code == 201, resposta.text
    copiado = ler(casal)
    assert {i["categoria_id"]: i["planejado_centavos"] for i in copiado["itens"]} == {
        alimentacao: 100000,
        lazer: 30000,
    }
    assert resposta.json() == copiado
    # O mês de origem não muda.
    assert len(ler(casal, "2026-09")["itens"]) == 2


def test_copiar_recusa_mes_de_destino_com_item_origem_vazia_e_origem_igual_ao_destino(
    casal: Casal,
):
    alimentacao = casal.categoria("Alimentação")
    item(casal, alimentacao, 100000, mes="2026-09")
    item(casal, alimentacao, 50000, mes="2026-10")

    def copiar(de):
        return casal.pedir(
            "flavio", "POST", "/api/planejamento/2026-10/copiar", json={"de": de}
        ).status_code

    assert copiar("2026-09") == 409  # destino já tem item
    assert copiar("2026-10") == 422  # copiar de si mesmo
    assert (
        casal.pedir(
            "flavio", "POST", "/api/planejamento/2026-11/copiar", json={"de": "2026-08"}
        ).status_code
        == 422
    )  # origem sem item
    assert ler(casal)["itens"][0]["planejado_centavos"] == 50000


def definir_modelo(casal: Casal, itens: list[tuple[str, int]]):
    return casal.pedir(
        "flavio",
        "PUT",
        "/api/planejamento/modelo",
        json={"itens": [{"categoria_id": c, "valor_centavos": v} for c, v in itens]},
    )


def test_modelo_padrao_comeca_vazio_e_e_editado_substituindo_o_conjunto(casal: Casal):
    alimentacao, lazer = casal.categoria("Alimentação"), casal.categoria("Lazer")
    assert casal.pedir("esposa", "GET", "/api/planejamento/modelo").json() == {"itens": []}

    resposta = definir_modelo(casal, [(alimentacao, 90000), (lazer, 20000)])
    assert resposta.status_code == 200, resposta.text
    assert {i["categoria_id"]: i["valor_centavos"] for i in resposta.json()["itens"]} == {
        alimentacao: 90000,
        lazer: 20000,
    }

    definir_modelo(casal, [(lazer, 25000)])
    lido = casal.pedir("esposa", "GET", "/api/planejamento/modelo").json()
    assert lido["itens"] == [{"categoria_id": lazer, "valor_centavos": 25000}]


def test_modelo_padrao_recusa_categoria_inexistente_repetida_e_valor_zero(casal: Casal):
    alimentacao = casal.categoria("Alimentação")
    assert definir_modelo(casal, [(str(uuid4()), 1000)]).status_code == 422
    assert definir_modelo(casal, [(alimentacao, 1000), (alimentacao, 2000)]).status_code == 422
    assert definir_modelo(casal, [(alimentacao, 0)]).status_code == 422


def test_aplica_o_modelo_padrao_a_um_mes_vazio_e_recusa_mes_com_item(casal: Casal):
    alimentacao, lazer = casal.categoria("Alimentação"), casal.categoria("Lazer")
    assert (
        casal.pedir("flavio", "POST", "/api/planejamento/2026-10/aplicar-modelo").status_code == 422
    )  # modelo vazio

    definir_modelo(casal, [(alimentacao, 90000), (lazer, 20000)])
    resposta = casal.pedir("flavio", "POST", "/api/planejamento/2026-10/aplicar-modelo")

    assert resposta.status_code == 201, resposta.text
    assert {i["categoria_id"]: i["planejado_centavos"] for i in ler(casal)["itens"]} == {
        alimentacao: 90000,
        lazer: 20000,
    }
    assert (
        casal.pedir("flavio", "POST", "/api/planejamento/2026-10/aplicar-modelo").status_code == 409
    )


def test_categoria_com_item_no_modelo_nao_se_exclui_e_juntar_leva_o_item_do_modelo(
    casal: Casal,
):
    origem, destino, outra = (casal.categoria(n) for n in ["Mercado", "Alimentação", "Lazer"])
    definir_modelo(casal, [(origem, 70000), (destino, 20000), (outra, 5000)])

    assert casal.pedir("flavio", "DELETE", f"/api/categorias/{outra}").status_code == 409

    assert (
        casal.pedir(
            "flavio", "POST", f"/api/categorias/{origem}/juntar", json={"destino_id": destino}
        ).status_code
        == 200
    )
    modelo = casal.pedir("flavio", "GET", "/api/planejamento/modelo").json()["itens"]
    assert {i["categoria_id"]: i["valor_centavos"] for i in modelo} == {
        destino: 90000,
        outra: 5000,
    }
