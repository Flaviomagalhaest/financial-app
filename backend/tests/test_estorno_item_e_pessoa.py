"""Item e pessoa do estorno acompanham a compra (ticket 191, ADR 0016)."""

from tests.conftest import Casal
from tests.test_cartoes import novo_cartao
from tests.test_estorno_de_parte_e_de_parcelas import (
    compra_em_partes,
    corrigir,
    estorno_da_parte,
    estorno_de_todas,
)
from tests.test_estorno_e_ajuste import estornar
from tests.test_lancamentos import lancamento
from tests.test_parcelamentos import parcelamento
from tests.test_partes_da_compra import parte


def lido(casal: Casal, id: str) -> dict:
    [achado] = [l for l in casal.pedir("flavio", "GET", "/api/lancamentos").json() if l["id"] == id]
    return achado


def parcelado_com_item(casal: Casal, **campos):
    cartao = novo_cartao(casal)["id"]
    mercado, lazer = casal.categoria("Mercado"), casal.categoria("Lazer")
    novo = (
        parcelamento(
            cartao,
            [mercado, lazer],
            data="2026-03-28",
            parcelas=3,
            valor_total_centavos=30000,
            item_categoria_id=lazer,
        )
        | campos
    )
    assert casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo).status_code == 201
    return mercado, lazer, novo


def test_estorno_de_todas_sem_partes_leva_o_item_do_parcelamento_e_o_acompanha(casal: Casal):
    mercado, lazer, novo = parcelado_com_item(casal)

    estorno = estorno_de_todas(casal, novo, 1000)

    assert estorno.status_code == 201, estorno.text
    assert estorno.json()["item_categoria_id"] == lazer
    corrigido = corrigir(casal, novo, item_categoria_id=mercado)
    assert corrigido.status_code == 200, corrigido.text
    assert lido(casal, estorno.json()["id"])["item_categoria_id"] == mercado


def test_estorno_de_todas_sem_partes_acompanha_a_edicao_em_lote_do_item(casal: Casal):
    _, _, novo = parcelado_com_item(casal)
    estorno = estorno_de_todas(casal, novo, 1000).json()

    corrigido = corrigir(casal, novo, item_categoria_id=None)

    assert corrigido.status_code == 200, corrigido.text
    assert lido(casal, estorno["id"])["item_categoria_id"] is None


def test_estorno_de_todas_leva_a_pessoa_do_parcelamento_e_ignora_a_do_cliente(casal: Casal):
    _, _, novo = parcelado_com_item(casal, pessoa="flavio")

    estorno = estorno_de_todas(casal, novo, 1000, pessoa="esposa")

    assert estorno.json()["pessoa"] == "flavio"
    assert corrigir(casal, novo, pessoa="esposa").status_code == 200
    assert lido(casal, estorno.json()["id"])["pessoa"] == "esposa"


def test_estorno_de_parte_leva_a_pessoa_da_parte_e_a_acompanha(casal: Casal):
    *_, compra = compra_em_partes(casal)
    parte0 = compra["partes"][0]
    assert parte0["pessoa"] is None

    estorno = estorno_da_parte(casal, compra, 0, 1000, pessoa="esposa")

    assert estorno.json()["pessoa"] is None
    partes = [
        {**p, "pessoa": "flavio" if i == 0 else p.get("pessoa")}
        for i, p in enumerate(compra["partes"])
    ]
    editado = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{compra['id']}",
        json={"partes": partes, "versao": compra["versao"]},
    )
    assert editado.status_code == 200, editado.text
    assert lido(casal, estorno.json()["id"])["pessoa"] == "flavio"


def test_estorno_de_compra_sem_partes_leva_a_pessoa_da_compra_e_o_avulso_guarda_a_dada(
    casal: Casal,
):
    cartao = novo_cartao(casal)["id"]
    mercado = casal.categoria("Mercado")
    compra = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(
            cartao, [mercado], data="2026-03-28", valor_centavos=10000, pessoa="flavio"
        ),
    ).json()

    ligado = estornar(casal, compra, "2026-04-02", valor_centavos=1000, pessoa="esposa")
    avulso = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(
            cartao, [], data="2026-04-02", valor_centavos=500, estorno_avulso=True, pessoa="esposa"
        ),
    )

    assert ligado.json()["pessoa"] == "flavio"
    assert avulso.status_code == 201, avulso.text
    assert avulso.json()["pessoa"] == "esposa"


def test_estorno_ligado_nao_muda_de_pessoa_pela_edicao(casal: Casal):
    _, _, novo = parcelado_com_item(casal, pessoa="flavio")
    estorno = estorno_de_todas(casal, novo, 1000).json()

    editado = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{estorno['id']}",
        json={"versao": estorno["versao"], "pessoa": "esposa"},
    )

    assert editado.status_code == 422, editado.text
    assert lido(casal, estorno["id"])["pessoa"] == "flavio"


def test_estorno_anterior_a_divisao_da_compra_fica_com_a_pessoa_que_tinha(casal: Casal):
    cartao = novo_cartao(casal)["id"]
    roupa, casa = casal.categoria("Roupa"), casal.categoria("Casa")
    compra = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(cartao, [roupa], data="2026-03-28", valor_centavos=10000, pessoa="flavio"),
    ).json()
    estorno = estornar(casal, compra, "2026-04-02", valor_centavos=1000).json()
    assert estorno["pessoa"] == "flavio"

    dividida = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/lancamentos/{compra['id']}",
        json={
            "versao": compra["versao"],
            "partes": [
                parte([roupa], 6000, descricao="A", pessoa="esposa"),
                parte([casa], 4000, descricao="B", pessoa="esposa"),
            ],
        },
    )

    assert dividida.status_code == 200, dividida.text
    assert lido(casal, estorno["id"])["pessoa"] == "flavio"
