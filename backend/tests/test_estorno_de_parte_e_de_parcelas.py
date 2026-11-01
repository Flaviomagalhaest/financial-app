"""Estorno de uma parte da compra e de todas as parcelas (ticket 138, ADR 0016 e 0022)."""

from uuid import uuid4

from tests.conftest import Casal
from tests.test_cartoes import comprar, novo_cartao
from tests.test_estorno_e_ajuste import fatura, totais
from tests.test_lancamentos import lancamento
from tests.test_parcelamentos import parcelamento, parcelas
from tests.test_partes_da_compra import compra_com_partes, editar, parte


def estorno_da_parte(casal: Casal, compra: dict, indice: int, valor: int, **campos):
    return casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(
            compra["conta_id"],
            [],
            data="2026-04-26",
            valor_centavos=valor,
            estorno_de=compra["id"],
            estorno_parte_id=compra["partes"][indice]["id"],
        )
        | campos,
    )


def compra_em_partes(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    roupa, casa = casal.categoria("Roupa"), casal.categoria("Casa")
    criada = compra_com_partes(
        casal,
        cartao,
        [
            parte([roupa], 6000, descricao="Vestido", tags=["presente"]),
            parte([casa], 4000, descricao="Cortina"),
        ],
        data="2026-03-28",
    )
    assert criada.status_code == 201, criada.text
    return cartao, roupa, casa, criada.json()


def test_estorno_de_uma_parte_leva_as_categorias_e_tags_dela_e_diminui_so_ela(casal: Casal):
    cartao, roupa, casa, compra = compra_em_partes(casal)

    estorno = estorno_da_parte(casal, compra, 0, 2500, categoria_ids=[casa], tags=["outra"])

    assert estorno.status_code == 201, estorno.text
    criado = estorno.json()
    assert criado["estorno_de"] == compra["id"]
    assert criado["estorno_parte_id"] == compra["partes"][0]["id"]
    assert (criado["categoria_ids"], criado["tags"]) == ([roupa], ["presente"])
    assert fatura(casal, cartao, "2026-04-01")["total_centavos"] == 10000
    assert fatura(casal, cartao, "2026-05-01")["total_centavos"] == -2500
    maio = totais(casal, "2026-05")
    assert maio["por_categoria"] == [{"categoria_id": roupa, "centavos": -2500}]
    assert maio["por_tag"] == [{"tag": "presente", "centavos": -2500}]


def test_estorno_de_parte_vai_ate_o_valor_dela_e_nao_ate_o_da_compra(casal: Casal):
    _, _, _, compra = compra_em_partes(casal)

    assert estorno_da_parte(casal, compra, 1, 3000).status_code == 201
    acima = estorno_da_parte(casal, compra, 1, 1001)
    resto = estorno_da_parte(casal, compra, 1, 1000)
    outra_parte = estorno_da_parte(casal, compra, 0, 6000)

    assert (acima.status_code, acima.json()["detail"]) == (
        422,
        "estornos somam mais que a parte",
    )
    assert (resto.status_code, outra_parte.status_code) == (201, 201)


def test_estorno_de_compra_com_partes_pede_a_parte_e_ela_tem_de_ser_da_compra(casal: Casal):
    cartao, roupa, _, compra = compra_em_partes(casal)
    sem_parte = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(cartao, [roupa], valor_centavos=100, estorno_de=compra["id"]),
    )
    de_outra = estorno_da_parte(casal, compra, 0, 100, estorno_parte_id=str(uuid4()))
    sem_partes = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(
            cartao,
            [roupa],
            valor_centavos=100,
            estorno_de=comprar(casal, cartao, "2026-03-28")["id"],
            estorno_parte_id=compra["partes"][0]["id"],
        ),
    )

    assert [(r.status_code, r.json()["detail"]) for r in (sem_parte, de_outra, sem_partes)] == [
        (422, "a compra tem partes: escolha a parte que foi estornada"),
        (422, "a parte não é desta compra"),
        (422, "a compra não tem partes"),
    ]


def test_estorno_de_parte_acompanha_a_parte_quando_ela_muda(casal: Casal):
    _, _, casa, compra = compra_em_partes(casal)
    estorno = estorno_da_parte(casal, compra, 0, 2500).json()
    novas = [
        {**compra["partes"][0], "categoria_ids": [casa], "tags": ["natal"]},
        compra["partes"][1],
    ]

    mudada = editar(casal, compra["id"], versao=compra["versao"], partes=novas)

    assert mudada.status_code == 200, mudada.text
    [lido] = [
        l
        for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()
        if l["id"] == estorno["id"]
    ]
    assert (lido["categoria_ids"], lido["tags"]) == ([casa], ["natal"])
    assert totais(casal, "2026-05")["por_categoria"] == [{"categoria_id": casa, "centavos": -2500}]


