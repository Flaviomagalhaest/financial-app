"""Favoritos (ticket 62): lançamentos-modelo que o casal lança com um toque. O valor padrão é o
do último lançamento feito com eles; os mais repetidos viram sugeridos."""

from uuid import uuid4

from tests.conftest import Casal
from tests.test_lancamentos import lancamento


def lancar(casal: Casal, conta: str, categorias: list[str], **campos) -> dict:
    resposta = casal.pedir(
        "flavio", "POST", "/api/lancamentos", json=lancamento(conta, categorias, **campos)
    )
    assert resposta.status_code == 201
    return resposta.json()


def favorito(conta: str, categorias: list[str], **campos) -> dict:
    return {
        "id": str(uuid4()),
        "descricao": "Café da padaria",
        "tipo": "despesa",
        "conta_id": conta,
        "categoria_ids": categorias,
        "tags": [],
        "pessoa": None,
        "valor_centavos": 1200,
    } | campos


def listar(casal: Casal, quem: str = "esposa") -> dict:
    resposta = casal.pedir(quem, "GET", "/api/favoritos")
    assert resposta.status_code == 200
    return resposta.json()


def test_o_favorito_criado_por_um_aparece_para_o_outro_com_o_valor_inicial(casal: Casal):
    conta, cafe = casal.conta(), casal.categoria("Café")
    novo = favorito(conta, [cafe], tags=["Rotina"], pessoa="flavio")

    criado = casal.pedir("flavio", "POST", "/api/favoritos", json=novo)

    assert criado.status_code == 201
    [visto] = listar(casal)["favoritos"]
    assert visto == novo | {"valor_padrao_centavos": 1200, "ordem": 1}


def test_o_valor_padrao_e_o_do_ultimo_lancamento_feito_com_o_favorito(casal: Casal):
    conta, cafe = casal.conta(), casal.categoria("Café")
    casal.pedir("flavio", "POST", "/api/favoritos", json=favorito(conta, [cafe]))

    lancar(
        casal, conta, [cafe], descricao="café da  padaria", valor_centavos=1350, data="2026-10-03"
    )
    lancar(
        casal, conta, [cafe], descricao="Café da padaria", valor_centavos=1500, data="2026-10-05"
    )
    lancar(
        casal, conta, [cafe], descricao="Café da padaria", valor_centavos=1100, data="2026-10-04"
    )
    # Outra conta ou outra descrição não é o mesmo lançamento.
    lancar(casal, casal.conta("Outra"), [cafe], descricao="Café da padaria", valor_centavos=999)
    lancar(casal, conta, [cafe], descricao="Padaria", valor_centavos=888, data="2026-10-06")
    lancar(casal, conta, [cafe], descricao="Café da padaria", valor_centavos=777, data="2026-10-01")

    [visto] = listar(casal)["favoritos"]
    assert visto["valor_padrao_centavos"] == 1500
    assert visto["valor_centavos"] == 1200


def test_o_lancamento_excluido_nao_conta_para_o_valor_padrao(casal: Casal):
    conta, cafe = casal.conta(), casal.categoria("Café")
    casal.pedir("flavio", "POST", "/api/favoritos", json=favorito(conta, [cafe]))
    lancar(
        casal, conta, [cafe], descricao="Café da padaria", valor_centavos=1000, data="2026-10-01"
    )
    errado = lancar(
        casal, conta, [cafe], descricao="Café da padaria", valor_centavos=9900, data="2026-10-02"
    )

    excluido = casal.pedir("flavio", "DELETE", f"/api/lancamentos/{errado['id']}")

    assert excluido.status_code == 204
    assert listar(casal)["favoritos"][0]["valor_padrao_centavos"] == 1000


def repetir(casal: Casal, vezes: int, conta: str, categorias: list[str], **campos) -> None:
    for dia in range(vezes):
        lancar(casal, conta, categorias, data=f"2026-09-{dia + 1:02d}", **campos)


