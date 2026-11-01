"""Partes da compra à vista (ticket 137, ADR 0022): a compra que junta coisas diferentes se divide
em partes, cada uma com descrição, valor, categorias, tags, pessoa e item próprios."""

from uuid import uuid4

from tests.conftest import Casal
from tests.test_lancamentos import lancamento


def parte(categorias: list[str], valor: int, **campos) -> dict:
    return {
        "id": str(uuid4()),
        "descricao": "",
        "valor_centavos": valor,
        "categoria_ids": categorias,
    } | campos


def compra_com_partes(casal: Casal, conta: str, partes: list[dict], quem="flavio", **campos):
    return casal.pedir(
        quem,
        "POST",
        "/api/lancamentos",
        json=lancamento(
            conta,
            [],
            valor_centavos=sum(p["valor_centavos"] for p in partes),
            descricao="Mercado Livre",
            partes=partes,
        )
        | campos,
    )


def test_compra_com_tres_partes_guarda_cada_uma_com_a_classificacao_dela(casal: Casal):
    conta = casal.conta()
    roupa, eletronico, casa = (
        casal.categoria("Roupa"),
        casal.categoria("Eletrônico"),
        casal.categoria("Casa"),
    )
    partes = [
        parte([roupa], 50000, descricao="Vestido", pessoa="esposa", tags=["presente"]),
        parte([eletronico], 25000, descricao="Fone", pessoa="flavio"),
        parte([casa], 25000, descricao="Cortina"),
    ]

    criada = compra_com_partes(casal, conta, partes)

    assert criada.status_code == 201, criada.text
    [vista] = casal.pedir("esposa", "GET", "/api/lancamentos").json()
    assert vista["valor_centavos"] == 100000
    assert (vista["categoria_ids"], vista["tags"], vista["pessoa"]) == ([], [], None)
    assert [
        (p["id"], p["descricao"], p["valor_centavos"], p["categoria_ids"], p["tags"], p["pessoa"])
        for p in vista["partes"]
    ] == [
        (partes[0]["id"], "Vestido", 50000, [roupa], ["presente"], "esposa"),
        (partes[1]["id"], "Fone", 25000, [eletronico], [], "flavio"),
        (partes[2]["id"], "Cortina", 25000, [casa], [], None),
    ]


def test_criar_recusa_partes_que_nao_somam_o_valor_ou_que_sao_uma_so(casal: Casal):
    conta, roupa, casa = casal.conta(), casal.categoria("Roupa"), casal.categoria("Casa")
    duas = [parte([roupa], 600), parte([casa], 400)]

    nao_soma = compra_com_partes(casal, conta, duas, valor_centavos=1100)
    uma_so = compra_com_partes(casal, conta, [parte([roupa], 1000)])
    com_categoria = compra_com_partes(casal, conta, duas, categoria_ids=[roupa])
    com_pessoa = compra_com_partes(casal, conta, duas, pessoa="flavio")
    receita = compra_com_partes(
        casal,
        conta,
        [parte([casal.categoria("Salário", "receita")], 1000), parte([roupa], 1)],
        tipo="receita",
    )

    assert [r.status_code for r in (nao_soma, uma_so, com_categoria, com_pessoa, receita)] == [
        422
    ] * 5
    assert "somam 1000 centavos e a compra, 1100" in nao_soma.text
    assert "duas partes ou mais" in uma_so.text
    assert "não tem categoria, tag nem pessoa próprias" in com_categoria.text
    assert casal.pedir("flavio", "GET", "/api/lancamentos").json() == []


def test_parte_confere_as_categorias_e_a_pessoa_como_um_lancamento(casal: Casal):
    conta, roupa = casal.conta(), casal.categoria("Roupa")
    salario = casal.categoria("Salário", "receita")

    de_receita = compra_com_partes(casal, conta, [parte([roupa], 600), parte([salario], 400)])
    sem_pessoa = compra_com_partes(
        casal, conta, [parte([roupa], 600), parte([roupa], 400, pessoa="vizinho")]
    )

    assert (de_receita.status_code, de_receita.json()["detail"]) == (
        422,
        "categoria de receita num lançamento de despesa",
    )
    assert (sem_pessoa.status_code, sem_pessoa.json()["detail"]) == (422, "pessoa não encontrada")


