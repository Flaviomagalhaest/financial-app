"""Favoritos (ticket 62): lançamentos-modelo que o casal lança de novo com um toque. Cada favorito
guarda conta, categorias, tags, pessoa e um valor inicial; o valor padrão que o aparelho mostra é o
do último lançamento feito com a mesma **identidade** (descrição normalizada, tipo, conta,
categorias, tags e pessoa). A mesma identidade conta os usos que fazem de um lançamento repetido um
**sugerido**. Favoritos precisam de internet para mudar (ADR 0011); a leitura vai para o aparelho."""

import json
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.banco import conectar, em_transacao
from app.config import valores_iniciais
from app.lancamentos import conferir_ligacoes, hoje, url_do_banco
from app.login import UsuarioLogado
from app.sugestao import chave

router = APIRouter(prefix="/api")


class DadosDoFavorito(BaseModel):
    descricao: str = ""
    tipo: Literal["despesa", "receita"]
    conta_id: UUID
    categoria_ids: list[UUID] = Field(min_length=1)
    tags: list[str] = []
    pessoa: str | None = None
    valor_centavos: int = Field(gt=0)


class NovoFavorito(DadosDoFavorito):
    id: UUID


class Favorito(NovoFavorito):
    ordem: int
    # O valor do último lançamento com a identidade do favorito; sem nenhum, o inicial.
    valor_padrao_centavos: int


def identidade_de(descricao, tipo, conta_id, categoria_ids, tags, pessoa) -> str:
    """O que faz dois lançamentos serem "o mesmo": a base dos usos e do valor padrão."""
    return json.dumps(
        [
            chave(descricao),
            tipo,
            str(conta_id),
            sorted(str(c) for c in categoria_ids),
            sorted(t.casefold() for t in tags),
            pessoa,
        ]
    )


def identidade(dados: DadosDoFavorito) -> str:
    return identidade_de(
        dados.descricao, dados.tipo, dados.conta_id, dados.categoria_ids, dados.tags, dados.pessoa
    )


class _Grupo(BaseModel):
    """Os lançamentos de uma identidade: o último deles e quantos são."""

    dados: DadosDoFavorito
    usos: int


def _grupos(conn) -> dict[str, _Grupo]:
    """Por identidade, o último lançamento (o de data mais recente, e entre os do mesmo dia o
    criado por último) e o total. O futuro, o excluído e o sem categoria ficam de fora. Categoria
    e tag arquivadas contam: a identidade do favorito não muda quando se arquiva."""
    categorias: dict[UUID, list[UUID]] = {}
    for lancamento_id, categoria_id in conn.execute(
        "SELECT lancamento_id, categoria_id FROM lancamento_categorias ORDER BY categoria_id"
    ):
        categorias.setdefault(lancamento_id, []).append(categoria_id)
    tags: dict[UUID, list[str]] = {}
    for lancamento_id, nome in conn.execute(
        "SELECT lt.lancamento_id, t.nome FROM lancamento_tags lt JOIN tags t ON t.id = lt.tag_id"
        " ORDER BY t.nome"
    ):
        tags.setdefault(lancamento_id, []).append(nome)
    grupos: dict[str, _Grupo] = {}
    for id, descricao, tipo, conta_id, pessoa, valor in conn.execute(
        "SELECT id, descricao, tipo, conta_id, pessoa, valor_centavos FROM lancamentos"
        " WHERE excluido_em IS NULL AND data <= %s AND valor_centavos > 0"
        " ORDER BY data DESC, criado_em DESC, id",
        (hoje(),),
    ):
        if id not in categorias:
            continue
        dados = DadosDoFavorito(
            descricao=descricao or "",
            tipo=tipo,
            conta_id=conta_id,
            categoria_ids=categorias[id],
            tags=tags.get(id, []),
            pessoa=pessoa,
            valor_centavos=valor,
        )
        chave_ = identidade(dados)
        if chave_ in grupos:
            grupos[chave_].usos += 1
        else:
            grupos[chave_] = _Grupo(dados=dados, usos=1)
    return grupos


def _favoritos(conn) -> list[Favorito]:
    grupos = _grupos(conn)
    linhas = conn.execute(
        "SELECT id, descricao, tipo, conta_id, categoria_ids, tags, pessoa, valor_centavos, ordem,"
        " identidade FROM favoritos WHERE estado = 'favorito' ORDER BY ordem, id"
    ).fetchall()
    return [
        Favorito(
            id=id,
            descricao=descricao,
            tipo=tipo,
            conta_id=conta_id,
            categoria_ids=json.loads(categorias),
            tags=json.loads(tags),
            pessoa=pessoa,
            valor_centavos=valor,
            ordem=ordem,
            valor_padrao_centavos=grupos[identidade_].dados.valor_centavos
            if identidade_ in grupos
            else valor,
        )
        for id, descricao, tipo, conta_id, categorias, tags, pessoa, valor, ordem, identidade_ in linhas
    ]


class Sugerido(DadosDoFavorito):
    # O que identifica o sugerido para dispensá-lo.
    chave: str
    usos: int


class Favoritos(BaseModel):
    favoritos: list[Favorito]
    # Os mais repetidos que ainda não são favoritos nem foram dispensados.
    sugeridos: list[Sugerido]