def test_parte_com_estorno_nao_some_nem_encolhe_abaixo_do_estornado_e_a_compra_nao_se_exclui(
    casal: Casal,
):
    _, roupa, _, compra = compra_em_partes(casal)
    estorno_da_parte(casal, compra, 0, 2500)
    vestido, cortina = compra["partes"]

    sem_a_parte = editar(
        casal,
        compra["id"],
        versao=compra["versao"],
        partes=[cortina, parte([roupa], 6000)],
    )
    juntada = editar(
        casal,
        compra["id"],
        versao=compra["versao"],
        partes=[cortina],
    )
    menor = editar(
        casal,
        compra["id"],
        versao=compra["versao"],
        partes=[{**vestido, "valor_centavos": 2000}, {**cortina, "valor_centavos": 8000}],
    )
    excluida = casal.pedir("flavio", "DELETE", f"/api/lancamentos/{compra['id']}")

    assert (sem_a_parte.status_code, sem_a_parte.json()["detail"]) == (
        422,
        "a parte tem estorno; exclua o estorno antes de tirá-la",
    )
    assert (juntada.status_code, juntada.json()["detail"]) == (
        422,
        "a compra tem estorno de parte; exclua o estorno antes de juntar as partes",
    )
    assert (menor.status_code, menor.json()["detail"]) == (
        422,
        "a parte tem estornos de 2500 centavos: o valor dela não pode ficar abaixo disso",
    )
    assert (excluida.status_code, excluida.json()["detail"]) == (
        422,
        "a compra tem estorno; exclua o estorno antes",
    )
    maior = editar(
        casal,
        compra["id"],
        versao=compra["versao"],
        partes=[{**vestido, "valor_centavos": 7000}, {**cortina, "valor_centavos": 3000}],
        valor_centavos=10000,
    )
    assert maior.status_code == 200, maior.text


def test_dividir_compra_que_ja_tem_estorno_deixa_o_estorno_com_o_que_ele_tinha(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    roupa, casa = casal.categoria("Roupa"), casal.categoria("Casa")
    compra = comprar(
        casal, cartao, "2026-03-28", valor_centavos=10000, categoria_ids=[roupa], tags=["loja"]
    )
    estorno = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(
            cartao,
            [roupa],
            data="2026-04-26",
            valor_centavos=3000,
            estorno_de=compra["id"],
        ),
    ).json()

    dividida = editar(
        casal,
        compra["id"],
        versao=compra["versao"],
        partes=[parte([roupa], 6000), parte([casa], 4000)],
    )

    assert dividida.status_code == 200, dividida.text
    [lido] = [
        l
        for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()
        if l["id"] == estorno["id"]
    ]
    assert (lido["categoria_ids"], lido["tags"], lido["estorno_parte_id"]) == (
        [roupa],
        ["loja"],
        None,
    )
    # O que já foi estornado da compra inteira conta contra o total dela.
    vestido, cortina = dividida.json()["partes"]
    for parte_estornada, valor in ((cortina, 4000), (vestido, 6000)):
        estorno_de_parte = casal.pedir(
            "flavio",
            "POST",
            "/api/lancamentos",
            json=lancamento(
                cartao,
                [],
                data="2026-04-26",
                valor_centavos=valor,
                estorno_de=compra["id"],
                estorno_parte_id=parte_estornada["id"],
            ),
        )
    assert (estorno_de_parte.status_code, estorno_de_parte.json()["detail"]) == (
        422,
        "estornos somam mais que a compra",
    )


def test_estorno_de_parte_com_item_do_planejamento_diminui_o_item_dela(casal: Casal):
    _, roupa, _, compra = compra_em_partes(casal)
    casal.pedir(
        "flavio",
        "POST",
        "/api/planejamento/2026-05/itens",
        json={"id": str(uuid4()), "categoria_id": roupa, "valor_centavos": 20000},
    )

    estorno_da_parte(casal, compra, 0, 2500)

    [item] = casal.pedir("flavio", "GET", "/api/planejamento/2026-05").json()["itens"]
    assert item["realizado_centavos"] == -2500


# --- Compra parcelada: uma parcela ou todas -------------------------------------------------


def parcelada_no_cartao(casal: Casal, **campos):
    cartao = novo_cartao(casal)["id"]
    mercado = casal.categoria("Mercado")
    novo = parcelamento(
        cartao,
        [mercado],
        data="2026-03-28",
        parcelas=3,
        valor_total_centavos=30000,
        tags=["viagem"],
        **campos,
    )
    assert casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo).status_code == 201
    return cartao, mercado, novo


def estorno_de_todas(casal: Casal, novo: dict, valor: int, data="2026-06-10", **campos):
    return casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(
            novo["conta_id"],
            [],
            data=data,
            valor_centavos=valor,
            estorno_parcelamento_id=novo["id"],
        )
        | campos,
    )


