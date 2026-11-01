"""Partes na compra parcelada (ticket 139, ADR 0022): o parcelamento guarda as partes como
proporção, cada parcela se divide por elas (os centavos vão para a maior parte, a primeira no
empate), e o que vale é o valor da parcela."""

from datetime import date
from uuid import uuid4

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_alcance_da_mudanca_na_parcela import editar_so_nela, mudar_parcela
from tests.test_parcelamentos import parcelas
from tests.test_partes_da_compra import parte

HOJE = date(2026, 10, 28)


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hoje é 28/10/2026 em São Paulo."""
    monkeypatch.setattr(lancamentos, "hoje", lambda: HOJE)


@pytest.fixture
def categorias(casal: Casal) -> tuple[str, str, str]:
    return casal.categoria("Roupa"), casal.categoria("Eletrônico"), casal.categoria("Casa")


def parcelado(casal: Casal, conta: str, partes: list[dict], quem="flavio", **campos):
    return casal.pedir(
        quem,
        "POST",
        "/api/parcelamentos",
        json={
            "id": str(uuid4()),
            "valor_total_centavos": sum(p["valor_centavos"] for p in partes),
            "parcelas": 3,
            "descricao": "Mercado Livre",
            "conta_id": conta,
            "categoria_ids": [],
            "data": "2026-11-10",
            "partes": partes,
        }
        | campos,
    )


def tres_partes(categorias) -> list[dict]:
    roupa, eletronico, casa = categorias
    return [
        parte([roupa], 50000, descricao="Vestido", pessoa="esposa", tags=["presente"]),
        parte([eletronico], 25000, descricao="Fone", pessoa="flavio"),
        parte([casa], 25000, descricao="Cortina"),
    ]


def divisao(parcela: dict) -> list[int]:
    return [p["valor_centavos"] for p in parcela["partes"]]


def regra(casal: Casal, id: str) -> dict:
    [achada] = [
        p for p in casal.pedir("flavio", "GET", "/api/parcelamentos").json() if p["id"] == id
    ]
    return achada


def test_cada_parcela_se_divide_pelas_partes_com_os_centavos_na_maior(casal: Casal, categorias):
    roupa, eletronico, casa = categorias
    partes = tres_partes(categorias)

    criado = parcelado(casal, casal.conta(), partes)

    assert criado.status_code == 201, criado.text
    assert (criado.json()["categoria_ids"], criado.json()["tags"], criado.json()["pessoa"]) == (
        [],
        [],
        None,
    )
    assert [(p["id"], p["valor_centavos"]) for p in criado.json()["partes"]] == [
        (partes[0]["id"], 50000),
        (partes[1]["id"], 25000),
        (partes[2]["id"], 25000),
    ]
    geradas = parcelas(casal, criado.json()["id"])
    # 1.000,00 em 3: 333,34 na 1ª e 333,33 nas outras; metade, um quarto e um quarto de cada,
    # e o centavo do arredondamento vai para o vestido, a maior parte.
    assert [(l["valor_centavos"], divisao(l)) for l in geradas] == [
        (33334, [16668, 8333, 8333]),
        (33333, [16667, 8333, 8333]),
        (33333, [16667, 8333, 8333]),
    ]
    [primeira, *_] = geradas
    assert (primeira["categoria_ids"], primeira["tags"], primeira["pessoa"]) == ([], [], None)
    assert [
        (p["descricao"], p["categoria_ids"], p["tags"], p["pessoa"]) for p in primeira["partes"]
    ] == [
        ("Vestido", [roupa], ["presente"], "esposa"),
        ("Fone", [eletronico], [], "flavio"),
        ("Cortina", [casa], [], None),
    ]
    # Cada parcela tem as partes dela, com ids próprios.
    assert len({p["id"] for l in geradas for p in l["partes"]}) == 9


def test_no_empate_os_centavos_vao_para_a_primeira_parte(casal: Casal, categorias):
    roupa, casa, _ = categorias

    criado = parcelado(
        casal,
        casal.conta(),
        [parte([roupa], 1001), parte([casa], 1001)],
        parcelas=2,
    )

    assert criado.status_code == 201, criado.text
    assert [divisao(l) for l in parcelas(casal, criado.json()["id"])] == [[501, 500], [501, 500]]


def test_com_o_valor_da_parcela_as_partes_dividem_a_parcela(casal: Casal, categorias):
    roupa, casa, _ = categorias

    criado = parcelado(
        casal,
        casal.conta(),
        [parte([roupa], 6000), parte([casa], 4000)],
        valor_total_centavos=None,
        valor_da_parcela_centavos=10000,
    )

    assert criado.status_code == 201, criado.text
    assert criado.json()["valor_total_centavos"] == 30000
    assert [divisao(l) for l in parcelas(casal, criado.json()["id"])] == [[6000, 4000]] * 3


def test_criar_recusa_partes_que_nao_somam_o_valor_ou_com_classificacao_propria(
    casal: Casal, categorias
):
    roupa, casa, _ = categorias
    conta = casal.conta()
    duas = [parte([roupa], 600), parte([casa], 400)]

    nao_soma = parcelado(casal, conta, duas, valor_total_centavos=1100)
    com_categoria = parcelado(casal, conta, duas, categoria_ids=[roupa])
    uma_so = parcelado(casal, conta, [parte([roupa], 1000)])
    # 2 centavos em 2 parcelas: a parte de 1% não chega a um centavo.
    sem_centavo = parcelado(casal, conta, [parte([roupa], 99), parte([casa], 1)], parcelas=50)

    assert [r.status_code for r in (nao_soma, com_categoria, uma_so, sem_centavo)] == [422] * 4
    assert "somam 1000 centavos e a compra, 1100" in nao_soma.text
    assert "não tem categoria, tag nem pessoa próprias" in com_categoria.text
    assert "duas partes ou mais" in uma_so.text
    assert "não chega a um centavo por parte" in sem_centavo.text
    assert casal.pedir("flavio", "GET", "/api/parcelamentos").json() == []


def test_as_somas_por_categoria_leem_as_partes_da_parcela(casal: Casal, categorias):
    roupa, eletronico, casa = categorias
    # A 1ª parcela, de hoje, nasce realizada em outubro.
    criado = parcelado(casal, casal.conta(), tres_partes(categorias), data="2026-10-28")
    assert criado.status_code == 201

    totais = casal.pedir("flavio", "GET", "/api/meses/2026-10/totais").json()

    assert totais["despesas_centavos"] == 33334
    assert {t["categoria_id"]: t["centavos"] for t in totais["por_categoria"]} == {
        roupa: 16668,
        eletronico: 8333,
        casa: 8333,
    }


def campos_a_mao(database_url: str, id: str) -> set[str]:
    import psycopg

    with psycopg.connect(database_url) as conn:
        return {
            c
            for (c,) in conn.execute(
                "SELECT campo FROM lancamento_campos WHERE lancamento_id = %s AND origem IS NULL",
                (id,),
            )
        }


def test_parcela_com_valor_editado_a_mao_se_redivide_na_mesma_proporcao(
    casal: Casal, categorias, database_url
):
    criado = parcelado(casal, casal.conta(), tres_partes(categorias)).json()
    [_, segunda, _] = parcelas(casal, criado["id"])

    # Sem as partes no pedido, ou com elas só divididas pelo valor novo, como a tela manda.
    editada = editar_so_nela(casal, segunda, valor_centavos=40001)
    redividida = [
        p | {"valor_centavos": v} for p, v in zip(editada["partes"], [20000, 10000, 10000])
    ]
    de_novo = editar_so_nela(casal, editada, valor_centavos=40000, partes=redividida)

    assert divisao(editada) == [20001, 10000, 10000]
    assert divisao(de_novo) == [20000, 10000, 10000]
    # Só o valor ficou alterado à mão: as partes seguem as do parcelamento.
    assert de_novo["alterada_a_mao"]
    assert campos_a_mao(database_url, segunda["id"]) == {"valor_centavos"}
    assert [p["id"] for p in de_novo["partes"]] == [p["id"] for p in segunda["partes"]]

    # A mudança das partes em "todas" chega a ela, na proporção nova e com o valor dela.
    roupa, eletronico, _ = categorias
    [primeira, *_] = parcelas(casal, criado["id"])
    novas = [
        parte([roupa], primeira["valor_centavos"] // 2, descricao="Vestido"),
        parte([eletronico], primeira["valor_centavos"] - primeira["valor_centavos"] // 2),
    ]
    resposta = mudar_parcela(casal, primeira, "todas", partes=novas)

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["parcelas_mantidas"] == 0
    assert [divisao(l) for l in parcelas(casal, criado["id"])] == [
        [16667, 16667],
        [20000, 20000],
        [16667, 16666],
    ]


def test_so_esta_da_partes_proprias_a_parcela_e_as_outras_mudancas_a_preservam(
    casal: Casal, categorias, database_url
):
    roupa, eletronico, casa = categorias
    criado = parcelado(casal, casal.conta(), tres_partes(categorias)).json()
    [_, segunda, terceira] = parcelas(casal, criado["id"])
    so_nela = [parte([casa], 23333, descricao="Só cortina"), parte([roupa], 10000)]

    propria = editar_so_nela(casal, terceira, partes=so_nela)

    assert propria["alterada_a_mao"]
    assert campos_a_mao(database_url, terceira["id"]) == {"partes"}
    assert [(p["descricao"], p["valor_centavos"]) for p in propria["partes"]] == [
        ("Só cortina", 23333),
        ("", 10000),
    ]

    novas = [parte([eletronico], 16667), parte([roupa], 16666)]
    proximas = mudar_parcela(casal, segunda, "esta_e_as_proximas", partes=novas)

    assert proximas.status_code == 200, proximas.text
    assert proximas.json()["parcelas_mantidas"] == 1
    depois = parcelas(casal, criado["id"])
    assert [divisao(l) for l in depois] == [[16668, 8333, 8333], [16667, 16666], [23333, 10000]]
    assert [p["categoria_ids"] for p in depois[1]["partes"]] == [[eletronico], [roupa]]
    assert [p["valor_centavos"] for p in regra(casal, criado["id"])["partes"]] == [16667, 16666]

    # A correção do valor redivide cada parcela: as que seguem o parcelamento pela proporção dele, a
    # que tem partes próprias pela dela, e a 1ª, de antes de "esta e as próximas", pela que tinha.
    corrigido = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/parcelamentos/{criado['id']}",
        json={"valor_da_parcela_centavos": 20000},
    )

    assert corrigido.status_code == 200, corrigido.text
    assert corrigido.json()["parcelas_mantidas"] == 0
    assert [(l["valor_centavos"], divisao(l)) for l in parcelas(casal, criado["id"])] == [
        (20000, [10000, 5000, 5000]),
        (20000, [10001, 9999]),
        (20000, [14000, 6000]),
    ]


def test_todas_divide_o_parcelamento_e_uma_parte_so_o_junta_de_novo(casal: Casal, categorias):
    roupa, eletronico, _ = categorias
    novo = {
        "id": str(uuid4()),
        "valor_total_centavos": 30000,
        "parcelas": 3,
        "descricao": "Mercado Livre",
        "conta_id": casal.conta(),
        "categoria_ids": [roupa],
        "tags": ["loja"],
        "pessoa": "esposa",
        "data": "2026-11-10",
    }
    assert casal.pedir("flavio", "POST", "/api/parcelamentos", json=novo).status_code == 201
    [_, segunda, _] = parcelas(casal, novo["id"])

    dividida = mudar_parcela(
        casal,
        segunda,
        "todas",
        partes=[parte([roupa], 7000, pessoa="esposa"), parte([eletronico], 3000)],
    )

    assert dividida.status_code == 200, dividida.text
    gravada = regra(casal, novo["id"])
    assert (gravada["categoria_ids"], gravada["tags"], gravada["pessoa"]) == ([], [], None)
    assert [divisao(l) for l in parcelas(casal, novo["id"])] == [[7000, 3000]] * 3
    assert {(tuple(l["categoria_ids"]), tuple(l["tags"])) for l in parcelas(casal, novo["id"])} == {
        ((), ())
    }

    segunda = parcelas(casal, novo["id"])[1]
    fica = segunda["partes"][1]
    junta = mudar_parcela(casal, segunda, "todas", partes=[fica])

    assert junta.status_code == 200, junta.text
    gravada = regra(casal, novo["id"])
    assert (gravada["partes"], gravada["categoria_ids"]) == ([], [eletronico])
    assert [(l["partes"], l["categoria_ids"]) for l in parcelas(casal, novo["id"])] == [
        ([], [eletronico])
    ] * 3


def test_correcao_do_parcelamento_redivide_as_parcelas_pelas_partes(casal: Casal, categorias):
    criado = parcelado(casal, casal.conta(), tres_partes(categorias)).json()

    corrigido = casal.pedir(
        "flavio",
        "PATCH",
        f"/api/parcelamentos/{criado['id']}",
        json={"valor_total_centavos": 40000, "parcelas": 4},
    )

    assert corrigido.status_code == 200, corrigido.text
    assert [(l["valor_centavos"], divisao(l)) for l in parcelas(casal, criado["id"])] == [
        (10000, [5000, 2500, 2500])
    ] * 4
    # A parcela nova também nasce dividida.
    assert [p["valor_centavos"] for p in corrigido.json()["partes"]] == [50000, 25000, 25000]


def test_correcao_recusa_categoria_propria_no_parcelamento_com_partes(casal: Casal, categorias):
    roupa, _, _ = categorias
    criado = parcelado(casal, casal.conta(), tres_partes(categorias)).json()

    resposta = casal.pedir(
        "flavio", "PATCH", f"/api/parcelamentos/{criado['id']}", json={"categoria_ids": [roupa]}
    )

    assert resposta.status_code == 422
    assert "não tem categoria, tag nem pessoa próprias" in resposta.text


def test_confirmar_a_parcela_com_outro_valor_a_redivide(casal: Casal, categorias):
    roupa, casa, _ = categorias
    criado = parcelado(
        casal, casal.conta(), [parte([roupa], 6000), parte([casa], 4000)], data="2026-11-10"
    ).json()
    [primeira, *_] = parcelas(casal, criado["id"])

    confirmada = casal.pedir(
        "flavio",
        "POST",
        f"/api/lancamentos/{primeira['id']}/confirmar",
        json={"versao": primeira["versao"], "valor_centavos": 5000},
    )

    assert confirmada.status_code == 200, confirmada.text
    assert divisao(confirmada.json()) == [3000, 2000]


def test_exclusao_do_parcelamento_tira_as_partes_dele(casal: Casal, categorias, database_url):
    import psycopg

    criado = parcelado(casal, casal.conta(), tres_partes(categorias)).json()

    excluido = casal.pedir("flavio", "DELETE", f"/api/parcelamentos/{criado['id']}")

    assert excluido.status_code == 204
    with psycopg.connect(database_url) as conn:
        assert conn.execute(
            "SELECT count(*) FROM parcelamento_partes WHERE parcelamento_id = %s", (criado["id"],)
        ).fetchone() == (0,)


def test_antecipar_as_ultimas_parcelas_as_redivide_pelo_valor_pago(casal: Casal, categorias):
    roupa, casa, _ = categorias
    criado = parcelado(casal, casal.conta(), [parte([roupa], 6000), parte([casa], 4000)]).json()

    resposta = casal.pedir(
        "flavio",
        "POST",
        f"/api/parcelamentos/{criado['id']}/antecipacoes",
        json={"parcelas": 2, "valor_total_centavos": 5000},
    )

    assert resposta.status_code == 200, resposta.text
    assert [(l["valor_centavos"], divisao(l)) for l in resposta.json()] == [
        (2500, [1500, 1000]),
        (2500, [1500, 1000]),
    ]


def test_edicao_em_lote_deixa_de_fora_as_parcelas_do_parcelamento_com_partes(
    casal: Casal, categorias
):
    from tests.test_edicao_em_lote import aplicar, previa

    roupa, _, casa = categorias
    criado = parcelado(casal, casal.conta(), tres_partes(categorias)).json()
    [primeira, segunda, _] = parcelas(casal, criado["id"])
    # A 1ª, juntada só nela, não tem partes, mas o parcelamento dela tem.
    editar_so_nela(casal, primeira, partes=[], categoria_ids=[roupa])
    selecao = {"lancamento_ids": [primeira["id"], segunda["id"]]}
    mudanca = {"categorias": {"acao": "acrescentar", "categoria_ids": [casa]}}

    vista = previa(casal, selecao, **mudanca)
    recusada = aplicar(casal, selecao, **mudanca)

    # A parcela selecionada leva o parcelamento inteiro: as três ficam de fora.
    assert (vista["mudam"], vista["com_partes_fora"]) == (0, 3)
    assert recusada.status_code == 422
    assert regra(casal, criado["id"])["categoria_ids"] == []
    assert parcelas(casal, criado["id"])[0]["categoria_ids"] == [roupa]