def editar(casal: Casal, id: str, quem="flavio", **campos):
    return casal.pedir(quem, "PATCH", f"/api/lancamentos/{id}", json=campos)


def test_dividir_uma_compra_tira_a_classificacao_dela_e_tirar_a_penultima_a_devolve(casal: Casal):
    conta, roupa, casa = casal.conta(), casal.categoria("Roupa"), casal.categoria("Casa")
    compra = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(conta, [roupa], valor_centavos=1000, tags=["loja"], pessoa="esposa"),
    ).json()

    dividida = editar(
        casal,
        compra["id"],
        versao=1,
        partes=[parte([roupa], 600, pessoa="esposa"), parte([casa], 400, tags=["sala"])],
    )

    assert dividida.status_code == 200, dividida.text
    assert (
        dividida.json()["categoria_ids"],
        dividida.json()["tags"],
        dividida.json()["pessoa"],
    ) == (
        [],
        [],
        None,
    )
    assert [p["valor_centavos"] for p in dividida.json()["partes"]] == [600, 400]

    fica = dividida.json()["partes"][1]
    junta = editar(casal, compra["id"], versao=2, partes=[fica])

    assert junta.status_code == 200, junta.text
    assert junta.json()["partes"] == []
    assert (
        junta.json()["valor_centavos"],
        junta.json()["categoria_ids"],
        junta.json()["tags"],
        junta.json()["pessoa"],
    ) == (1000, [casa], ["sala"], None)


def test_compra_com_partes_recusa_classificacao_propria_e_valor_que_nao_bate(casal: Casal):
    conta, roupa, casa = casal.conta(), casal.categoria("Roupa"), casal.categoria("Casa")
    compra = compra_com_partes(casal, conta, [parte([roupa], 600), parte([casa], 400)]).json()

    categoria = editar(casal, compra["id"], versao=1, categoria_ids=[roupa])
    pessoa = editar(casal, compra["id"], versao=1, pessoa="flavio")
    valor = editar(casal, compra["id"], versao=1, valor_centavos=1200)
    sem_partes = editar(casal, compra["id"], versao=1, partes=[])
    valor_e_partes = editar(
        casal,
        compra["id"],
        versao=1,
        valor_centavos=1200,
        partes=[compra["partes"][0], compra["partes"][1] | {"valor_centavos": 600}],
    )

    assert [r.status_code for r in (categoria, pessoa, valor, sem_partes)] == [422] * 4
    assert (
        categoria.json()["detail"]
        == "a compra com partes não tem categoria, tag nem pessoa próprias"
    )
    assert valor.json()["detail"] == "as partes somam 1000 centavos e a compra, 1200"
    assert sem_partes.json()["detail"] == (
        "sem as partes, a compra volta a ter categoria: mande as categorias dela"
    )
    assert valor_e_partes.status_code == 200, valor_e_partes.text
    assert [p["valor_centavos"] for p in valor_e_partes.json()["partes"]] == [600, 600]


def test_partes_sao_um_campo_so_no_conflito(casal: Casal):
    conta, roupa, casa = casal.conta(), casal.categoria("Roupa"), casal.categoria("Casa")
    compra = compra_com_partes(casal, conta, [parte([roupa], 600), parte([casa], 400)]).json()
    [vestido, cortina] = compra["partes"]

    dela = editar(
        casal,
        compra["id"],
        "esposa",
        versao=1,
        partes=[vestido | {"descricao": "Vestido"}, cortina],
    )
    dele = editar(casal, compra["id"], versao=1, partes=[vestido, cortina | {"pessoa": "flavio"}])

    assert dela.status_code == 200
    assert dele.status_code == 409, dele.text
    assert [c["campo"] for c in dele.json()["campos"]] == ["partes"]
    assert dele.json()["lancamento"]["partes"][0]["descricao"] == "Vestido"


