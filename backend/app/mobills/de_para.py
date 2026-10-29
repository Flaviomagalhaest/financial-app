"""O de-para de categorias e tags (ticket 04 e `## Answer` do ticket 18): cada nome de `Categoria` e
de `Tags` do Mobills, de despesa e de receita, vira categoria, tag ou pessoa no app, ou é
descartado. O padrão é o mesmo nome e o mesmo papel; "viagem" e "ilhabela" viram a categoria
Viagem."""

from collections import Counter
from dataclasses import dataclass, replace

PAPEIS = ("categoria", "tag", "pessoa", "descartar")
VIRAM_A_CATEGORIA_VIAGEM = {"viagem", "ilhabela"}


@dataclass(frozen=True)
class Regra:
    papel: str
    nome: str


Chave = tuple[str, str, str]  # tipo do lançamento, 'Categoria' ou 'Tag', nome no Mobills


def chaves(lancamento) -> list[Chave]:
    """Os nomes do Mobills que um lançamento ainda não traduzido carrega."""
    return [(lancamento.tipo, "Categoria", c) for c in lancamento.categorias] + [
        (lancamento.tipo, "Tag", t) for t in lancamento.tags
    ]


def proposta(chave: Chave) -> Regra:
    _, origem, nome = chave
    if origem == "Tag" and nome.casefold() in VIRAM_A_CATEGORIA_VIAGEM:
        return Regra("categoria", "Viagem")
    return Regra(origem.casefold(), nome)


def contar(lancamentos) -> Counter[Chave]:
    return Counter(chave for x in lancamentos for chave in chaves(x))


def aplicar(lancamento, regras: dict[Chave, Regra]):
    """O lançamento com os nomes do app; sem regra, vale a proposta."""
    categorias: list[str] = []
    tags: list[str] = []
    pessoa = lancamento.pessoa
    for chave in chaves(lancamento):
        regra = regras.get(chave) or proposta(chave)
        if regra.papel == "categoria":
            categorias.append(regra.nome)
        elif regra.papel == "tag":
            tags.append(regra.nome)
        elif regra.papel == "pessoa":
            pessoa = regra.nome
    return replace(
        lancamento,
        categorias=list(dict.fromkeys(categorias)),
        tags=list(dict.fromkeys(tags)),
        pessoa=pessoa,
    )