def test_sugere_so_os_tres_mais_repetidos_com_cinco_usos_ou_mais(casal: Casal):
    conta, comida = casal.conta(), casal.categoria("Comida")
    repetir(casal, 4, conta, [comida], descricao="Quase lá", valor_centavos=100)
    repetir(casal, 5, conta, [comida], descricao="Padaria", valor_centavos=1000)
    repetir(casal, 8, conta, [comida], descricao="Mercado", valor_centavos=2000)
    repetir(casal, 6, conta, [comida], descricao="Feira", valor_centavos=3000)
    repetir(casal, 7, conta, [comida], descricao="Lanche", valor_centavos=4000)

    sugeridos = listar(casal)["sugeridos"]

    assert [(s["descricao"], s["usos"]) for s in sugeridos] == [
        ("Mercado", 8),
        ("Lanche", 7),
        ("Feira", 6),
    ]
    # Os campos são os de um favorito, com o último valor, para promover com um toque.
    assert sugeridos[0] | {"chave": None} == {
        "chave": None,
        "descricao": "Mercado",
        "tipo": "despesa",
        "conta_id": conta,
        "categoria_ids": [comida],
        "tags": [],
        "pessoa": None,
        "valor_centavos": 2000,
        "usos": 8,
    }


def test_quem_ja_e_favorito_nao_e_sugerido_e_promover_tira_da_lista(casal: Casal):
    conta, comida = casal.conta(), casal.categoria("Comida")
    repetir(casal, 6, conta, [comida], descricao="Mercado", valor_centavos=2000)
    repetir(casal, 5, conta, [comida], descricao="Padaria", valor_centavos=1000)
    [mercado, padaria] = listar(casal)["sugeridos"]

    promovido = casal.pedir(
        "flavio",
        "POST",
        "/api/favoritos",
        json=favorito(
            conta,
            [comida],
            descricao=mercado["descricao"],
            valor_centavos=mercado["valor_centavos"],
        ),
    )

    assert promovido.status_code == 201
    visto = listar(casal)
    assert [f["descricao"] for f in visto["favoritos"]] == ["Mercado"]
    assert [s["descricao"] for s in visto["sugeridos"]] == [padaria["descricao"]]


def test_dispensar_um_sugerido_o_tira_da_lista_para_os_dois_e_cabe_outro_no_lugar(casal: Casal):
    conta, comida = casal.conta(), casal.categoria("Comida")
    for descricao, vezes in [("A", 9), ("B", 8), ("C", 7), ("D", 6)]:
        repetir(casal, vezes, conta, [comida], descricao=descricao)
    [a, *_] = listar(casal)["sugeridos"]

    dispensado = casal.pedir(
        "flavio", "POST", "/api/favoritos/sugeridos/dispensar", json={"chave": a["chave"]}
    )

    assert dispensado.status_code == 204
    assert [s["descricao"] for s in listar(casal, "esposa")["sugeridos"]] == ["B", "C", "D"]


def test_reenviar_o_mesmo_favorito_nao_duplica_e_o_mesmo_lancamento_vale_um_favorito_so(
    casal: Casal,
):
    conta, cafe = casal.conta(), casal.categoria("Café")
    novo = favorito(conta, [cafe])

    primeiro = casal.pedir("flavio", "POST", "/api/favoritos", json=novo)
    de_novo = casal.pedir("flavio", "POST", "/api/favoritos", json=novo)
    do_outro = casal.pedir("esposa", "POST", "/api/favoritos", json=favorito(conta, [cafe]))

    assert [primeiro.status_code, de_novo.status_code, do_outro.status_code] == [201, 200, 200]
    assert do_outro.json()["id"] == novo["id"]
    assert len(listar(casal)["favoritos"]) == 1


