"""A edição em lote na compra com partes (ticket 150, ADR 0022): a mudança vale em cada parte; na
busca com filtro de categoria, tag ou pessoa, só nas partes que ela achou."""

from tests.conftest import Casal
from tests.test_alcance_da_mudanca_na_parcela import editar_so_nela
from tests.test_edicao_em_lote import aplicada, aplicar, desfazer, marcados, previa, todos
from tests.test_estorno_de_parte_e_de_parcelas import compra_em_partes, estorno_da_parte
from tests.test_partes_da_compra import compra_com_partes, editar, parte
from tests.test_partes_na_compra_parcelada import categorias, parcelado, parcelas, regra
from tests.test_planejamento import item

__all__ = ["categorias"]


def classificacao_das_partes(casal: Casal, compra: dict) -> list[tuple[set[str], set[str]]]:
    return [(set(p["categoria_ids"]), set(p["tags"])) for p in todos(casal)[compra["id"]]["partes"]]


def test_marcada_a_mao_a_compra_com_partes_muda_em_todas_as_partes(casal: Casal):
    conta, roupa, casa = casal.conta(), casal.categoria("Roupa"), casal.categoria("Casa")
    compra = compra_com_partes(casal, conta, [parte([roupa], 600), parte([casa], 400)]).json()
    mudanca = {
        "categorias": {"acao": "acrescentar", "categoria_ids": [casa]},
        "tags": {"acao": "acrescentar", "tags": ["obra"]},
    }

    vista = previa(casal, marcados(compra), **mudanca)
    lote = aplicada(casal, marcados(compra), **mudanca)

    assert (vista["mudam"], vista["partes_que_mudam"], vista["ja_estao_como_pedido"]) == (1, 2, 0)
    [amostra] = vista["amostra"]
    assert [set(p["categoria_ids"]) for p in amostra["partes"]] == [{roupa, casa}, {casa}]
    assert (amostra["categoria_ids"], amostra["tags"]) == ([], [])
    assert lote["lancamentos"] == 1
    assert classificacao_das_partes(casal, compra) == [
        ({roupa, casa}, {"obra"}),
        ({casa}, {"obra"}),
    ]
    agora = todos(casal)[compra["id"]]
    # A compra continua sem classificação própria.
    assert (agora["categoria_ids"], agora["tags"], agora["versao"]) == ([], [], 2)


def _tres_partes(casal: Casal) -> tuple[dict, str, str, str]:
    """Vestido da esposa (Roupa), fone do Flávio (Roupa) e cortina do conjunto (Casa)."""
    roupa, casa, presente = (
        casal.categoria("Roupa"),
        casal.categoria("Casa"),
        casal.categoria("Presente"),
    )
    compra = compra_com_partes(
        casal,
        casal.conta(),
        [
            parte([roupa], 500, descricao="Vestido", pessoa="esposa"),
            parte([roupa], 250, descricao="Fone", pessoa="flavio"),
            parte([casa], 250, descricao="Cortina"),
        ],
        data="2026-10-02",
    ).json()
    return compra, roupa, casa, presente


def test_na_busca_com_filtro_muda_so_as_partes_que_ela_achou_mesmo_marcada_a_mao(casal: Casal):
    compra, roupa, casa, presente = _tres_partes(casal)
    da_esposa = {"busca": {"pessoas": ["esposa"]}, "lancamento_ids": [compra["id"]]}
    mudanca = {"categorias": {"acao": "acrescentar", "categoria_ids": [presente]}}

    vista = previa(casal, da_esposa, **mudanca)
    aplicada(casal, da_esposa, **mudanca)

    assert (vista["mudam"], vista["partes_que_mudam"]) == (1, 1)
    assert classificacao_das_partes(casal, compra) == [
        ({roupa, presente}, set()),
        ({roupa}, set()),
        ({casa}, set()),
    ]


def test_trocar_muda_so_as_partes_que_tem_a_categoria(casal: Casal):
    compra, roupa, casa, presente = _tres_partes(casal)
    mudanca = {"categorias": {"acao": "trocar", "categoria_ids": [roupa], "por": presente}}

    vista = previa(casal, marcados(compra), **mudanca)
    aplicada(casal, marcados(compra), **mudanca)

    assert vista["partes_que_mudam"] == 2
    assert [c for c, _ in classificacao_das_partes(casal, compra)] == [
        {presente},
        {presente},
        {casa},
    ]


def test_recusa_o_lote_que_deixaria_uma_parte_sem_categoria(casal: Casal):
    compra, roupa, casa, _ = _tres_partes(casal)
    mudanca = {"categorias": {"acao": "remover", "categoria_ids": [casa]}}

    vista = previa(casal, marcados(compra), **mudanca)
    recusada = aplicar(casal, marcados(compra), **mudanca)

    assert vista["recusa"] == "o lote deixaria 1 parte sem categoria"
    assert recusada.status_code == 422
    assert [c for c, _ in classificacao_das_partes(casal, compra)] == [{roupa}, {roupa}, {casa}]


