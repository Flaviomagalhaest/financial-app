"""Sugestão pela descrição (ticket 22). O contrato é o de uma **fonte de sugestão**: entra a
descrição (e o contexto do lançamento) e sai uma lista de pacotes de categorias, tags, conta e
pessoa, cada um com a sua origem. A v1 só tem a fonte "histórico": aqui ela produz o índice que
o aparelho guarda, e o casamento com o que se digita roda nele, sem internet."""

import re
import unicodedata
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.banco import conectar
from app.config import valores_iniciais
from app.lancamentos import url_do_banco
from app.login import UsuarioLogado

router = APIRouter(prefix="/api")

# O número da parcela que o banco e o Mobills põem na descrição: "Geladeira (2/10)".
_PARCELA = re.compile(r"\(\s*\d+\s*/\s*\d+\s*\)")


def chave(descricao: str) -> str:
    """A descrição como se compara: sem acento, sem maiúscula, sem `(n/total)` e com os espaços
    juntados. O aparelho normaliza o que se digita do mesmo jeito (`web/src/sugestao/`)."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", descricao) if not unicodedata.combining(c)
    )
    return " ".join(_PARCELA.sub(" ", sem_acento.lower()).split())


class Pacote(BaseModel):
    """O que um lançamento anterior sugere, por inteiro: escolhê-lo preenche esses campos."""

    # A descrição normalizada (`chave`), com que o aparelho casa o que se digita.
    chave: str
    # A descrição do lançamento mais recente com este pacote, como foi escrita.
    descricao: str
    tipo: Literal["despesa", "receita"]
    conta_id: UUID
    categoria_ids: list[UUID]
    tags: list[str]
    pessoa: str | None
    # Quando o pacote foi escolhido por último: corrigir as categorias o torna o mais recente.
    em: datetime
    origem: Literal["historico"] = "historico"


class IndiceDeSugestao(BaseModel):
    pacotes: list[Pacote]


def _pacotes(linhas) -> list[Pacote]:
    """Por descrição, os pacotes diferentes, do mais recente ao mais antigo, até o máximo que o
    aparelho mostra: um pacote mais antigo que esses nunca entra na lista de ninguém."""
    maximo = int(valores_iniciais()["sugestao"]["maximoDeSugestoes"])
    vistos: dict[str, set[tuple]] = {}
    pacotes = []
    for descricao, tipo, conta_id, pessoa, em, categorias, tags in linhas:
        k = chave(descricao)
        # Sem descrição não há o que casar; sem categoria que se possa escolher, nada a sugerir.
        if not k or not categorias:
            continue
        do_mesmo = vistos.setdefault(k, set())
        igual = (
            tipo,
            conta_id,
            tuple(categorias),
            tuple(sorted(t.casefold() for t in tags)),
            pessoa,
        )
        if igual in do_mesmo or len(do_mesmo) >= maximo:
            continue
        do_mesmo.add(igual)
        pacotes.append(
            Pacote(
                chave=k,
                descricao=descricao,
                tipo=tipo,
                conta_id=conta_id,
                categoria_ids=categorias,
                tags=tags,
                pessoa=pessoa,
                em=em,
            )
        )
    return pacotes


# Quando o pacote foi escolhido: a criação ou a última mudança num campo dele (a descrição
# inclusive, que muda o lançamento de grupo). Mudar o valor ou a data não conta.
_CAMPOS_DO_PACOTE = ("descricao", "tipo", "conta_id", "categoria_ids", "tags", "pessoa")
_EM = (
    "GREATEST(l.criado_em, (SELECT max(alterado_em) FROM lancamento_campos m"
    f" WHERE m.lancamento_id = l.id AND m.campo IN {_CAMPOS_DO_PACOTE}))"
)


@router.get("/sugestoes", response_model=IndiceDeSugestao, operation_id="indice_de_sugestao")
def indice_de_sugestao(usuario: UsuarioLogado, request: Request) -> IndiceDeSugestao:
    with conectar(url_do_banco(request)) as conn:
        linhas = conn.execute(
            f"SELECT l.descricao, l.tipo, l.conta_id, l.pessoa, {_EM} AS em,"
            # A categoria e a tag arquivadas saem do pacote: não se escolhe mais.
            " ARRAY(SELECT lc.categoria_id FROM lancamento_categorias lc"
            "       JOIN categorias c ON c.id = lc.categoria_id"
            "       WHERE lc.lancamento_id = l.id AND c.arquivada_em IS NULL ORDER BY c.id),"
            " ARRAY(SELECT t.nome FROM lancamento_tags lt JOIN tags t ON t.id = lt.tag_id"
            "       WHERE lt.lancamento_id = l.id AND t.arquivada_em IS NULL ORDER BY t.nome)"
            " FROM lancamentos l WHERE l.excluido_em IS NULL"
            " ORDER BY em DESC, l.data DESC, l.id"
        ).fetchall()
    return IndiceDeSugestao(pacotes=_pacotes(linhas))
