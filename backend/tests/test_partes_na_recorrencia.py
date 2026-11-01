"""Partes na recorrência (ticket 140, ADR 0022): a despesa recorrente que junta coisas diferentes
(o combo de celular e internet numa conta só) guarda as partes na regra, como proporção, e cada
ocorrência se divide por elas."""

from datetime import date
from uuid import uuid4

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_parcelamentos import cartao
from tests.test_partes_da_compra import parte
from tests.test_recorrencias import gerados, lote, mudar, recorrencia

HOJE = date(2026, 10, 28)


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lancamentos, "hoje", lambda: HOJE)


def combo(casal: Casal, partes: list[dict], **campos) -> dict:
    """O combo de celular e internet: uma regra só, com as partes e sem classificação própria."""
    return (
        recorrencia(
            casal.conta(),
            [],
            descricao="Combo",
            tipo_do_valor="fixo",
            valor_centavos=sum(p["valor_centavos"] for p in partes),
            vezes=3,
            partes=partes,
        )
        | campos
    )


def partes_de(lancamento: dict) -> list[tuple]:
    return [(p["descricao"], p["valor_centavos"], p["categoria_ids"]) for p in lancamento["partes"]]


def test_cada_ocorrencia_nasce_dividida_pelas_partes_da_regra(casal: Casal):
    celular, internet = casal.categoria("Celular"), casal.categoria("Internet")
    partes = [
        parte([celular], 6000, descricao="Celular", pessoa="esposa", tags=["combo"]),
        parte([internet], 4000, descricao="Internet"),
    ]
    nova = combo(casal, partes)

    resposta = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)

    assert resposta.status_code == 201, resposta.text
    regra = resposta.json()
    assert (regra["categoria_ids"], regra["tags"], regra["pessoa"]) == ([], [], None)
    assert [(p["id"], p["valor_centavos"], p["pessoa"], p["tags"]) for p in regra["partes"]] == [
        (partes[0]["id"], 6000, "esposa", ["combo"]),
        (partes[1]["id"], 4000, None, []),
    ]
    previstos = gerados(casal, nova["id"])
    assert len(previstos) == 3
    for previsto in previstos:
        assert (previsto["categoria_ids"], previsto["tags"], previsto["pessoa"]) == ([], [], None)
        assert partes_de(previsto) == [
            ("Celular", 6000, [celular]),
            ("Internet", 4000, [internet]),
        ]
        assert [(p["pessoa"], p["tags"]) for p in previsto["partes"]] == [
            ("esposa", ["combo"]),
            (None, []),
        ]
    # Cada previsto tem as partes dele: o id não se repete entre as ocorrências.
    assert len({p["id"] for l in previstos for p in l["partes"]}) == 6


def editar(casal: Casal, id: str, quem="flavio", **campos):
    return casal.pedir(quem, "PATCH", f"/api/lancamentos/{id}", json=campos)


def criada(casal: Casal, nova: dict) -> list[dict]:
    resposta = casal.pedir("flavio", "POST", "/api/recorrencias", json=nova)
    assert resposta.status_code == 201, resposta.text
    return gerados(casal, nova["id"])


def test_o_valor_do_mes_que_muda_divide_as_partes_de_novo_com_os_centavos_na_maior(
    casal: Casal,
):
    luz, agua = casal.categoria("Luz"), casal.categoria("Água")
    # A conta do condomínio junta luz e água, estimada: 2/3 e 1/3 de R$ 150,00.
    nova = combo(
        casal,
        [parte([agua], 5000, descricao="Água"), parte([luz], 10000, descricao="Luz")],
        tipo_do_valor="estimado",
    )
    [novembro, dezembro, _] = criada(casal, nova)

    editado = editar(casal, novembro["id"], versao=1, valor_centavos=20000)
    confirmado = casal.pedir(
        "flavio",
        "POST",
        f"/api/lancamentos/{dezembro['id']}/confirmar",
        json={"versao": 1, "valor_centavos": 10001},
    )

    assert editado.status_code == 200, editado.text
    # 20000 em 1/3 e 2/3: 6666 e 13333 somam 19999; o centavo que sobra vai para a maior.
    assert partes_de(editado.json()) == [("Água", 6666, [agua]), ("Luz", 13334, [luz])]
    assert confirmado.status_code == 200, confirmado.text
    assert partes_de(confirmado.json()) == [("Água", 3333, [agua]), ("Luz", 6668, [luz])]
    # Os ids das partes ficam: é a mesma parte, com outro valor.
    assert [p["id"] for p in editado.json()["partes"]] == [p["id"] for p in novembro["partes"]]