def test_previa_conta_as_partes_que_trocam_de_item(casal: Casal):
    compra, roupa, _, presente = _tres_partes(casal)
    item(casal, roupa, 100000)
    item(casal, presente, 100000)
    mudanca = {"categorias": {"acao": "trocar", "categoria_ids": [roupa], "por": presente}}

    vista = previa(casal, marcados(compra), **mudanca)

    assert (vista["mudam"], vista["trocam_de_item"]) == (1, 2)


def test_desfazer_volta_as_partes_e_pula_a_compra_cujas_partes_mudaram_depois(casal: Casal):
    compra, roupa, casa, _ = _tres_partes(casal)
    outra, *_ = _tres_partes(casal)
    mudanca = {"tags": {"acao": "acrescentar", "tags": ["obra"]}}
    lote = aplicada(casal, marcados(compra, outra), **mudanca)
    depois = todos(casal)[outra["id"]]
    partes = [p | {"tags": []} for p in depois["partes"]]
    editada = editar(casal, outra["id"], versao=depois["versao"], partes=partes)
    assert editada.status_code == 200, editada.text

    resposta = desfazer(casal, lote)

    assert resposta.status_code == 200, resposta.text
    desfeito = resposta.json()
    assert desfeito["desfeitos"] == 1, desfeito
    assert [(p["lancamento_id"], p["motivo"]) for p in desfeito["pulados"]] == [
        (outra["id"], "mudou_depois")
    ]
    assert classificacao_das_partes(casal, compra) == [
        ({roupa}, set()),
        ({roupa}, set()),
        ({casa}, set()),
    ]


def test_o_estorno_de_uma_parte_acompanha_a_parte_e_volta_com_o_desfazer(casal: Casal):
    _, _, casa, compra = compra_em_partes(casal)
    estorno = estorno_da_parte(casal, compra, 1, 1000).json()
    obra = casal.categoria("Obra")
    mudanca = {"categorias": {"acao": "trocar", "categoria_ids": [casa], "por": obra}}

    lote = aplicada(casal, marcados(compra, estorno), **mudanca)
    depois = todos(casal)[estorno["id"]]
    desfazer(casal, lote)
    desfeito = todos(casal)[estorno["id"]]

    assert lote["lancamentos"] == 1
    assert depois["categoria_ids"] == [obra]
    assert desfeito["categoria_ids"] == [casa]


def test_no_parcelamento_com_partes_muda_as_partes_dele_e_de_cada_parcela(casal: Casal, categorias):
    roupa, eletronico, casa = categorias
    criado = parcelado(casal, casal.conta(), [parte([roupa], 20000), parte([casa], 10000)]).json()
    [primeira, segunda, _] = parcelas(casal, criado["id"])
    # A 2ª tem partes próprias: a mudança vale nas dela, e ela segue alterada à mão.
    so_nela = [p | {"categoria_ids": [eletronico]} for p in segunda["partes"]]
    editar_so_nela(casal, segunda, partes=so_nela)
    mudanca = {"tags": {"acao": "acrescentar", "tags": ["loja"]}}

    vista = previa(casal, marcados(primeira), **mudanca)
    lote = aplicada(casal, marcados(primeira), **mudanca)

    assert (vista["compras"], vista["mudam"], vista["partes_que_mudam"]) == (1, 3, 6)
    assert [p["tags"] for p in regra(casal, criado["id"])["partes"]] == [["loja"], ["loja"]]
    agora = parcelas(casal, criado["id"])
    assert [[p["tags"] for p in l["partes"]] for l in agora] == [[["loja"], ["loja"]]] * 3
    assert [l["alterada_a_mao"] for l in agora] == [False, True, False]
    assert [p["categoria_ids"] for p in agora[1]["partes"]] == [[eletronico], [eletronico]]

    desfazer(casal, lote)

    assert [p["tags"] for p in regra(casal, criado["id"])["partes"]] == [[], []]
    assert [[p["tags"] for p in l["partes"]] for l in parcelas(casal, criado["id"])] == [
        [[], []]
    ] * 3


def test_na_busca_com_filtro_o_parcelamento_muda_so_as_partes_achadas(casal: Casal, categorias):
    roupa, _, casa = categorias
    criado = parcelado(casal, casal.conta(), [parte([roupa], 20000), parte([casa], 10000)]).json()
    da_casa = {"busca": {"categoria_ids": [casa]}}
    obra = casal.categoria("Obra")

    aplicada(casal, da_casa, categorias={"acao": "acrescentar", "categoria_ids": [obra]})

    assert [set(p["categoria_ids"]) for p in regra(casal, criado["id"])["partes"]] == [
        {roupa},
        {casa, obra},
    ]
    assert [
        [set(p["categoria_ids"]) for p in l["partes"]] for l in parcelas(casal, criado["id"])
    ] == [[{roupa}, {casa, obra}]] * 3
