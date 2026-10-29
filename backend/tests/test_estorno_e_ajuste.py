"""Cancelamento, estorno e ajuste de fatura (ticket 39, ADR 0008): o casal acerta uma fatura que
não bate sem inventar categoria."""

from tests.conftest import Casal
from tests.test_cartoes import comprar, novo_cartao


def fatura(casal: Casal, cartao: str, mes: str) -> dict:
    [achada] = [
        f
        for f in casal.pedir("flavio", "GET", f"/api/cartoes/{cartao}/faturas").json()
        if f["mes"] == mes
    ]
    return achada


def test_total_da_fatura_soma_as_compras(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-03-28", valor_centavos=12000)
    comprar(casal, cartao, "2026-04-02", valor_centavos=3050)

    abril = fatura(casal, cartao, "2026-04-01")

    assert abril["compras_centavos"] == 15050
    assert abril["ajuste_centavos"] == 0
    assert abril["total_centavos"] == 15050


def test_compra_cancelada_antes_do_fechamento_some_da_fatura_e_do_planejamento(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    mercado = casal.categoria("Mercado")
    mantida = comprar(casal, cartao, "2026-04-02", valor_centavos=5000, categoria_ids=[mercado])
    cancelada = comprar(
        casal, cartao, "2026-04-03", valor_centavos=12000, categoria_ids=[mercado], tags=["viagem"]
    )
    casal.pedir(
        "flavio",
        "POST",
        "/api/planejamento/2026-04/itens",
        json={
            "id": "00000000-0000-0000-0000-0000000000a1",
            "categoria_id": mercado,
            "valor_centavos": 40000,
        },
    )
    assert fatura(casal, cartao, "2026-04-01")["total_centavos"] == 17000

    excluida = casal.pedir("flavio", "DELETE", f"/api/lancamentos/{cancelada['id']}")

    assert excluida.status_code == 204
    assert fatura(casal, cartao, "2026-04-01")["total_centavos"] == 5000
    [item] = casal.pedir("flavio", "GET", "/api/planejamento/2026-04").json()["itens"]
    assert item["realizado_centavos"] == 5000
    assert [l["id"] for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()] == [
        mantida["id"]
    ]


def ajustar(casal: Casal, cartao: str, mes: str, centavos: int):
    return casal.pedir(
        "flavio",
        "PATCH",
        f"/api/cartoes/{cartao}/faturas/{mes}",
        json={"ajuste_centavos": centavos},
    )


def test_ajuste_entra_no_total_da_fatura_e_pode_ser_negativo_ou_desfeito(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    comprar(casal, cartao, "2026-04-02", valor_centavos=10000)

    para_mais = ajustar(casal, cartao, "2026-04-01", 2350)
    assert para_mais.status_code == 200, para_mais.text
    assert (para_mais.json()["ajuste_centavos"], para_mais.json()["total_centavos"]) == (
        2350,
        12350,
    )

    para_menos = ajustar(casal, cartao, "2026-04-01", -400)
    assert (para_menos.json()["compras_centavos"], para_menos.json()["total_centavos"]) == (
        10000,
        9600,
    )
    assert fatura(casal, cartao, "2026-04-01")["ajuste_centavos"] == -400

    desfeito = ajustar(casal, cartao, "2026-04-01", 0)
    assert desfeito.json()["total_centavos"] == 10000


def test_ajuste_em_fatura_que_ainda_nao_nasceu_cria_ela_sem_mexer_nas_datas(casal: Casal):
    cartao = novo_cartao(casal)["id"]

    ajustada = ajustar(casal, cartao, "2026-04-15", 500)

    assert ajustada.status_code == 200, ajustada.text
    assert ajustada.json() | {"situacao": None} == {
        "cartao_id": cartao,
        "mes": "2026-04-01",
        "fechamento": "2026-04-25",
        "vencimento": "2026-05-05",
        "situacao": None,
        "compras_centavos": 0,
        "ajuste_centavos": 500,
        "total_centavos": 500,
    }


def test_ajuste_do_adicional_vai_para_a_fatura_do_titular(casal: Casal):
    titular = novo_cartao(casal)["id"]
    adicional = novo_cartao(
        casal, "Adicional", titular_id=titular, dia_fechamento=None, dia_vencimento=None
    )["id"]

    ajustar(casal, adicional, "2026-04-01", 700)

    assert fatura(casal, titular, "2026-04-01")["ajuste_centavos"] == 700


def totais(casal: Casal, mes: str) -> dict:
    resposta = casal.pedir("flavio", "GET", f"/api/meses/{mes}/totais")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_ajuste_conta_nas_despesas_do_mes_e_no_ainda_da_para_gastar_mas_nao_em_categoria_tag_nem_item(
    casal: Casal,
):
    cartao = novo_cartao(casal)["id"]
    mercado = casal.categoria("Mercado")
    comprar(
        casal,
        cartao,
        "2026-03-28",
        valor_centavos=10000,
        categoria_ids=[mercado],
        tags=["viagem"],
    )
    casal.pedir(
        "flavio",
        "POST",
        "/api/planejamento/2026-04/itens",
        json={
            "id": "00000000-0000-0000-0000-0000000000a1",
            "categoria_id": mercado,
            "valor_centavos": 40000,
        },
    )

    ajustar(casal, cartao, "2026-04-01", 2350)

    abril = totais(casal, "2026-04")
    assert abril["despesas_centavos"] == 12350
    assert abril["ajustes_de_fatura_centavos"] == 2350
    assert abril["por_categoria"] == [{"categoria_id": mercado, "centavos": 10000}]
    assert abril["por_tag"] == [{"tag": "viagem", "centavos": 10000}]
    planejamento = casal.pedir("flavio", "GET", "/api/planejamento/2026-04").json()
    [item] = planejamento["itens"]
    assert item["realizado_centavos"] == 10000
    assert item["ainda_da_para_gastar_centavos"] == 30000
    assert planejamento["ajustes_de_fatura_centavos"] == 2350
    assert planejamento["ainda_da_para_gastar_centavos"] == 27650
    assert totais(casal, "2026-03")["despesas_centavos"] == 0


def estornar(casal: Casal, original: dict, data: str, **campos):
    from tests.test_lancamentos import lancamento

    return casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(
            original["conta_id"],
            original["categoria_ids"],
            data=data,
            valor_centavos=original["valor_centavos"],
            tags=original["tags"],
            estorno_de=original["id"],
        )
        | campos,
    )


def test_estorno_diminui_a_fatura_em_que_aparece_e_o_total_da_tag_naquele_mes(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    mercado = casal.categoria("Mercado")
    original = comprar(
        casal,
        cartao,
        "2026-03-28",
        valor_centavos=12000,
        categoria_ids=[mercado],
        tags=["viagem"],
    )
    comprar(casal, cartao, "2026-03-29", valor_centavos=3000, categoria_ids=[mercado])
    casal.pedir(
        "flavio",
        "POST",
        "/api/planejamento/2026-05/itens",
        json={
            "id": "00000000-0000-0000-0000-0000000000a1",
            "categoria_id": mercado,
            "valor_centavos": 40000,
        },
    )

    estorno = estornar(casal, original, "2026-04-26", valor_centavos=4500)

    assert estorno.status_code == 201, estorno.text
    assert estorno.json()["estorno_de"] == original["id"]
    assert estorno.json()["categoria_ids"] == [mercado]
    assert estorno.json()["tags"] == ["viagem"]
    assert estorno.json()["fatura_mes"] == "2026-05-01"
    # A fatura de abril, onde a compra está, não muda; a de maio recebe o crédito.
    assert fatura(casal, cartao, "2026-04-01")["total_centavos"] == 15000
    assert fatura(casal, cartao, "2026-05-01")["total_centavos"] == -4500
    abril, maio = totais(casal, "2026-04"), totais(casal, "2026-05")
    assert abril["por_tag"] == [{"tag": "viagem", "centavos": 12000}]
    assert maio["despesas_centavos"] == -4500
    assert maio["por_tag"] == [{"tag": "viagem", "centavos": -4500}]
    assert maio["por_categoria"] == [{"categoria_id": mercado, "centavos": -4500}]
    [item] = casal.pedir("flavio", "GET", "/api/planejamento/2026-05").json()["itens"]
    assert item["realizado_centavos"] == -4500


def compra_no_cartao(casal: Casal, **campos) -> dict:
    cartao = novo_cartao(casal)["id"]
    return comprar(
        casal,
        cartao,
        "2026-03-28",
        valor_centavos=12000,
        categoria_ids=[casal.categoria("Mercado")],
        tags=["viagem"],
        **campos,
    )


def test_estorno_recusa_o_que_nao_e_devolucao_de_uma_compra_no_cartao(casal: Casal):
    original = compra_no_cartao(casal)

    outra_categoria = estornar(
        casal, original, "2026-04-26", categoria_ids=[casal.categoria("Lazer")]
    )
    sem_tag = estornar(casal, original, "2026-04-26", tags=[])
    inexistente = estornar(
        casal, original, "2026-04-26", estorno_de="00000000-0000-0000-0000-0000000000ff"
    )
    na_conta = estornar(casal, original, "2026-04-26", conta_id=casal.conta())
    como_receita = estornar(casal, original, "2026-04-26", tipo="receita")

    assert outra_categoria.status_code == sem_tag.status_code == 422
    assert outra_categoria.json()["detail"] == "estorno leva as mesmas categorias e tags da compra"
    assert inexistente.json()["detail"] == "compra original não encontrada"
    assert na_conta.json()["detail"] == "estorno é um crédito no cartão"
    assert como_receita.status_code == 422


def test_estorno_nao_e_de_estorno_nem_de_compra_na_conta_nem_passa_do_valor(casal: Casal):
    original = compra_no_cartao(casal)
    estorno = estornar(casal, original, "2026-04-26", valor_centavos=8000).json()
    conta = casal.conta()
    da_conta = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json={
            "id": "00000000-0000-0000-0000-0000000000c1",
            "tipo": "despesa",
            "valor_centavos": 1000,
            "data": "2026-04-01",
            "conta_id": conta,
            "categoria_ids": original["categoria_ids"],
        },
    ).json()

    de_estorno = estornar(casal, estorno, "2026-04-27", valor_centavos=100)
    de_compra_na_conta = estornar(casal, da_conta | {"tags": []}, "2026-04-27", valor_centavos=100)
    passa_do_valor = estornar(casal, original, "2026-04-27", valor_centavos=4001)
    cabe = estornar(casal, original, "2026-04-27", valor_centavos=4000)

    assert de_estorno.json()["detail"] == "estorno de estorno"
    assert de_compra_na_conta.json()["detail"] == "só compra no cartão tem estorno"
    assert passa_do_valor.json()["detail"] == "estornos somam mais que a compra"
    assert cabe.status_code == 201


def test_estorno_reenviado_pela_fila_devolve_o_gravado_mesmo_se_a_compra_sumiu(casal: Casal):
    original = compra_no_cartao(casal)
    estorno = estornar(casal, original, "2026-04-26")
    assert estorno.status_code == 201
    casal.pedir("flavio", "DELETE", f"/api/lancamentos/{original['id']}")

    reenvio = casal.pedir("flavio", "POST", "/api/lancamentos", json=estorno.json())

    assert reenvio.status_code == 200
    assert reenvio.json()["id"] == estorno.json()["id"]


def test_estorno_nao_muda_de_categoria_nem_de_tag_mas_o_valor_respeita_a_compra(casal: Casal):
    original = compra_no_cartao(casal)
    estorno = estornar(casal, original, "2026-04-26", valor_centavos=5000).json()

    categoria = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{estorno['id']}",
        json={"versao": 1, "categoria_ids": [casal.categoria("Lazer")]},
    )
    tags = casal.pedir(
        "flavio", "PATCH", f"/api/lancamentos/{estorno['id']}", json={"versao": 1, "tags": []}
    )
    valor_demais = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{estorno['id']}",
        json={"versao": 1, "valor_centavos": 12001},
    )
    valor_certo = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{estorno['id']}",
        json={"versao": 1, "valor_centavos": 12000},
    )

    assert categoria.status_code == tags.status_code == valor_demais.status_code == 422
    assert valor_certo.status_code == 200
    assert valor_certo.json()["estorno_de"] == original["id"]
