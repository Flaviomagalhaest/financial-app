from tests.conftest import Casal, lancamento


def test_renomear_categoria_aparece_no_historico_sem_mexer_nos_lancamentos(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    novo = lancamento(conta, [mercado])
    casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)

    resposta = casal.pedir("esposa", "PATCH", f"/api/categorias/{mercado}", json={"nome": "Feira"})

    assert resposta.status_code == 200
    assert resposta.json() == {
        "id": mercado,
        "nome": "Feira",
        "tipo": "despesa",
        "arquivada": False,
    }
    [visto] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert visto["categoria_ids"] == [mercado]
    [categoria] = casal.pedir("flavio", "GET", "/api/categorias").json()
    assert categoria["nome"] == "Feira"


def test_categoria_arquivada_sai_das_opcoes_mas_o_historico_a_mantem(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    antigo = lancamento(conta, [mercado])
    casal.pedir("flavio", "POST", "/api/lancamentos", json=antigo)

    arquivada = casal.pedir(
        "flavio", "PATCH", f"/api/categorias/{mercado}", json={"arquivada": True}
    )
    novo = casal.pedir("flavio", "POST", "/api/lancamentos", json=lancamento(conta, [mercado]))
    editado = casal.pedir(
        "flavio", "PUT", f"/api/lancamentos/{antigo['id']}", json=antigo | {"descricao": "Feira"}
    )

    assert arquivada.json()["arquivada"] is True
    assert novo.status_code == 422
    assert editado.status_code == 200  # quem já a tinha continua com ela
    desarquivada = casal.pedir(
        "flavio", "PATCH", f"/api/categorias/{mercado}", json={"arquivada": False}
    )
    assert desarquivada.json()["arquivada"] is False
    nova = casal.pedir("flavio", "POST", "/api/lancamentos", json=lancamento(conta, [mercado]))
    assert nova.status_code == 201


def test_juntar_categorias_move_os_lancamentos_sem_repetir_e_some_com_a_origem(casal: Casal):
    conta = casal.conta()
    mercado, feira, viagem = (
        casal.categoria("Mercado"),
        casal.categoria("Feira"),
        casal.categoria("Viagem"),
    )
    so_origem = lancamento(conta, [mercado])
    nas_duas = lancamento(conta, [mercado, feira, viagem])
    for novo in (so_origem, nas_duas):
        casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)

    resposta = casal.pedir(
        "flavio", "POST", f"/api/categorias/{mercado}/juntar", json={"destino_id": feira}
    )

    assert resposta.status_code == 200
    assert resposta.json()["id"] == feira
    vistos = {
        l["id"]: l["categoria_ids"] for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()
    }
    assert vistos == {so_origem["id"]: [feira], nas_duas["id"]: sorted([feira, viagem])}
    assert [c["id"] for c in casal.pedir("flavio", "GET", "/api/categorias").json()].count(
        mercado
    ) == 0


def test_juntar_recusa_destino_de_outro_tipo_ou_o_proprio_ou_inexistente(casal: Casal):
    mercado, salario = casal.categoria("Mercado"), casal.categoria("Salário", "receita")
    juntar = lambda destino: casal.pedir(
        "flavio", "POST", f"/api/categorias/{mercado}/juntar", json={"destino_id": destino}
    )

    assert juntar(salario).status_code == 422
    assert juntar(mercado).status_code == 422
    assert juntar("00000000-0000-0000-0000-000000000000").status_code == 404


def test_excluir_categoria_so_sem_lancamentos(casal: Casal):
    conta, usada, solta = casal.conta(), casal.categoria("Mercado"), casal.categoria("Solta")
    casal.pedir("flavio", "POST", "/api/lancamentos", json=lancamento(conta, [usada]))

    recusada = casal.pedir("flavio", "DELETE", f"/api/categorias/{usada}")
    excluida = casal.pedir("flavio", "DELETE", f"/api/categorias/{solta}")
    de_novo = casal.pedir("flavio", "DELETE", f"/api/categorias/{solta}")

    assert recusada.status_code == 409
    assert excluida.status_code == 204
    assert de_novo.status_code == 204
    assert [c["id"] for c in casal.pedir("flavio", "GET", "/api/categorias").json()] == [usada]


def tags_de(casal: Casal) -> dict[str, dict]:
    return {t["nome"]: t for t in casal.pedir("flavio", "GET", "/api/tags").json()}


