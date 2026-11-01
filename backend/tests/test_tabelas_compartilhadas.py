"""As regras que o app repete para o aviso de planejamento sem internet (ticket 52) e para mostrar
a divisão do parcelamento (ticket 98), contra as mesmas tabelas que `web/e2e/tabelas.spec.ts`
roda no código do app."""

import json
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.faturas import Titular, escolher_fatura
from app.item_em_que_conta import onde_conta
from app.parcelamentos import parcelas_puladas, valor_da_parcela
from app.planejamento import percentual
from app.recorrencias import NovaRecorrencia, ocorrencias_puladas

TABELAS = Path(__file__).resolve().parents[2] / "tabelas-de-teste"


def casos(nome: str, chave: str = "casos") -> list[dict]:
    return json.loads((TABELAS / f"{nome}.json").read_text())[chave]


@pytest.mark.parametrize("caso", casos("onde-conta"), ids=lambda c: c["caso"])
def test_onde_conta(caso: dict):
    assert onde_conta(set(caso["com_item"]), caso["escolhida"], caso["atual"]) == (
        caso["conta_em"],
        caso["a_escolher"],
    )


@pytest.mark.parametrize("caso", casos("percentual"), ids=lambda c: c["caso"])
def test_percentual(caso: dict):
    assert percentual(caso["realizado_e_previsto"], caso["planejado"]) == caso["percentual"]


@pytest.mark.parametrize("caso", casos("divisao-das-parcelas"), ids=lambda c: c["caso"])
def test_divisao_das_parcelas(caso: dict):
    total, parcelas = caso["total"], caso["parcelas"]
    assert valor_da_parcela(total, parcelas, 1) == caso["primeira"]
    assert {valor_da_parcela(total, parcelas, n) for n in range(2, parcelas + 1)} == {
        caso["outras"]
    }


@pytest.mark.parametrize("caso", casos("mes-da-compra"), ids=lambda c: c["caso"])
def test_mes_da_compra(caso: dict):
    titular = Titular(
        id=uuid4(),
        nome="Cartão",
        dia_fechamento=caso["titular"]["dia_fechamento"],
        dia_vencimento=None,
        mes_anterior_ao_fechamento=caso["titular"]["mes_anterior_ao_fechamento"],
    )
    gravados = {
        date.fromisoformat(f["mes"]): date.fromisoformat(f["fechamento"])
        for f in caso["faturas"]
        if f["fechamento"]
    }
    data = date.fromisoformat(caso["data"])
    if caso["mes"] is None:
        with pytest.raises(HTTPException):
            escolher_fatura(titular, gravados, data)
    else:
        assert escolher_fatura(titular, gravados, data) == date.fromisoformat(caso["mes"])


@pytest.mark.parametrize("caso", casos("puladas", "recorrencias"), ids=lambda c: c["caso"])
def test_ocorrencias_puladas(caso: dict):
    regra = NovaRecorrencia(
        id=uuid4(),
        tipo="despesa",
        valor_centavos=100,
        tipo_do_valor="estimado",
        conta_id=uuid4(),
        categoria_ids=[uuid4()],
        inicio=date.fromisoformat(caso["inicio"]),
        a_cada=caso["a_cada"],
        unidade=caso["unidade"],
        ate=date.fromisoformat(caso["ate"]) if caso["ate"] else None,
        vezes=caso["vezes"],
    )
    assert ocorrencias_puladas(regra, date.fromisoformat(caso["hoje"])) == caso["puladas"]


@pytest.mark.parametrize("caso", casos("puladas", "parcelamentos"), ids=lambda c: c["caso"])
def test_parcelas_puladas(caso: dict):
    assert (
        parcelas_puladas(
            caso["parcelas"],
            date.fromisoformat(caso["data"]),
            date.fromisoformat(caso["hoje"]),
            caso["no_cartao"],
        )
        == caso["puladas"]
    )