def test_dividir_conflita_com_a_categoria_que_o_outro_lado_mudou(casal: Casal):
    conta, roupa, casa = casal.conta(), casal.categoria("Roupa"), casal.categoria("Casa")
    compra = casal.pedir(
        "flavio", "POST", "/api/lancamentos", json=lancamento(conta, [roupa], valor_centavos=1000)
    ).json()

    assert editar(casal, compra["id"], "esposa", versao=1, categoria_ids=[casa]).status_code == 200
    dividida = editar(
        casal, compra["id"], versao=1, partes=[parte([roupa], 600), parte([casa], 400)]
    )

    assert dividida.status_code == 409, dividida.text
    assert [c["campo"] for c in dividida.json()["campos"]] == ["categoria_ids"]


def test_estorno_de_compra_com_partes_espera_o_estorno_de_uma_parte(casal: Casal):
    from tests.test_cartoes import novo_cartao

    cartao, roupa, casa = (
        novo_cartao(casal)["id"],
        casal.categoria("Roupa"),
        casal.categoria("Casa"),
    )
    compra = compra_com_partes(
        casal, cartao, [parte([roupa], 600), parte([casa], 400)], data="2026-03-28"
    ).json()

    estorno = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(cartao, [roupa], valor_centavos=100, estorno_de=compra["id"]),
    )

    assert (estorno.status_code, estorno.json()["detail"]) == (
        422,
        "o estorno de uma parte da compra ainda não existe",
    )


def test_parcela_ainda_nao_se_divide_em_partes(casal: Casal):
    from tests.test_parcelamentos import parcelamento, parcelas

    conta, roupa, casa = casal.conta(), casal.categoria("Roupa"), casal.categoria("Casa")
    novo = parcelamento(conta, [roupa], parcelas=2, data="2099-01-10")
    assert casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo).status_code == 201
    [primeira, _] = parcelas(casal, novo["id"])

    dividida = editar(
        casal,
        primeira["id"],
        versao=primeira["versao"],
        partes=[parte([roupa], 1), parte([casa], primeira["valor_centavos"] - 1)],
    )

    assert (dividida.status_code, dividida.json()["detail"]) == (
        422,
        "por enquanto, só a compra à vista tem partes",
    )


def test_tag_e_categoria_de_uma_parte_contam_como_usadas_ate_a_compra_sair(casal: Casal):
    conta, roupa, casa = casal.conta(), casal.categoria("Roupa"), casal.categoria("Casa")
    compra = compra_com_partes(
        casal, conta, [parte([roupa], 600, tags=["loja"]), parte([casa], 400)]
    ).json()
    [loja] = [t for t in casal.pedir("flavio", "GET", "/api/tags").json() if t["nome"] == "loja"]

    assert casal.pedir("flavio", "DELETE", f"/api/tags/{loja['id']}").status_code == 409
    assert casal.pedir("flavio", "DELETE", f"/api/categorias/{casa}").status_code == 409

    assert casal.pedir("flavio", "DELETE", f"/api/lancamentos/{compra['id']}").status_code == 204

    assert casal.pedir("flavio", "DELETE", f"/api/tags/{loja['id']}").status_code == 204
    assert casal.pedir("flavio", "DELETE", f"/api/categorias/{casa}").status_code == 204


def test_juntar_categorias_e_tags_leva_as_das_partes(casal: Casal):
    conta, roupa, casa = casal.conta(), casal.categoria("Roupa"), casal.categoria("Casa")
    vestuario = casal.categoria("Vestuário")
    compra = compra_com_partes(
        casal, conta, [parte([roupa], 600, tags=["loja"]), parte([casa], 400)]
    ).json()
    tags = {t["nome"]: t["id"] for t in casal.pedir("flavio", "GET", "/api/tags").json()}
    casal.pedir(
        "flavio", "POST", "/api/lancamentos", json=lancamento(conta, [casa], tags=["shopping"])
    )
    tags = {t["nome"]: t["id"] for t in casal.pedir("flavio", "GET", "/api/tags").json()}

    juntou = casal.pedir(
        "flavio", "POST", f"/api/categorias/{roupa}/juntar", json={"destino_id": vestuario}
    )
    juntou_tag = casal.pedir(
        "flavio", "POST", f"/api/tags/{tags['loja']}/juntar", json={"destino_id": tags["shopping"]}
    )

    assert (juntou.status_code, juntou_tag.status_code) == (200, 200), (
        juntou.text,
        juntou_tag.text,
    )
    [vista] = [
        l
        for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()
        if l["id"] == compra["id"]
    ]
    assert vista["partes"][0]["categoria_ids"] == [vestuario]
    assert vista["partes"][0]["tags"] == ["shopping"]


