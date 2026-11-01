"""Sugestão pela descrição (tickets 22 e 63). O contrato é o de uma **fonte de sugestão**: entra a
descrição (e o contexto do lançamento) e sai uma lista de sugestões (categorias, tags, conta e
pessoa de um lançamento anterior), cada uma com a sua origem. A v1 só tem a fonte "histórico":
aqui ela produz o índice que o aparelho guarda, e o casamento com o que se digita roda nele, sem
internet (`web/src/dados/sugestao.ts`)."""

import re
import unicodedata
from datetime import UTC, datetime
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
    juntados. O aparelho normaliza o que se digita do mesmo jeito (`chaveDaDescricao`)."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", descricao) if not unicodedata.combining(c)
    )
    return " ".join(_PARCELA.sub(" ", sem_acento.lower()).split())


class Sugestao(BaseModel):
    """O que um lançamento anterior sugere, por inteiro: escolher preenche esses campos."""

    # A descrição normalizada (`chave`), com que o aparelho casa o que se digita.
    chave: str
    # A descrição do lançamento mais recente com estes campos, como foi escrita.
    descricao: str
    tipo: Literal["despesa", "receita"]
    conta_id: UUID
    categoria_ids: list[UUID]
    tags: list[str]
    pessoa: str | None
    # Quando estes campos foram escolhidos por último: corrigir as categorias põe a sugestão
    # como a mais recente.
    em: datetime
    origem: Literal["historico"] = "historico"


class IndiceDeSugestao(BaseModel):
    # A hora do servidor em que o índice foi montado: o aparelho põe por cima o que mudou depois.
    gerado_em: datetime
    sugestoes: list[Sugestao]


def _sugestoes(linhas) -> list[Sugestao]:
    """Por descrição, as sugestões diferentes, da mais recente à mais antiga, até o máximo que o
    aparelho mostra: uma mais antiga que essas nunca entra na lista de ninguém."""
    maximo = int(valores_iniciais()["sugestao"]["maximoDeSugestoes"])
    vistas: dict[str, set[tuple]] = {}
    sugestoes = []
    for descricao, tipo, conta_id, pessoa, em, categorias, tags in linhas:
        k = chave(descricao)
        # Sem descrição não há o que casar; sem categoria que se possa escolher, nada a sugerir.
        if not k or not categorias:
            continue
        da_descricao = vistas.setdefault(k, set())
        identidade = (
            tipo,
            conta_id,
            tuple(categorias),
            tuple(sorted(t.casefold() for t in tags)),
            pessoa,
        )
        if identidade in da_descricao or len(da_descricao) >= maximo:
            continue
        da_descricao.add(identidade)
        sugestoes.append(
            Sugestao(
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
    return sugestoes


# Quando os campos da sugestão foram escolhidos: a criação ou a última mudança num deles (a
# descrição inclusive, que muda o lançamento de grupo). Mudar o valor ou a data não conta. O
# previsto que a recorrência gera foi escolhido com a regra: a ocorrência que a tarefa diária cria
# depois não passa na frente de uma correção feita antes dela.
_CAMPOS_DA_SUGESTAO = ["descricao", "tipo", "conta_id", "categoria_ids", "tags", "pessoa"]


@router.get("/sugestoes", response_model=IndiceDeSugestao, operation_id="indice_de_sugestao")
def indice_de_sugestao(usuario: UsuarioLogado, request: Request) -> IndiceDeSugestao:
    gerado_em = datetime.now(UTC)
    with conectar(url_do_banco(request)) as conn:
        lidos = conn.execute(
            "SELECT l.id, l.descricao, l.tipo, l.conta_id, l.pessoa,"
            " GREATEST("
            "   COALESCE((SELECT r.alterado_em FROM recorrencias r WHERE r.id = l.recorrencia_id),"
            "            l.criado_em),"
            "   (SELECT max(alterado_em) FROM lancamento_campos m"
            "       WHERE m.lancamento_id = l.id AND m.campo = ANY(%s))) AS em"
            " FROM lancamentos l WHERE l.excluido_em IS NULL"
            # A compra com partes entra na sugestão com elas no ticket 141 (ADR 0022).
            " AND NOT EXISTS (SELECT FROM lancamento_partes p WHERE p.lancamento_id = l.id)"
            " ORDER BY em DESC, l.data DESC, l.id",
            (_CAMPOS_DA_SUGESTAO,),
        ).fetchall()
        # A categoria e a tag arquivadas saem da sugestão: não se escolhe mais.
        categorias: dict[UUID, list[UUID]] = {}
        for lancamento_id, categoria_id in conn.execute(
            "SELECT lc.lancamento_id, lc.categoria_id FROM lancamento_categorias lc"
            " JOIN categorias c ON c.id = lc.categoria_id WHERE c.arquivada_em IS NULL"
            " ORDER BY lc.categoria_id"
        ):
            categorias.setdefault(lancamento_id, []).append(categoria_id)
        tags: dict[UUID, list[str]] = {}
        for lancamento_id, nome in conn.execute(
            "SELECT lt.lancamento_id, t.nome FROM lancamento_tags lt JOIN tags t ON t.id = lt.tag_id"
            " WHERE t.arquivada_em IS NULL ORDER BY t.nome"
        ):
            tags.setdefault(lancamento_id, []).append(nome)
    linhas = [
        (descricao, tipo, conta_id, pessoa, em, categorias.get(id, []), tags.get(id, []))
        for id, descricao, tipo, conta_id, pessoa, em in lidos
    ]
    return IndiceDeSugestao(gerado_em=gerado_em, sugestoes=_sugestoes(linhas))
