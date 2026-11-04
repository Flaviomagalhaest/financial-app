"""Os lançamentos que a fatura, o Mês e o parcelamento leem do servidor (ticket 165, ADR 0024):
com a janela do aparelho, a lista guardada não tem os meses antigos."""

from datetime import date
from uuid import uuid4

import pytest

from app import lancamentos
from tests.conftest import Casal
from tests.test_cartoes import comprar, novo_cartao
from tests.test_lancamentos import lancamento
from tests.test_parcelamentos import parcelamento


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lancamentos, "hoje", lambda: date(2026, 10, 28))


def ler(casal: Casal, caminho: str) -> list[dict]:
    resposta = casal.pedir("flavio", "GET", caminho)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_compras_da_fatura_incluem_as_do_adicional_e_deixam_de_fora_as_de_outra_fatura(
    casal: Casal,
):
    titular = novo_cartao(casal)["id"]
    adicional = casal.pedir(
        "flavio", "POST", "/api/cartoes", json={"nome": "Adicional", "titular_id": titular}
    ).json()["id"]
    outro = novo_cartao(casal, nome="Outro")["id"]
    # A fatura fecha dia 25: 10/04 e 28/03 contam em abril; 28/04 conta em maio.
    do_titular = comprar(casal, titular, "2026-04-10")
    do_adicional = comprar(casal, adicional, "2026-03-28")
    comprar(casal, titular, "2026-04-28")
    comprar(casal, outro, "2026-04-10")

    achadas = ler(casal, f"/api/cartoes/{titular}/faturas/2026-04-01/lancamentos")

    assert {l["id"] for l in achadas} == {do_titular["id"], do_adicional["id"]}


def test_lancamentos_do_mes_sao_os_que_contam_nele_e_a_compra_no_cartao_conta_na_fatura(
    casal: Casal,
):
    conta, cartao = casal.conta(), novo_cartao(casal)["id"]
    categoria = casal.categoria()
    avulso = casal.pedir(
        "flavio", "POST", "/api/lancamentos", json=lancamento(conta, [categoria], data="2026-04-10")
    ).json()
    no_cartao = comprar(casal, cartao, "2026-03-28")  # conta em abril
    casal.pedir(
        "flavio", "POST", "/api/lancamentos", json=lancamento(conta, [categoria], data="2026-03-10")
    )

    achados = ler(casal, "/api/meses/2026-04/lancamentos")

    assert {l["id"] for l in achados} == {avulso["id"], no_cartao["id"]}


def test_parcelas_do_parcelamento_vem_todas_e_so_as_dele(casal: Casal):
    conta, categoria = casal.conta(), casal.categoria()
    novo = parcelamento(conta, [categoria], parcelas=4)
    outro = parcelamento(conta, [categoria], parcelas=2)
    for p in (novo, outro):
        assert casal.pedir("flavio", "POST", "/api/parcelamentos", json=p).status_code == 201

    achadas = ler(casal, f"/api/parcelamentos/{novo['id']}/lancamentos")

    assert [l["parcela"] for l in achadas] == [1, 2, 3, 4]
    assert {l["parcelamento_id"] for l in achadas} == {novo["id"]}


def test_parcelamento_que_nao_existe_e_404(casal: Casal):
    resposta = casal.pedir("flavio", "GET", f"/api/parcelamentos/{uuid4()}/lancamentos")
    assert resposta.status_code == 404