def test_o_valor_que_nao_da_um_centavo_para_cada_parte_e_recusado(casal: Casal):
    a, b = casal.categoria("A"), casal.categoria("B")
    [novembro, *_] = criada(casal, combo(casal, [parte([a], 9900), parte([b], 100)]))

    resposta = editar(casal, novembro["id"], versao=1, valor_centavos=50)

    assert resposta.status_code == 422
    assert "cada uma precisa de um centavo" in resposta.json()["detail"]


def test_so_este_muda_as_partes_do_previsto_e_daqui_para_frente_nao_o_sobrescreve(casal: Casal):
    celular, internet, tv = (
        casal.categoria("Celular"),
        casal.categoria("Internet"),
        casal.categoria("TV"),
    )
    nova = combo(casal, [parte([celular], 6000), parte([internet], 4000)], vezes=4)
    [novembro, dezembro, *_] = criada(casal, nova)

    # Só dezembro: a operadora cobrou a TV junto, no lugar de parte da internet.
    so_este = editar(
        casal,
        dezembro["id"],
        versao=1,
        partes=[parte([celular], 6000), parte([internet], 2500), parte([tv], 1500)],
    )
    assert so_este.status_code == 200, so_este.text

    # Daqui para frente, desde a 1ª: o combo passa a ter a TV, e a internet fica com menos.
    tres = [
        parte([celular], 5000, descricao="Celular"),
        parte([internet], 3000, descricao="Internet"),
        parte([tv], 2000, descricao="TV"),
    ]
    resposta = mudar(casal, nova["id"], 1, partes=tres)

    assert resposta.status_code == 200, resposta.text
    assert [(p["id"], p["valor_centavos"]) for p in resposta.json()["partes"]] == [
        (p["id"], p["valor_centavos"]) for p in tres
    ]
    previstos = gerados(casal, nova["id"])
    assert [[p["valor_centavos"] for p in l["partes"]] for l in previstos] == [
        [5000, 3000, 2000],
        [6000, 2500, 1500],
        [5000, 3000, 2000],
        [5000, 3000, 2000],
    ]
    assert previstos[0]["versao"] == novembro["versao"] + 1
    assert previstos[1]["versao"] == 2


def test_mudar_o_valor_da_regra_divide_as_partes_dela_de_novo(casal: Casal):
    celular, internet = casal.categoria("Celular"), casal.categoria("Internet")
    nova = combo(casal, [parte([celular], 6000), parte([internet], 4000)])
    criada(casal, nova)

    resposta = mudar(casal, nova["id"], 2, valor_centavos=12000)

    assert resposta.status_code == 200, resposta.text
    assert [p["valor_centavos"] for p in resposta.json()["partes"]] == [7200, 4800]
    assert [
        (l["valor_centavos"], [p["valor_centavos"] for p in l["partes"]])
        for l in gerados(casal, nova["id"])
    ] == [(10000, [6000, 4000]), (12000, [7200, 4800]), (12000, [7200, 4800])]


def test_dividir_e_juntar_a_regra_daqui_para_frente(casal: Casal):
    conta, celular, internet = (
        casal.conta(),
        casal.categoria("Celular"),
        casal.categoria("Internet"),
    )
    nova = recorrencia(conta, [celular], valor_centavos=10000, vezes=2, tags=["vivo"])
    criada(casal, nova)

    dividida = mudar(casal, nova["id"], 1, partes=[parte([celular], 6000), parte([internet], 4000)])

    assert dividida.status_code == 200, dividida.text
    assert (dividida.json()["categoria_ids"], dividida.json()["tags"]) == ([], [])
    assert [(l["categoria_ids"], len(l["partes"])) for l in gerados(casal, nova["id"])] == [
        ([], 2),
        ([], 2),
    ]

    fica = parte([internet], 4000, tags=["fibra"], pessoa="esposa")
    junta = mudar(casal, nova["id"], 2, partes=[fica])

    assert junta.status_code == 200, junta.text
    regra = junta.json()
    assert (regra["partes"], regra["categoria_ids"], regra["tags"], regra["pessoa"]) == (
        [],
        [internet],
        ["fibra"],
        "esposa",
    )
    # O valor da regra fica: juntar não muda quanto a conta custa.
    assert regra["valor_centavos"] == 10000
    assert [
        (len(l["partes"]), l["categoria_ids"], l["tags"]) for l in gerados(casal, nova["id"])
    ] == [(2, [], []), (0, [internet], ["fibra"])]


