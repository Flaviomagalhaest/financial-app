"""A edição em lote na compra com partes (ticket 150, ADR 0022): a mudança vale em cada parte; na
busca com filtro de categoria, tag ou pessoa, só nas partes que ela achou."""

import pytest

from app import lancamentos
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


def test_desfazer_volta_as_partes_e_pula_cada_parte_reclassificada_depois(casal: Casal):
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
    assert [
        (p["lancamento_id"], p["parte_descricao"], p["motivo"]) for p in desfeito["pulados"]
    ] == [(outra["id"], descricao, "mudou_depois") for descricao in ("Vestido", "Fone", "Cortina")]
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


def test_na_ocorrencia_da_recorrencia_muda_as_partes_como_so_este(
    casal: Casal, monkeypatch: pytest.MonkeyPatch
):
    from tests.test_partes_na_recorrencia import HOJE, combo, criada
    from tests.test_recorrencias import gerados, mudar

    monkeypatch.setattr(lancamentos, "hoje", lambda: HOJE)

    celular, internet = casal.categoria("Celular"), casal.categoria("Internet")
    nova = combo(casal, [parte([celular], 6000), parte([internet], 4000)], vezes=3)
    [novembro, dezembro, _] = criada(casal, nova)

    aplicada(casal, marcados(dezembro), tags={"acao": "acrescentar", "tags": ["combo"]})
    # Daqui para frente, desde a 1ª: o lote fez de dezembro um "só este", que a mudança não alcança.
    trocadas = [
        parte([internet], 6000, descricao="Internet"),
        parte([celular], 4000, descricao="Celular"),
    ]
    assert mudar(casal, nova["id"], 1, partes=trocadas).status_code == 200

    agora = {l["id"]: l for l in gerados(casal, nova["id"])}
    assert [p["tags"] for p in agora[dezembro["id"]]["partes"]] == [["combo"], ["combo"]]
    assert [p["categoria_ids"] for p in agora[dezembro["id"]]["partes"]] == [[celular], [internet]]
    assert [p["categoria_ids"] for p in agora[novembro["id"]]["partes"]] == [[internet], [celular]]


def _reclassificar(casal: Casal, compra: dict, indice: int, quem="flavio", **campos) -> dict:
    """Muda depois do lote uma parte da compra (ou, sem `campos`, nada nela), à mão."""
    agora = todos(casal)[compra["id"]]
    partes = [p | campos if i == indice else p for i, p in enumerate(agora["partes"])]
    editada = editar(casal, compra["id"], quem, versao=agora["versao"], partes=partes)
    assert editada.status_code == 200, editada.text
    return editada.json()


def test_desfazer_pula_so_a_parte_reclassificada_depois_e_volta_as_outras(casal: Casal):
    compra, roupa, casa, presente = _tres_partes(casal)
    lote = aplicada(casal, marcados(compra), tags={"acao": "acrescentar", "tags": ["obra"]})
    _reclassificar(casal, compra, 1, categoria_ids=[presente])

    resposta = desfazer(casal, lote)

    assert resposta.status_code == 200, resposta.text
    desfeito = resposta.json()
    assert desfeito["desfeitos"] == 1
    [pulado] = desfeito["pulados"]
    fone = todos(casal)[compra["id"]]["partes"][1]
    assert (
        pulado["lancamento_id"],
        pulado["descricao"],
        pulado["parte_id"],
        pulado["parte_descricao"],
        pulado["motivo"],
        pulado["alterado_por"],
        pulado["por_voce"],
    ) == (compra["id"], "Mercado Livre", fone["id"], "Fone", "mudou_depois", "flavio", False)
    assert pulado["alterado_em"] is not None
    assert classificacao_das_partes(casal, compra) == [
        ({roupa}, set()),
        ({presente}, {"obra"}),
        ({casa}, set()),
    ]


