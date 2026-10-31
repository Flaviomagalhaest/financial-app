"""As regras que o app repete para o aviso de planejamento sem internet (ticket 52), contra as
mesmas tabelas que `web/e2e/tabelas.spec.ts` roda no código do app."""

import json
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.faturas import Titular, escolher_fatura
from app.item_em_que_conta import onde_conta
from app.planejamento import percentual

TABELAS = Path(__file__).resolve().parents[2] / "tabelas-de-teste"


def casos(nome: str) -> list[dict]:
    return json.loads((TABELAS / f"{nome}.json").read_text())["casos"]


@pytest.mark.parametrize("caso", casos("onde-conta"), ids=lambda c: c["caso"])
def test_onde_conta(caso: dict):
    assert onde_conta(set(caso["com_item"]), caso["escolhida"], caso["atual"]) == (
        caso["conta_em"],
        caso["a_escolher"],
    )


@pytest.mark.parametrize("caso", casos("percentual"), ids=lambda c: c["caso"])
def test_percentual(caso: dict):
    assert percentual(caso["realizado_e_previsto"], caso["planejado"]) == caso["percentual"]


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