def test_regra_com_partes_que_nao_somam_ou_com_classificacao_propria_e_recusada(casal: Casal):
    celular, internet = casal.categoria("Celular"), casal.categoria("Internet")
    duas = [parte([celular], 6000), parte([internet], 4000)]

    nao_soma = casal.pedir(
        "flavio", "POST", "/api/recorrencias", json=combo(casal, duas, valor_centavos=9000)
    )
    com_categoria = casal.pedir(
        "flavio", "POST", "/api/recorrencias", json=combo(casal, duas, categoria_ids=[celular])
    )
    sem_nada = casal.pedir(
        "flavio", "POST", "/api/recorrencias", json=combo(casal, [], valor_centavos=10000)
    )

    assert [r.status_code for r in (nao_soma, com_categoria, sem_nada)] == [422] * 3
    assert "somam 10000 centavos e a compra, 9000" in nao_soma.text
    assert "não tem categoria, tag nem pessoa próprias" in com_categoria.text
    assert "sem categoria" in sem_nada.text
    assert casal.pedir("flavio", "GET", "/api/recorrencias").json() == []


def test_mudar_as_partes_pela_fila_e_recusado_se_a_outra_pessoa_as_mudou_depois(casal: Casal):
    celular, internet = casal.categoria("Celular"), casal.categoria("Internet")
    duas = [parte([celular], 6000), parte([internet], 4000)]
    nova = combo(casal, duas)
    criada(casal, nova)
    # A esposa viu o combo em 60/40 e mudou sem internet; o Flávio pôs 70/30 antes de ela subir.
    mudar(
        casal,
        nova["id"],
        1,
        partes=[duas[0] | {"valor_centavos": 7000}, duas[1] | {"valor_centavos": 3000}],
    )

    def alterar(alteracao: dict, antes: dict) -> dict:
        return {
            "acao": "alterar_recorrencia",
            "id": nova["id"],
            "alteracao": {"a_partir_da_ocorrencia": 1} | alteracao,
            "antes": antes,
        }

    meio = [duas[0] | {"valor_centavos": 5000}, duas[1] | {"valor_centavos": 5000}]
    resultados = lote(
        casal,
        "esposa",
        alterar({"partes": meio}, {"partes": duas}),
        # Outro campo passa: as partes do Flávio ficam.
        alterar({"descricao": "Vivo"}, {"descricao": "Combo"}),
    )

    assert [(r["resultado"], r["motivo"]) for r in resultados] == [
        ("recusada", "a regra mudou depois (partes): confira e mude de novo"),
        ("aceita", None),
    ]
    assert [
        (l["descricao"], [p["valor_centavos"] for p in l["partes"]])
        for l in gerados(casal, nova["id"])
    ] == [("Vivo", [7000, 3000])] * 3


def test_o_previsto_que_o_fim_tirou_volta_com_as_partes_da_regra_de_hoje(casal: Casal):
    celular, internet = casal.categoria("Celular"), casal.categoria("Internet")
    nova = combo(casal, [parte([celular], 6000), parte([internet], 4000)], vezes=None)
    criada(casal, nova)
    mudar(casal, nova["id"], 1, vezes=2)
    mudar(casal, nova["id"], 1, partes=[parte([celular], 5000), parte([internet], 5000)])

    resposta = mudar(casal, nova["id"], 2, vezes=None)

    assert resposta.status_code == 200, resposta.text
    previstos = gerados(casal, nova["id"])
    assert len(previstos) == 24
    volta = previstos[2]
    assert (volta["ocorrencia"], [p["valor_centavos"] for p in volta["partes"]]) == (
        3,
        [5000, 5000],
    )
    assert [p["categoria_ids"] for p in volta["partes"]] == [[celular], [internet]]