def _mercado_livre(casal: Casal, conta: str, **campos) -> tuple[dict, dict[str, str]]:
    """O exemplo da ADR 0022: R$ 500 de roupa da esposa, R$ 250 de fone do Flávio e R$ 250 de
    cortina do casal, numa compra só."""
    c = {nome: casal.categoria(nome) for nome in ("Roupa", "Eletrônico", "Casa")}
    compra = compra_com_partes(
        casal,
        conta,
        [
            parte([c["Roupa"]], 50000, descricao="Vestido", pessoa="esposa", tags=["presente"]),
            parte([c["Eletrônico"]], 25000, descricao="Fone", pessoa="flavio", tags=["presente"]),
            parte([c["Casa"]], 25000, descricao="Cortina", tags=["sala"]),
        ],
        **campos,
    )
    assert compra.status_code == 201, compra.text
    return compra.json(), c


def test_categoria_tag_e_pessoa_somam_as_partes_e_o_mes_soma_a_compra(casal: Casal):
    compra, c = _mercado_livre(casal, casal.conta(), data="2026-10-02")

    totais = casal.pedir("flavio", "GET", "/api/meses/2026-10/totais").json()
    ranking = casal.pedir("flavio", "GET", "/api/meses/2026-10").json()["ranking"]

    assert totais["despesas_centavos"] == 100000
    assert {t["categoria_id"]: t["centavos"] for t in totais["por_categoria"]} == {
        c["Roupa"]: 50000,
        c["Eletrônico"]: 25000,
        c["Casa"]: 25000,
    }
    assert {t["tag"]: t["centavos"] for t in totais["por_tag"]} == {
        "presente": 75000,
        "sala": 25000,
    }
    pessoas = {
        l["chave"]: (l["centavos"], l["lancamento_ids"], len(l["parte_ids"]))
        for l in ranking["por_pessoa"]
    }
    assert pessoas == {
        "esposa": (50000, [compra["id"]], 1),
        "flavio": (25000, [compra["id"]], 1),
        None: (25000, [compra["id"]], 1),
    }
    [presente] = [l for l in ranking["por_tag"] if l["chave"] == "presente"]
    assert (presente["centavos"], presente["lancamento_ids"]) == (75000, [compra["id"]])
    assert presente["parte_ids"] == [p["id"] for p in compra["partes"][:2]]


def test_historico_da_categoria_soma_so_a_parte(casal: Casal):
    _, c = _mercado_livre(casal, casal.conta(), data="2026-10-02")

    historico = casal.pedir(
        "flavio",
        "GET",
        "/api/historico",
        params={"metrica": "categoria", "categoria_id": c["Casa"]},
    ).json()

    assert {m["mes"]: m["centavos"] for m in historico["doze_meses"]}["2026-10"] == 25000


def test_item_do_planejamento_conta_a_parte_e_a_fatura_e_o_saldo_contam_a_compra(casal: Casal):
    from tests.test_cartoes import novo_cartao
    from tests.test_estorno_e_ajuste import fatura

    cartao = novo_cartao(casal)["id"]
    conta = casal.conta()
    roupa = casal.categoria("Roupa")
    for mes in ("2026-04",):
        casal.pedir(
            "flavio",
            "POST",
            f"/api/planejamento/{mes}/itens",
            json={"id": str(uuid4()), "categoria_id": roupa, "valor_centavos": 80000},
        )
    casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(cartao, [casal.categoria("Casa")], valor_centavos=3000, data="2026-03-28"),
    )
    compra_com_partes(
        casal,
        cartao,
        [parte([roupa], 50000), parte([casal.categoria("Fone")], 25000)],
        data="2026-03-28",
    )
    compra_com_partes(
        casal, conta, [parte([roupa], 100), parte([casal.categoria("Pão")], 900)], data="2026-04-03"
    )

    [item] = casal.pedir("flavio", "GET", "/api/planejamento/2026-04").json()["itens"]
    [saldo] = [s["saldo_centavos"] for s in casal.pedir("flavio", "GET", "/api/contas").json()]

    assert item["realizado_centavos"] == 50100
    assert fatura(casal, cartao, "2026-04-01")["total_centavos"] == 78000
    assert saldo == -1000


