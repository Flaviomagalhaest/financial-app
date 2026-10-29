"""Índice de sugestão pelo histórico (ticket 22): os pacotes de categorias, tags, conta e pessoa
dos lançamentos do casal, que o aparelho casa com a descrição sem internet."""

import psycopg

from tests.conftest import Casal
from tests.test_lancamentos import lancamento


def lancar(casal: Casal, quem: str = "flavio", **campos) -> dict:
    resposta = casal.pedir(quem, "POST", "/api/lancamentos", json=lancamento(**campos))
    assert resposta.status_code == 201
    return resposta.json()


def indice(casal: Casal, quem: str = "esposa") -> list[dict]:
    resposta = casal.pedir(quem, "GET", "/api/sugestoes")
    assert resposta.status_code == 200
    return resposta.json()["pacotes"]


def test_o_indice_traz_o_pacote_do_lancamento_com_a_descricao_sem_acento_maiuscula_e_parcela(
    casal: Casal,
):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    lancar(
        casal,
        conta=conta,
        categorias=[mercado],
        descricao="  Pão de Açúcar  (2/10) ",
        tags=["Casa"],
        pessoa="flavio",
        acao_em="2026-10-12T17:32:00Z",
    )

    assert indice(casal) == [
        {
            "chave": "pao de acucar",
            "descricao": "  Pão de Açúcar  (2/10) ",
            "tipo": "despesa",
            "conta_id": conta,
            "categoria_ids": [mercado],
            "tags": ["Casa"],
            "pessoa": "flavio",
            "em": "2026-10-12T17:32:00Z",
            "origem": "historico",
        }
    ]


def test_por_descricao_ficam_os_pacotes_diferentes_do_mais_recente_ao_mais_antigo_ate_3(
    casal: Casal,
):
    conta = casal.conta()
    [a, b, c, d] = [casal.categoria(nome) for nome in ("Mercado", "Casa", "Lazer", "Saúde")]
    for dia, categorias, descricao in [
        ("01", [a], "Extra"),
        ("02", [b], "Extra"),
        ("03", [a], "EXTRA"),
        ("04", [c], "Extra"),
        ("05", [d], "Extra"),
        ("06", [d], "Extrá"),
    ]:
        lancar(
            casal,
            conta=conta,
            categorias=categorias,
            descricao=descricao,
            acao_em=f"2026-10-{dia}T12:00:00Z",
        )

    pacotes = indice(casal)

    # O pacote de Mercado repetido conta pela vez mais recente (dia 3), e o de Casa, o mais
    # antigo dos quatro, fica de fora: o aparelho nunca mostra mais de 3.
    assert [(p["categoria_ids"], p["descricao"], p["em"][:10]) for p in pacotes] == [
        ([d], "Extrá", "2026-10-06"),
        ([c], "Extra", "2026-10-04"),
        ([a], "EXTRA", "2026-10-03"),
    ]


def test_corrigir_as_categorias_torna_o_pacote_o_mais_recente_e_mudar_o_valor_nao(casal: Casal):
    conta, transporte, lazer = (
        casal.conta(),
        casal.categoria("Transporte"),
        casal.categoria("Lazer"),
    )
    corrida = lancar(
        casal, conta=conta, categorias=[lazer], descricao="Uber", acao_em="2026-10-01T12:00:00Z"
    )
    outra = lancar(
        casal, conta=conta, categorias=[lazer], descricao="Uber", acao_em="2026-10-02T12:00:00Z"
    )
    passeio = casal.categoria("Passeio")
    lancar(
        casal, conta=conta, categorias=[passeio], descricao="Uber", acao_em="2026-10-03T12:00:00Z"
    )

    corrigida = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/lancamentos/{corrida['id']}",
        json={"versao": 1, "categoria_ids": [transporte], "acao_em": "2026-10-04T12:00:00Z"},
    )
    so_o_valor = casal.pedir(
        "esposa",
        "PATCH",
        f"/api/lancamentos/{outra['id']}",
        json={"versao": 1, "valor_centavos": 999, "acao_em": "2026-10-05T12:00:00Z"},
    )

    assert corrigida.status_code == so_o_valor.status_code == 200
    assert [(p["categoria_ids"], p["em"][:10]) for p in indice(casal)] == [
        ([transporte], "2026-10-04"),
        ([passeio], "2026-10-03"),
        ([lazer], "2026-10-02"),
    ]


def test_ficam_de_fora_o_excluido_a_descricao_vazia_e_o_que_esta_arquivado(casal: Casal):
    conta, mercado, antiga = casal.conta(), casal.categoria("Mercado"), casal.categoria("Antiga")
    excluido = lancar(casal, conta=conta, categorias=[mercado], descricao="Feira")
    casal.pedir("flavio", "DELETE", f"/api/lancamentos/{excluido['id']}")
    lancar(casal, conta=conta, categorias=[mercado], descricao="   ")
    lancar(casal, conta=conta, categorias=[antiga], descricao="Só a antiga")
    lancar(
        casal,
        "esposa",
        conta=conta,
        categorias=[mercado, antiga],
        descricao="Padaria",
        tags=["velha", "nova"],
    )
    casal.pedir("flavio", "PATCH", f"/api/categorias/{antiga}", json={"arquivada": True})
    [velha] = [t for t in casal.pedir("flavio", "GET", "/api/tags").json() if t["nome"] == "velha"]
    casal.pedir("flavio", "PATCH", f"/api/tags/{velha['id']}", json={"arquivada": True})

    assert [(p["descricao"], p["categoria_ids"], p["tags"]) for p in indice(casal)] == [
        ("Padaria", [mercado], ["nova"]),
    ]


def test_o_historico_importado_do_mobills_e_o_da_outra_pessoa_entram(
    casal: Casal, database_url: str
):
    conta, mercado = casal.conta(), casal.categoria("Mercado")
    importado = lancar(casal, conta=conta, categorias=[mercado], descricao="Assaí")
    lancar(casal, "esposa", conta=conta, categorias=[mercado], descricao="Atacadão")
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("UPDATE lancamentos SET fonte = 'mobills' WHERE id = %s", (importado["id"],))

    assert sorted(p["chave"] for p in indice(casal, "flavio")) == ["assai", "atacadao"]