def test_juntar_categorias_e_tags_leva_as_das_partes_da_regra(casal: Casal):
    celular, internet, telefonia = (
        casal.categoria("Celular"),
        casal.categoria("Internet"),
        casal.categoria("Telefonia"),
    )
    nova = combo(
        casal, [parte([celular], 6000, tags=["vivo"]), parte([internet], 4000, tags=["fibra"])]
    )
    criada(casal, nova)
    tags = {t["nome"]: t["id"] for t in casal.pedir("flavio", "GET", "/api/tags").json()}

    casal.pedir(
        "flavio", "POST", f"/api/categorias/{celular}/juntar", json={"destino_id": telefonia}
    )
    casal.pedir(
        "flavio", "POST", f"/api/tags/{tags['vivo']}/juntar", json={"destino_id": tags["fibra"]}
    )

    [regra] = casal.pedir("flavio", "GET", "/api/recorrencias").json()
    assert [(p["categoria_ids"], p["tags"]) for p in regra["partes"]] == [
        ([telefonia], ["fibra"]),
        ([internet], ["fibra"]),
    ]
    # A regra segue gerando com a categoria e a tag de destino.
    resposta = mudar(casal, nova["id"], 1, descricao="Vivo")
    assert resposta.status_code == 200, resposta.text
    assert [
        [(p["categoria_ids"], p["tags"]) for p in l["partes"]] for l in gerados(casal, nova["id"])
    ] == [[([telefonia], ["fibra"]), ([internet], ["fibra"])]] * 3


def test_o_estorno_de_uma_ocorrencia_com_partes_espera_o_estorno_de_uma_parte(casal: Casal):
    """O estorno de uma parte é do ticket 138; a ocorrência é uma compra com partes como a à vista,
    e o estorno dela será de uma parte dela, não da regra."""
    no_cartao, celular, internet = (
        cartao(casal),
        casal.categoria("Celular"),
        casal.categoria("Internet"),
    )
    nova = combo(casal, [parte([celular], 6000), parte([internet], 4000)], conta_id=no_cartao)
    [novembro, *_] = criada(casal, nova)

    resposta = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json={
            "id": str(uuid4()),
            "tipo": "despesa",
            "valor_centavos": 4000,
            "data": "2026-11-12",
            "conta_id": no_cartao,
            "categoria_ids": [celular],
            "estorno_de": novembro["id"],
        },
    )

    assert (resposta.status_code, resposta.json()["detail"]) == (
        422,
        "o estorno de uma parte da compra ainda não existe",
    )


def test_dividir_pela_fila_e_recusado_se_a_outra_pessoa_trocou_a_categoria_depois(casal: Casal):
    conta, celular, internet = (
        casal.conta(),
        casal.categoria("Celular"),
        casal.categoria("Internet"),
    )
    telefonia = casal.categoria("Telefonia")
    nova = recorrencia(conta, [celular], valor_centavos=10000, vezes=2)
    criada(casal, nova)
    # O Flávio troca a categoria; a esposa, sem internet, ainda via Celular e dividiu a regra.
    mudar(casal, nova["id"], 1, categoria_ids=[telefonia])

    [resultado] = lote(
        casal,
        "esposa",
        {
            "acao": "alterar_recorrencia",
            "id": nova["id"],
            "alteracao": {
                "a_partir_da_ocorrencia": 1,
                "partes": [parte([celular], 6000), parte([internet], 4000)],
            },
            "antes": {
                "partes": [],
                "categoria_ids": [celular],
                "tags": [],
                "pessoa": None,
                "item_categoria_id": None,
            },
        },
    )

    assert (resultado["resultado"], resultado["motivo"]) == (
        "recusada",
        "a regra mudou depois (categorias): confira e mude de novo",
    )
    assert [l["categoria_ids"] for l in gerados(casal, nova["id"])] == [[telefonia], [telefonia]]