def test_parte_com_duas_categorias_com_item_fica_a_escolher_e_a_escolha_e_da_parte(casal: Casal):
    conta = casal.conta()
    roupa, presente, casa = (
        casal.categoria("Roupa"),
        casal.categoria("Presentes"),
        casal.categoria("Casa"),
    )
    for categoria in (roupa, presente, casa):
        casal.pedir(
            "flavio",
            "POST",
            "/api/planejamento/2026-10/itens",
            json={"id": str(uuid4()), "categoria_id": categoria, "valor_centavos": 80000},
        )
    compra = compra_com_partes(
        casal, conta, [parte([roupa, presente], 600), parte([casa], 400)], data="2026-10-02"
    ).json()

    plano = casal.pedir("flavio", "GET", "/api/planejamento/2026-10").json()
    assert [(a["lancamento_id"], a["parte_id"]) for a in plano["a_escolher"]] == [
        (compra["id"], compra["partes"][0]["id"])
    ]
    assert {i["categoria_id"]: i["realizado_centavos"] for i in plano["itens"]} == {
        roupa: 0,
        presente: 0,
        casa: 400,
    }

    [vestido, cortina] = compra["partes"]
    escolhida = editar(
        casal, compra["id"], versao=1, partes=[vestido | {"item_categoria_id": presente}, cortina]
    )
    assert escolhida.status_code == 200, escolhida.text

    plano = casal.pedir("flavio", "GET", "/api/planejamento/2026-10").json()
    assert plano["a_escolher"] == []
    assert {i["categoria_id"]: i["realizado_centavos"] for i in plano["itens"]} == {
        roupa: 0,
        presente: 600,
        casa: 400,
    }


def buscar(casal: Casal, **criterios) -> dict:
    resposta = casal.pedir("esposa", "POST", "/api/busca", json=criterios)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_busca_por_categoria_tag_ou_pessoa_acha_so_a_parte_que_bate_com_o_valor_dela(casal: Casal):
    compra, c = _mercado_livre(casal, casal.conta(), data="2026-10-02")
    [vestido, fone, cortina] = [p["id"] for p in compra["partes"]]

    sem_filtro = buscar(casal)
    da_casa = buscar(casal, categoria_ids=[c["Casa"]])
    presentes = buscar(casal, tags=["presente"])
    da_esposa = buscar(casal, pessoas=["esposa"])
    do_conjunto = buscar(casal, conjunto=True)
    presente_dele = buscar(casal, tags=["presente"], pessoas=["flavio"])
    ninguem = buscar(casal, tags=["sala"], pessoas=["flavio"])
    pelo_valor = buscar(casal, categoria_ids=[c["Casa"]], valor_minimo_centavos=30000)

    assert [l["lancamento"]["id"] for l in sem_filtro["linhas"]] == [compra["id"]]
    assert sem_filtro["linhas"][0]["partes_achadas"] is None
    assert sem_filtro["totais"]["despesas"]["realizado_centavos"] == 100000
    for resultado, achadas, centavos in (
        (da_casa, [cortina], 25000),
        (presentes, [vestido, fone], 75000),
        (da_esposa, [vestido], 50000),
        (do_conjunto, [cortina], 25000),
        (presente_dele, [fone], 25000),
    ):
        [linha] = resultado["linhas"]
        assert (linha["lancamento"]["id"], linha["partes_achadas"]) == (compra["id"], achadas)
        assert resultado["totais"]["despesas"]["realizado_centavos"] == centavos
    assert ninguem["linhas"] == pelo_valor["linhas"] == []