def test_descricao_valor_pessoa_e_ordem_mudados_depois_nao_impedem_o_desfazer(casal: Casal):
    compra, roupa, casa, _ = _tres_partes(casal)
    lote = aplicada(casal, marcados(compra), tags={"acao": "acrescentar", "tags": ["obra"]})
    agora = todos(casal)[compra["id"]]
    vestido, fone, cortina = agora["partes"]
    editada = editar(
        casal,
        compra["id"],
        versao=agora["versao"],
        partes=[
            cortina | {"pessoa": "esposa"},
            fone | {"valor_centavos": 500},
            vestido | {"descricao": "Vestido azul", "valor_centavos": 250},
        ],
    )
    assert editada.status_code == 200, editada.text

    desfeito = desfazer(casal, lote).json()

    assert (desfeito["desfeitos"], desfeito["pulados"]) == (1, [])
    assert classificacao_das_partes(casal, compra) == [
        ({casa}, set()),
        ({roupa}, set()),
        ({roupa}, set()),
    ]
    assert [p["descricao"] for p in todos(casal)[compra["id"]]["partes"]] == [
        "Cortina",
        "Fone",
        "Vestido azul",
    ]


def test_a_parte_apagada_depois_e_pulada_e_a_criada_depois_fica_como_esta(casal: Casal):
    compra, roupa, casa, _ = _tres_partes(casal)
    lote = aplicada(casal, marcados(compra), tags={"acao": "acrescentar", "tags": ["obra"]})
    agora = todos(casal)[compra["id"]]
    vestido, fone, cortina = agora["partes"]
    bolsa = parte([roupa], 250, descricao="Bolsa", tags=["obra"])
    editada = editar(casal, compra["id"], versao=agora["versao"], partes=[vestido, bolsa, cortina])
    assert editada.status_code == 200, editada.text

    desfeito = desfazer(casal, lote, "flavio").json()

    assert desfeito["desfeitos"] == 1
    [pulado] = desfeito["pulados"]
    assert (
        pulado["parte_id"],
        pulado["parte_descricao"],
        pulado["motivo"],
        pulado["alterado_por"],
        pulado["por_voce"],
    ) == (fone["id"], "", "excluido", "flavio", True)
    assert classificacao_das_partes(casal, compra) == [
        ({roupa}, set()),
        ({roupa}, {"obra"}),
        ({casa}, set()),
    ]


def test_a_parte_com_categoria_de_antes_juntada_depois_sai_e_as_outras_voltam(casal: Casal):
    compra, roupa, casa, presente = _tres_partes(casal)
    lote = aplicada(
        casal,
        marcados(compra),
        categorias={"acao": "trocar", "categoria_ids": [roupa], "por": presente},
        tags={"acao": "acrescentar", "tags": ["obra"]},
    )
    juntada = casal.pedir(
        "flavio", "POST", f"/api/categorias/{roupa}/juntar", json={"destino_id": casa}
    )
    assert juntada.status_code == 200, juntada.text

    desfeito = desfazer(casal, lote).json()

    assert desfeito["desfeitos"] == 1
    assert [
        (p["parte_descricao"], p["motivo"], p["alterado_por"]) for p in desfeito["pulados"]
    ] == [("Vestido", "saiu", None), ("Fone", "saiu", None)]
    assert classificacao_das_partes(casal, compra) == [
        ({presente}, {"obra"}),
        ({presente}, {"obra"}),
        ({casa}, set()),
    ]


def test_a_compra_que_perdeu_todas_as_partes_depois_e_pulada_inteira(casal: Casal):
    compra, roupa, _, _ = _tres_partes(casal)
    outra, *_ = _tres_partes(casal)
    lote = aplicada(casal, marcados(compra, outra), tags={"acao": "acrescentar", "tags": ["obra"]})
    agora = todos(casal)[compra["id"]]
    editada = editar(casal, compra["id"], versao=agora["versao"], partes=[], categoria_ids=[roupa])
    assert editada.status_code == 200, editada.text

    desfeito = desfazer(casal, lote).json()

    assert desfeito["desfeitos"] == 1
    [pulado] = desfeito["pulados"]
    assert (
        pulado["lancamento_id"],
        pulado["parte_id"],
        pulado["parte_descricao"],
        pulado["motivo"],
        pulado["alterado_por"],
    ) == (compra["id"], None, "", "mudou_depois", "flavio")
    assert [t for _, t in classificacao_das_partes(casal, outra)] == [set()] * 3
    assert (todos(casal)[compra["id"]]["categoria_ids"], todos(casal)[compra["id"]]["partes"]) == (
        [roupa],
        [],
    )