def _sugeridos(conn, favoritos: list[Favorito]) -> list[Sugerido]:
    config = valores_iniciais()["favoritos"]
    fora = {linha[0] for linha in conn.execute("SELECT identidade FROM favoritos")}
    arquivadas = {
        linha[0]
        for linha in conn.execute("SELECT id FROM categorias WHERE arquivada_em IS NOT NULL")
    }
    # Não se sugere o que já não se pode escolher: categoria arquivada.
    candidatos = [
        (chave_, grupo)
        for chave_, grupo in _grupos(conn).items()
        if chave_ not in fora
        and grupo.usos >= config["usosMinimos"]
        and not arquivadas.intersection(grupo.dados.categoria_ids)
    ]
    # Mais usados primeiro; o empate fica com o que foi lançado por último (a ordem dos grupos).
    candidatos.sort(key=lambda c: -c[1].usos)
    return [
        Sugerido(chave=chave_, usos=grupo.usos, **grupo.dados.model_dump())
        for chave_, grupo in candidatos[: config["sugeridos"]]
    ]


@router.get("/favoritos", response_model=Favoritos, operation_id="listar_favoritos")
def listar_favoritos(usuario: UsuarioLogado, request: Request) -> Favoritos:
    with conectar(url_do_banco(request)) as conn:
        favoritos = _favoritos(conn)
        return Favoritos(favoritos=favoritos, sugeridos=_sugeridos(conn, favoritos))


@router.post("/favoritos", status_code=201, response_model=Favorito, operation_id="criar_favorito")
def criar_favorito(
    novo: NovoFavorito, usuario: UsuarioLogado, request: Request, response: Response
) -> Favorito:
    """Reenviar o mesmo id, ou favoritar o que já é favorito, devolve o que já está gravado, com
    200. Favoritar o que foi removido ou dispensado o traz de volta."""

    def gravar(conn) -> Favorito:
        chave_ = identidade(novo)
        existente = conn.execute(
            "SELECT id, estado FROM favoritos WHERE id = %s OR identidade = %s",
            (novo.id, chave_),
        ).fetchall()
        ja_favorito = next((id for id, estado in existente if estado == "favorito"), None)
        if ja_favorito:
            response.status_code = 200
            return next(f for f in _favoritos(conn) if f.id == ja_favorito)
        conferir_ligacoes(conn, novo)
        conn.execute("DELETE FROM favoritos WHERE id = %s OR identidade = %s", (novo.id, chave_))
        ordem = conn.execute(
            "SELECT COALESCE(max(ordem), 0) + 1 FROM favoritos WHERE estado = 'favorito'"
        ).fetchone()[0]
        _inserir(conn, novo.id, "favorito", chave_, novo, ordem, usuario)
        return next(f for f in _favoritos(conn) if f.id == novo.id)

    return em_transacao(url_do_banco(request), gravar)


def _inserir(conn, id: UUID, estado: str, chave_: str, dados: DadosDoFavorito, ordem, usuario):
    conn.execute(
        "INSERT INTO favoritos (id, estado, identidade, descricao, tipo, conta_id,"
        " categoria_ids, tags, pessoa, valor_centavos, ordem, criado_por)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            id,
            estado,
            chave_,
            dados.descricao,
            dados.tipo,
            dados.conta_id,
            json.dumps([str(c) for c in dados.categoria_ids]),
            json.dumps(dados.tags),
            dados.pessoa,
            dados.valor_centavos,
            ordem,
            usuario,
        ),
    )


@router.delete("/favoritos/{id}", status_code=204, operation_id="remover_favorito")
def remover_favorito(id: UUID, usuario: UsuarioLogado, request: Request) -> Response:
    """Idempotente. O removido vira dispensado: com 5 usos ou mais, não volta como sugerido."""

    def remover(conn) -> None:
        conn.execute(
            "UPDATE favoritos SET estado = 'dispensado', ordem = NULL"
            " WHERE id = %s AND estado = 'favorito'",
            (id,),
        )

    em_transacao(url_do_banco(request), remover)
    return Response(status_code=204)


class NovaOrdem(BaseModel):
    ids: list[UUID]


@router.put("/favoritos/ordem", response_model=Favoritos, operation_id="reordenar_favoritos")
def reordenar_favoritos(nova: NovaOrdem, usuario: UsuarioLogado, request: Request) -> Favoritos:
    """A lista inteira, na ordem nova: o que faltar ou sobrar recusa (alguém mudou a lista)."""

    def reordenar(conn) -> Favoritos:
        atuais = {f.id for f in _favoritos(conn)}
        if set(nova.ids) != atuais or len(nova.ids) != len(atuais):
            raise HTTPException(status_code=422, detail="a lista de favoritos mudou")
        for ordem, id in enumerate(nova.ids, start=1):
            conn.execute("UPDATE favoritos SET ordem = %s WHERE id = %s", (ordem, id))
        favoritos = _favoritos(conn)
        return Favoritos(favoritos=favoritos, sugeridos=_sugeridos(conn, favoritos))

    return em_transacao(url_do_banco(request), reordenar)


class Dispensa(BaseModel):
    chave: str


@router.post("/favoritos/sugeridos/dispensar", status_code=204, operation_id="dispensar_sugerido")
def dispensar_sugerido(dispensa: Dispensa, usuario: UsuarioLogado, request: Request) -> Response:
    """Idempotente: dispensar de novo o mesmo sugerido também dá 204."""

    def gravar(conn) -> None:
        grupo = _grupos(conn).get(dispensa.chave)
        if (
            not grupo
            or conn.execute(
                "SELECT 1 FROM favoritos WHERE identidade = %s", (dispensa.chave,)
            ).fetchone()
        ):
            return
        _inserir(conn, uuid4(), "dispensado", dispensa.chave, grupo.dados, None, usuario)

    em_transacao(url_do_banco(request), gravar)
    return Response(status_code=204)
