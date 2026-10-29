"""As duas pessoas do casal: o id é o usuário do token (`sub`) e o nome vem da configuração
`PESSOAS` (JSON `{"<sub>": "<nome>"}`), porque o token de acesso não traz nome (ADR 0002)."""

import json
import os

from fastapi import APIRouter
from pydantic import BaseModel

from app.login import UsuarioLogado

router = APIRouter(prefix="/api")


class Pessoa(BaseModel):
    id: str
    nome: str
    # A pessoa que está chamando.
    eu: bool


def configuradas() -> dict[str, str]:
    """Id e nome de cada pessoa; vazio quando a configuração falta (só desenvolvimento)."""
    return json.loads(os.environ.get("PESSOAS") or "{}")


@router.get("/pessoas", response_model=list[Pessoa], operation_id="listar_pessoas")
def listar_pessoas(usuario: UsuarioLogado) -> list[Pessoa]:
    return [Pessoa(id=id, nome=nome, eu=id == usuario) for id, nome in configuradas().items()]