def test_tag_nasce_no_proprio_lancamento_e_e_reaproveitada(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    primeiro = lancamento(conta, [mercado], tags=["novo ap", "férias"])
    segundo = lancamento(conta, [mercado], tags=["novo ap"])

    criado = casal.pedir("flavio", "POST", "/api/lancamentos", json=primeiro)
    casal.pedir("esposa", "POST", "/api/lancamentos", json=segundo)
    sem_tag = casal.pedir("flavio", "POST", "/api/lancamentos", json=lancamento(conta, [mercado]))

    assert criado.json()["tags"] == ["férias", "novo ap"]
    assert sem_tag.json()["tags"] == []
    assert sorted(tags_de(casal)) == ["férias", "novo ap"]
    vistos = {l["id"]: l["tags"] for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()}
    assert vistos[segundo["id"]] == ["novo ap"]


def test_editar_lancamento_troca_as_tags(casal: Casal):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    novo = lancamento(conta, [mercado], tags=["novo ap"])
    casal.pedir("flavio", "POST", "/api/lancamentos", json=novo)

    editado = casal.pedir(
        "flavio", "PUT", f"/api/lancamentos/{novo['id']}", json=novo | {"tags": ["obra"]}
    )
    sem = casal.pedir("flavio", "PUT", f"/api/lancamentos/{novo['id']}", json=novo | {"tags": []})

    assert editado.json()["tags"] == ["obra"]
    assert sem.json()["tags"] == []


def lancar_com_tags(casal: Casal, *tags: str) -> dict:
    novo = lancamento(casal.conta(), [casal.categoria(f"c{len(tags)}{tags}")], tags=list(tags))
    assert casal.pedir("flavio", "POST", "/api/lancamentos", json=novo).status_code == 201
    return novo


def test_renomear_tag_reflete_nos_lancamentos(casal: Casal):
    lancar_com_tags(casal, "novo ap")
    [tag] = tags_de(casal).values()

    resposta = casal.pedir(
        "esposa", "PATCH", f"/api/tags/{tag['id']}", json={"nome": "apartamento"}
    )

    assert resposta.json() == {"id": tag["id"], "nome": "apartamento", "arquivada": False}
    [visto] = casal.pedir("flavio", "GET", "/api/lancamentos").json()
    assert visto["tags"] == ["apartamento"]


def test_tag_arquivada_sai_das_opcoes_mas_o_historico_a_mantem(casal: Casal):
    antigo = lancar_com_tags(casal, "obra")
    [tag] = tags_de(casal).values()

    arquivada = casal.pedir("flavio", "PATCH", f"/api/tags/{tag['id']}", json={"arquivada": True})
    novo = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(antigo["conta_id"], antigo["categoria_ids"], tags=["obra"]),
    )
    editado = casal.pedir(
        "flavio", "PUT", f"/api/lancamentos/{antigo['id']}", json=antigo | {"descricao": "x"}
    )

    assert arquivada.json()["arquivada"] is True
    assert novo.status_code == 422
    assert editado.status_code == 200
    assert editado.json()["tags"] == ["obra"]


def test_juntar_tags_move_os_lancamentos_sem_repetir(casal: Casal):
    so_origem = lancar_com_tags(casal, "obra")
    nas_duas = lancar_com_tags(casal, "obra", "novo ap")
    tags = tags_de(casal)

    resposta = casal.pedir(
        "flavio",
        "POST",
        f"/api/tags/{tags['obra']['id']}/juntar",
        json={"destino_id": tags["novo ap"]["id"]},
    )

    assert resposta.status_code == 200
    assert resposta.json()["id"] == tags["novo ap"]["id"]
    vistos = {l["id"]: l["tags"] for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()}
    assert vistos == {so_origem["id"]: ["novo ap"], nas_duas["id"]: ["novo ap"]}
    assert list(tags_de(casal)) == ["novo ap"]
    mesma = casal.pedir(
        "flavio",
        "POST",
        f"/api/tags/{tags['novo ap']['id']}/juntar",
        json={"destino_id": tags["novo ap"]["id"]},
    )
    assert mesma.status_code == 422


def test_excluir_tag_so_sem_lancamentos(casal: Casal):
    lancar_com_tags(casal, "usada")
    solta = casal.pedir("flavio", "POST", "/api/tags", json={"nome": "solta"})
    tags = tags_de(casal)

    recusada = casal.pedir("flavio", "DELETE", f"/api/tags/{tags['usada']['id']}")
    excluida = casal.pedir("flavio", "DELETE", f"/api/tags/{tags['solta']['id']}")

    assert solta.status_code == 201
    assert recusada.status_code == 409
    assert excluida.status_code == 204
    assert list(tags_de(casal)) == ["usada"]