def test_estorno_de_todas_as_parcelas_e_um_so_ligado_ao_parcelamento_e_conta_inteiro(
    casal: Casal,
):
    cartao, mercado, novo = parcelada_no_cartao(casal)

    estorno = estorno_de_todas(casal, novo, 30000, categoria_ids=[], tags=["outra"])

    assert estorno.status_code == 201, estorno.text
    criado = estorno.json()
    assert (criado["estorno_de"], criado["estorno_parcelamento_id"]) == (None, novo["id"])
    assert (criado["categoria_ids"], criado["tags"]) == ([mercado], ["viagem"])
    junho = fatura(casal, cartao, criado["fatura_mes"])
    # A 3ª parcela (10.000) cai na mesma fatura: o crédito entra inteiro, não em três.
    assert junho["total_centavos"] == 10000 - 30000
    assert totais(casal, criado["mes"][:7])["despesas_centavos"] == 10000 - 30000


def test_estorno_de_todas_vai_ate_a_soma_das_parcelas_menos_o_ja_estornado(casal: Casal):
    _, _, novo = parcelada_no_cartao(casal)
    [primeira, *_] = parcelas(casal, novo["id"])
    da_primeira = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(
            novo["conta_id"],
            [],
            data="2026-04-26",
            valor_centavos=4000,
            estorno_de=primeira["id"],
        ),
    )
    assert da_primeira.status_code == 201, da_primeira.text

    acima = estorno_de_todas(casal, novo, 26001)
    todas = estorno_de_todas(casal, novo, 26000)
    sobra = estorno_de_todas(casal, novo, 1)

    assert (acima.status_code, acima.json()["detail"]) == (
        422,
        "estornos somam mais que o parcelamento",
    )
    assert (todas.status_code, sobra.status_code) == (201, 422)
    # Estorno de uma parcela depois do de todas também respeita o total.
    [_, segunda, _] = parcelas(casal, novo["id"])
    depois = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(
            novo["conta_id"],
            [],
            data="2026-06-10",
            valor_centavos=100,
            estorno_de=segunda["id"],
        ),
    )
    assert depois.status_code == 422


def test_estorno_de_todas_so_no_cartao_e_o_valor_editado_respeita_o_restante(casal: Casal):
    conta = casal.conta()
    no_boleto = parcelamento(conta, [casal.categoria("Empréstimo")], data="2026-11-30")
    assert casal.pedir("flavio", "POST", "/api/parcelamentos", json=no_boleto).status_code == 201
    _, _, novo = parcelada_no_cartao(casal)

    boleto = estorno_de_todas(casal, no_boleto, 100)
    primeiro = estorno_de_todas(casal, novo, 10000).json()
    segundo = estorno_de_todas(casal, novo, 20000)
    editado = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{primeiro['id']}",
        json={"versao": 1, "valor_centavos": 10001},
    )

    assert boleto.status_code == 422
    assert segundo.status_code == 201
    assert (editado.status_code, editado.json()["detail"]) == (
        422,
        "estornos somam mais que o parcelamento",
    )


def test_estorno_de_todas_acompanha_o_parcelamento_e_trava_a_exclusao_dele(casal: Casal):
    _, _, novo = parcelada_no_cartao(casal)
    estorno = estorno_de_todas(casal, novo, 10000).json()
    lazer = casal.categoria("Lazer")

    corrigido = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/parcelamentos/{novo['id']}",
        json={"categoria_ids": [lazer], "tags": ["natal"]},
    )
    excluido = casal.pedir("flavio", "DELETE", f"/api/parcelamentos/{novo['id']}")

    assert corrigido.status_code == 200, corrigido.text
    [lido] = [
        l
        for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()
        if l["id"] == estorno["id"]
    ]
    assert (lido["categoria_ids"], lido["tags"]) == ([lazer], ["natal"])
    assert (excluido.status_code, excluido.json()["detail"]) == (
        422,
        "o parcelamento tem estorno; exclua o estorno antes",
    )
    apagado = casal.pedir("flavio", "DELETE", f"/api/lancamentos/{estorno['id']}")
    assert apagado.status_code == 204
    sem_estorno = casal.pedir(
        "flavio", "DELETE", f"/api/parcelamentos/{novo['id']}?confirmar_realizadas=true"
    )
    assert sem_estorno.status_code == 204


def test_estorno_nao_mistura_parte_e_parcelamento_nem_aceita_os_dois_ligados(casal: Casal):
    cartao, _, novo = parcelada_no_cartao(casal)
    compra = comprar(casal, cartao, "2026-03-28", valor_centavos=1000)

    os_dois = estorno_de_todas(casal, novo, 100, estorno_de=compra["id"])
    avulso = estorno_de_todas(casal, novo, 100, estorno_avulso=True)

    assert os_dois.status_code == 422
    assert avulso.status_code == 422
