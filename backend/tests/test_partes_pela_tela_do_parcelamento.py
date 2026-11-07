"""Mudar as partes pela tela do parcelamento (ticket 158, ADR 0022): o `PATCH` do parcelamento
divide, muda e junta as partes de todas as parcelas, inclusive as realizadas, e preserva a que
tem partes próprias; a leitura traz as partes divididas pelo total, somando o valor dele."""

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_alcance_da_mudanca_na_parcela import editar_so_nela
from tests.test_parcelamentos import parcelas
from tests.test_partes_da_compra import parte
from tests.test_partes_na_compra_parcelada import HOJE, divisao, parcelado, regra, tres_partes


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lancamentos, "hoje", lambda: HOJE)


@pytest.fixture
def categorias(casal: Casal) -> tuple[str, str, str]:
    return casal.categoria("Roupa"), casal.categoria("Eletrônico"), casal.categoria("Casa")


def mudar_partes(casal: Casal, id: str, partes: list[dict], **campos):
    return casal.pedir(
        "flavio", "PATCH", f"/api/parcelamentos/{id}", json={"partes": partes} | campos
    )


def test_a_leitura_traz_as_partes_divididas_pelo_total(casal: Casal, categorias):
    roupa, eletronico, _ = categorias
    # 3 x 100,00 dividido em 2/3 e 1/3: a proporção guardada vem de uma parcela.
    criado = parcelado(
        casal,
        casal.conta(),
        [parte([roupa], 6667), parte([eletronico], 3333)],
        valor_total_centavos=None,
        valor_da_parcela_centavos=10000,
    )

    assert criado.status_code == 201, criado.text
    assert divisao(criado.json()) == [20001, 9999]
    assert divisao(regra(casal, criado.json()["id"])) == [20001, 9999]


def test_mudar_as_partes_vale_para_todas_e_preserva_as_partes_proprias(casal: Casal, categorias):
    roupa, eletronico, casa = categorias
    criado = parcelado(casal, casal.conta(), [parte([roupa], 20000), parte([casa], 10000)]).json()
    [primeira, _, terceira] = parcelas(casal, criado["id"])
    confirmada = casal.pedir(
        "flavio",
        "POST",
        f"/api/lancamentos/{primeira['id']}/confirmar",
        json={"versao": primeira["versao"]},
    )
    assert confirmada.status_code == 200, confirmada.text
    editar_so_nela(casal, terceira, partes=[parte([casa], 7000), parte([roupa], 3000)])

    # Pela tela, as partes somam o total: 2 x 150,00 em 3 parcelas de 100,00.
    mudada = mudar_partes(
        casal, criado["id"], [parte([eletronico], 15000), parte([roupa], 15000, pessoa="esposa")]
    )

    assert mudada.status_code == 200, mudada.text
    assert mudada.json()["parcelas_mantidas"] == 1
    assert divisao(mudada.json()) == [15000, 15000]
    depois = parcelas(casal, criado["id"])
    assert [divisao(l) for l in depois] == [[5000, 5000], [5000, 5000], [7000, 3000]]
    assert depois[0]["situacao"] == "realizado"
    assert [p["pessoa"] for p in depois[0]["partes"]] == [None, "esposa"]


def test_juntar_as_partes_pela_tela_devolve_a_classificacao(casal: Casal, categorias):
    _, eletronico, _ = categorias
    criado = parcelado(casal, casal.conta(), tres_partes(categorias)).json()

    junta = mudar_partes(casal, criado["id"], [parte([eletronico], 100000, tags=["fone"])])

    assert junta.status_code == 200, junta.text
    gravada = regra(casal, criado["id"])
    assert (gravada["partes"], gravada["categoria_ids"], gravada["tags"]) == (
        [],
        [eletronico],
        ["fone"],
    )
    assert {
        (tuple(l["categoria_ids"]), len(l["partes"])) for l in parcelas(casal, criado["id"])
    } == {((eletronico,), 0)}


def test_dividir_pela_tela_o_parcelamento_sem_partes(casal: Casal, categorias):
    roupa, eletronico, _ = categorias
    novo = parcelado(casal, casal.conta(), [parte([roupa], 20000), parte([eletronico], 10000)])
    assert novo.status_code == 201, novo.text
    id = novo.json()["id"]
    assert mudar_partes(casal, id, [parte([roupa], 1)]).status_code == 200

    # Pela tela, em valor da parcela: 60,00 + 40,00 de uma parcela de 100,00.
    dividida = mudar_partes(casal, id, [parte([roupa], 6000), parte([eletronico], 4000)])

    assert dividida.status_code == 200, dividida.text
    assert divisao(regra(casal, id)) == [18000, 12000]
    assert [divisao(l) for l in parcelas(casal, id)] == [[6000, 4000]] * 3


def test_a_leitura_traz_a_proporcao_para_a_mudanca_so_de_classificacao(casal: Casal, categorias):
    roupa, eletronico, casa = categorias
    # A proporção vem de uma parcela de 100,00 (66,67 + 33,33) e não é a do total em 7 parcelas.
    criado = parcelado(
        casal,
        casal.conta(),
        [parte([roupa], 6667), parte([eletronico], 3333)],
        valor_total_centavos=None,
        valor_da_parcela_centavos=10000,
        parcelas=7,
    ).json()
    antes = [divisao(l) for l in parcelas(casal, criado["id"])]
    lido = regra(casal, criado["id"])
    assert lido["proporcao_das_partes"] == [6667, 3333]

    # Só a categoria da 2ª parte muda; vai a proporção da leitura, como a tela manda.
    partes = [
        p | {"valor_centavos": v} for p, v in zip(lido["partes"], lido["proporcao_das_partes"])
    ]
    partes[1]["categoria_ids"] = [casa]
    mudada = mudar_partes(casal, criado["id"], partes)

    assert mudada.status_code == 200, mudada.text
    assert mudada.json()["proporcao_das_partes"] == [6667, 3333]
    assert [divisao(l) for l in parcelas(casal, criado["id"])] == antes