def test_remover_o_favorito_tira_da_lista_e_nao_o_devolve_como_sugerido(casal: Casal):
    conta, comida = casal.conta(), casal.categoria("Comida")
    repetir(casal, 6, conta, [comida], descricao="Mercado")
    novo = favorito(conta, [comida], descricao="Mercado")
    casal.pedir("flavio", "POST", "/api/favoritos", json=novo)

    removido = casal.pedir("esposa", "DELETE", f"/api/favoritos/{novo['id']}")
    de_novo = casal.pedir("esposa", "DELETE", f"/api/favoritos/{novo['id']}")

    assert [removido.status_code, de_novo.status_code] == [204, 204]
    assert listar(casal) == {"favoritos": [], "sugeridos": []}


def test_favoritar_de_novo_o_que_foi_removido_ou_dispensado_o_traz_de_volta(casal: Casal):
    conta, comida = casal.conta(), casal.categoria("Comida")
    novo = favorito(conta, [comida], descricao="Mercado")
    casal.pedir("flavio", "POST", "/api/favoritos", json=novo)
    casal.pedir("flavio", "DELETE", f"/api/favoritos/{novo['id']}")

    de_novo = casal.pedir(
        "flavio", "POST", "/api/favoritos", json=favorito(conta, [comida], descricao="mercado")
    )

    assert de_novo.status_code == 201
    assert [f["descricao"] for f in listar(casal)["favoritos"]] == ["mercado"]


def test_reordenar_muda_a_ordem_para_os_dois_e_o_novo_entra_no_fim(casal: Casal):
    conta, comida = casal.conta(), casal.categoria("Comida")
    ids = []
    for descricao in ["A", "B", "C"]:
        novo = favorito(conta, [comida], descricao=descricao)
        casal.pedir("flavio", "POST", "/api/favoritos", json=novo)
        ids.append(novo["id"])

    reordenado = casal.pedir(
        "flavio", "PUT", "/api/favoritos/ordem", json={"ids": [ids[2], ids[0], ids[1]]}
    )

    assert reordenado.status_code == 200
    assert [f["descricao"] for f in reordenado.json()["favoritos"]] == ["C", "A", "B"]
    casal.pedir("esposa", "POST", "/api/favoritos", json=favorito(conta, [comida], descricao="D"))
    assert [f["descricao"] for f in listar(casal)["favoritos"]] == ["C", "A", "B", "D"]


def test_reordenar_exige_exatamente_os_favoritos_que_existem(casal: Casal):
    conta, comida = casal.conta(), casal.categoria("Comida")
    novo = favorito(conta, [comida])
    casal.pedir("flavio", "POST", "/api/favoritos", json=novo)

    faltando = casal.pedir("flavio", "PUT", "/api/favoritos/ordem", json={"ids": []})
    sobrando = casal.pedir(
        "flavio", "PUT", "/api/favoritos/ordem", json={"ids": [novo["id"], str(uuid4())]}
    )

    assert faltando.status_code == sobrando.status_code == 422


def test_recusa_favorito_com_conta_inexistente_categoria_de_outro_tipo_ou_valor_zero(
    casal: Casal,
):
    conta, comida = casal.conta(), casal.categoria("Comida")
    salario = casal.categoria("Salário", "receita")

    sem_conta = casal.pedir(
        "flavio", "POST", "/api/favoritos", json=favorito(str(uuid4()), [comida])
    )
    tipo_errado = casal.pedir("flavio", "POST", "/api/favoritos", json=favorito(conta, [salario]))
    sem_valor = casal.pedir(
        "flavio", "POST", "/api/favoritos", json=favorito(conta, [comida], valor_centavos=0)
    )

    assert sem_conta.status_code == tipo_errado.status_code == sem_valor.status_code == 422
    assert listar(casal)["favoritos"] == []


def test_quem_nao_entrou_nao_ve_nem_mexe_nos_favoritos(casal: Casal):
    assert casal.client.get("/api/favoritos").status_code == 401