def test_busca_pelo_texto_acha_a_compra_pela_descricao_de_uma_parte(casal: Casal):
    compra, _ = _mercado_livre(casal, casal.conta(), data="2026-10-02")

    [linha] = buscar(casal, texto="cortina")["linhas"]

    assert linha["lancamento"]["id"] == compra["id"]


def test_edicao_em_lote_deixa_de_fora_a_compra_com_partes(casal: Casal):
    from tests.test_edicao_em_lote import aplicada, previa

    conta, roupa, casa = casal.conta(), casal.categoria("Roupa"), casal.categoria("Casa")
    compra = compra_com_partes(casal, conta, [parte([roupa], 600), parte([casa], 400)]).json()
    avulso = casal.pedir(
        "flavio", "POST", "/api/lancamentos", json=lancamento(conta, [roupa])
    ).json()
    selecao = {"lancamento_ids": [compra["id"], avulso["id"]]}
    mudanca = {"categorias": {"acao": "acrescentar", "categoria_ids": [casa]}}

    vista = previa(casal, selecao, **mudanca)
    aplicada(casal, selecao, **mudanca)

    assert (vista["mudam"], vista["com_partes_fora"]) == (1, 1)
    [depois] = [
        l
        for l in casal.pedir("flavio", "GET", "/api/lancamentos").json()
        if l["id"] == compra["id"]
    ]
    assert depois["categoria_ids"] == [] and depois["versao"] == 1


def test_sugestao_leva_a_compra_com_partes_e_o_favorito_a_conta_pelas_partes(casal: Casal):
    conta, roupa, casa = casal.conta(), casal.categoria("Roupa"), casal.categoria("Casa")
    for dia in range(1, 6):
        compra_com_partes(
            casal, conta, [parte([roupa], 600), parte([casa], 400)], data=f"2026-10-0{dia}"
        )

    sugestoes = casal.pedir("flavio", "GET", "/api/sugestoes").json()["sugestoes"]
    favoritos = casal.pedir("flavio", "GET", "/api/favoritos").json()

    [sugestao] = sugestoes
    assert [(p["valor_centavos"], p["categoria_ids"]) for p in sugestao["partes"]] == [
        (600, [roupa]),
        (400, [casa]),
    ]
    [sugerido] = favoritos["sugeridos"]
    assert sugerido["usos"] == 5 and len(sugerido["partes"]) == 2


def test_juntar_as_partes_com_a_classificacao_que_o_pedido_traz(casal: Casal):
    conta, roupa, casa = casal.conta(), casal.categoria("Roupa"), casal.categoria("Casa")
    compra = compra_com_partes(casal, conta, [parte([roupa], 600), parte([casa], 400)]).json()

    junta = editar(casal, compra["id"], versao=1, partes=[], categoria_ids=[casa], pessoa="esposa")

    assert junta.status_code == 200, junta.text
    assert (junta.json()["partes"], junta.json()["categoria_ids"], junta.json()["pessoa"]) == (
        [],
        [casa],
        "esposa",
    )


def test_dividir_como_a_tela_manda_com_a_classificacao_vazia(casal: Casal):
    # A tela manda os campos que mudaram desde a base: as partes e a classificação esvaziada.
    conta, roupa, casa = casal.conta(), casal.categoria("Roupa"), casal.categoria("Casa")
    compra = casal.pedir(
        "flavio",
        "POST",
        "/api/lancamentos",
        json=lancamento(conta, [roupa], valor_centavos=1000, tags=["loja"], pessoa="esposa"),
    ).json()

    dividida = editar(
        casal,
        compra["id"],
        versao=1,
        categoria_ids=[],
        tags=[],
        pessoa="",
        partes=[parte([roupa], 600), parte([casa], 400)],
    )
    sem_nada = editar(casal, compra["id"], versao=2, partes=[], categoria_ids=[])

    assert dividida.status_code == 200, dividida.text
    assert len(dividida.json()["partes"]) == 2
    assert sem_nada.status_code == 422