def test_no_parcelamento_pula_so_a_parte_reclassificada_e_volta_as_outras(casal: Casal, categorias):
    from tests.test_partes_pela_tela_do_parcelamento import mudar_partes

    roupa, eletronico, casa = categorias
    criado = parcelado(casal, casal.conta(), [parte([roupa], 20000), parte([casa], 10000)]).json()
    [primeira, *_] = parcelas(casal, criado["id"])
    lote = aplicada(casal, marcados(primeira), tags={"acao": "acrescentar", "tags": ["loja"]})
    [blusa, cortina] = regra(casal, criado["id"])["partes"]
    mudada = mudar_partes(casal, criado["id"], [blusa | {"categoria_ids": [eletronico]}, cortina])
    assert mudada.status_code == 200, mudada.text

    desfeito = desfazer(casal, lote).json()

    assert desfeito["desfeitos"] == 3
    # Um pulado por parcela: a blusa dela, refeita pelo parcelamento.
    blusas = {l["id"]: l["partes"][0]["id"] for l in parcelas(casal, criado["id"])}
    assert {p["lancamento_id"]: p["parte_id"] for p in desfeito["pulados"]} == blusas
    assert {(p["motivo"], p["alterado_por"]) for p in desfeito["pulados"]} == {
        ("mudou_depois", "flavio")
    }
    assert all(p["alterado_em"] for p in desfeito["pulados"])
    assert [(p["categoria_ids"], p["tags"]) for p in regra(casal, criado["id"])["partes"]] == [
        ([eletronico], ["loja"]),
        ([casa], []),
    ]
    assert [
        [(p["categoria_ids"], p["tags"]) for p in l["partes"]]
        for l in parcelas(casal, criado["id"])
    ] == [[([eletronico], ["loja"]), ([casa], [])]] * 3


def test_na_parcela_com_partes_proprias_pula_so_a_parte_reclassificada(casal: Casal, categorias):
    roupa, eletronico, casa = categorias
    criado = parcelado(casal, casal.conta(), [parte([roupa], 20000), parte([casa], 10000)]).json()
    [primeira, segunda, _] = parcelas(casal, criado["id"])
    lote = aplicada(casal, marcados(primeira), tags={"acao": "acrescentar", "tags": ["loja"]})
    segunda = parcelas(casal, criado["id"])[1]
    so_nela = [segunda["partes"][0] | {"categoria_ids": [eletronico]}, segunda["partes"][1]]
    editar_so_nela(casal, segunda, partes=so_nela)

    desfeito = desfazer(casal, lote).json()

    assert desfeito["desfeitos"] == 3
    [pulado] = desfeito["pulados"]
    assert (pulado["lancamento_id"], pulado["parte_id"], pulado["motivo"]) == (
        segunda["id"],
        segunda["partes"][0]["id"],
        "mudou_depois",
    )
    assert pulado["alterado_por"] == "flavio"
    assert [p["tags"] for p in regra(casal, criado["id"])["partes"]] == [[], []]
    assert [
        [(p["categoria_ids"], p["tags"]) for p in l["partes"]]
        for l in parcelas(casal, criado["id"])
    ] == [
        [([roupa], []), ([casa], [])],
        [([eletronico], ["loja"]), ([casa], [])],
        [([roupa], []), ([casa], [])],
    ]


def test_a_parte_com_categoria_de_antes_excluida_depois_sai(casal: Casal):
    compra, roupa, _, presente = _tres_partes(casal)
    lote = aplicada(
        casal,
        marcados(compra),
        categorias={"acao": "trocar", "categoria_ids": [roupa], "por": presente},
    )
    excluida = casal.pedir("flavio", "DELETE", f"/api/categorias/{roupa}")
    assert excluida.status_code in (200, 204), excluida.text

    desfeito = desfazer(casal, lote).json()

    assert desfeito["desfeitos"] == 0
    assert [(p["parte_descricao"], p["motivo"]) for p in desfeito["pulados"]] == [
        ("Vestido", "saiu"),
        ("Fone", "saiu"),
    ]
