"""Favoritos (ticket 62): lançamentos-modelo que o casal lança de novo com um toque. Cada favorito
guarda conta, categorias, tags, pessoa e um valor inicial; o valor padrão que o aparelho mostra é o
do último lançamento feito com a mesma **identidade** (descrição normalizada, tipo, conta,
categorias, tags e pessoa). A mesma identidade conta os usos que fazem de um lançamento repetido um
**sugerido**. Favoritos precisam de internet para mudar (ADR 0011); a leitura vai para o aparelho."""

import json
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, ValidationError, model_validator

from app.banco import conectar, em_transacao
from app.config import valores_iniciais
from app.lancamentos import conferir_ligacoes, hoje, url_do_banco
from app.login import UsuarioLogado
from app.sugestao import ParteDoModelo, chave, identidade_da_parte

router = APIRouter(prefix="/api")


class DadosDoFavorito(BaseModel):
    descricao: str = ""
    tipo: Literal["despesa", "receita"]
    conta_id: UUID
    # Vazias, com as partes: a compra com partes classifica em cada parte.
    categoria_ids: list[UUID] = []
    tags: list[str] = []
    pessoa: str | None = None
    valor_centavos: int = Field(gt=0)
    partes: list[ParteDoModelo] = []

    @model_validator(mode="after")
    def _com_ou_sem_partes(self):
        if not self.partes:
            if not self.categoria_ids:
                raise ValueError("o favorito precisa de uma categoria ou de partes")
            return self
        if len(self.partes) < 2:
            raise ValueError("a compra tem duas partes ou mais")
        if self.tipo != "despesa":
            raise ValueError("partes só na despesa")
        if self.categoria_ids or self.tags or self.pessoa:
            raise ValueError("a compra com partes não tem categoria, tag nem pessoa próprias")
        soma = sum(p.valor_centavos for p in self.partes)
        if soma != self.valor_centavos:
            raise ValueError(f"as partes somam {soma} centavos e o valor é {self.valor_centavos}")
        return self


class NovoFavorito(DadosDoFavorito):
    id: UUID


class Favorito(NovoFavorito):
    ordem: int
    # O valor do último lançamento com a identidade do favorito; sem nenhum, o inicial.
    valor_padrao_centavos: int


def identidade_de(
    descricao, tipo, conta_id, categoria_ids, tags, pessoa, partes=(), valor_centavos=0
) -> str:
    """O que faz dois lançamentos serem "o mesmo": a base dos usos e do valor padrão. Com partes,
    entram também a descrição, as categorias, as tags, a pessoa e a proporção de cada uma, na
    ordem; sem partes, a identidade é a de antes (ADR 0022)."""
    base = [
        chave(descricao),
        tipo,
        str(conta_id),
        sorted(str(c) for c in categoria_ids),
        sorted(t.casefold() for t in tags),
        pessoa,
    ]
    if partes:
        base.append([identidade_da_parte(p, valor_centavos) for p in partes])
    return json.dumps(base)


def identidade(dados: DadosDoFavorito) -> str:
    return identidade_de(
        dados.descricao,
        dados.tipo,
        dados.conta_id,
        dados.categoria_ids,
        dados.tags,
        dados.pessoa,
        dados.partes,
        dados.valor_centavos,
    )


class _Grupo(BaseModel):
    """Os lançamentos de uma identidade: o último deles e quantos são."""

    dados: DadosDoFavorito
    usos: int


def _partes_dos_lancamentos(conn) -> dict[UUID, list[ParteDoModelo]]:
    """As partes de cada compra, na ordem delas. A categoria e a tag arquivadas contam, como na
    compra sem partes."""
    categorias: dict[UUID, list[UUID]] = {}
    for parte_id, categoria_id in conn.execute(
        "SELECT parte_id, categoria_id FROM parte_categorias ORDER BY categoria_id"
    ):
        categorias.setdefault(parte_id, []).append(categoria_id)
    tags: dict[UUID, list[str]] = {}
    for parte_id, nome in conn.execute(
        "SELECT pt.parte_id, t.nome FROM parte_tags pt JOIN tags t ON t.id = pt.tag_id"
        " ORDER BY t.nome"
    ):
        tags.setdefault(parte_id, []).append(nome)
    partes: dict[UUID, list[ParteDoModelo]] = {}
    for id, lancamento_id, descricao, valor, pessoa in conn.execute(
        "SELECT id, lancamento_id, descricao, valor_centavos, pessoa FROM lancamento_partes"
        " ORDER BY lancamento_id, ordem"
    ):
        if id not in categorias:
            continue
        partes.setdefault(lancamento_id, []).append(
            ParteDoModelo(
                descricao=descricao,
                valor_centavos=valor,
                categoria_ids=categorias[id],
                tags=tags.get(id, []),
                pessoa=pessoa,
            )
        )
    return partes


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
    partes = _partes_dos_lancamentos(conn)
    grupos: dict[str, _Grupo] = {}
    for id, descricao, tipo, conta_id, pessoa, valor in conn.execute(
        "SELECT id, descricao, tipo, conta_id, pessoa, valor_centavos FROM lancamentos"
        " WHERE excluido_em IS NULL AND data <= %s AND valor_centavos > 0"
        " ORDER BY data DESC, criado_em DESC, id",
        (hoje(),),
    ):
        if id in partes:
            # A compra com partes não tem classificação própria: vale a das partes. A que não
            # fecha (dado antigo, parte sem categoria) fica de fora em vez de derrubar a lista.
            try:
                dados = DadosDoFavorito(
                    descricao=descricao or "",
                    tipo=tipo,
                    conta_id=conta_id,
                    valor_centavos=valor,
                    partes=partes[id],
                )
            except ValidationError:
                continue
        elif id in categorias:
            dados = DadosDoFavorito(
                descricao=descricao or "",
                tipo=tipo,
                conta_id=conta_id,
                categoria_ids=categorias[id],
                tags=tags.get(id, []),
                pessoa=pessoa,
                valor_centavos=valor,
            )
        else:
            continue
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
        " identidade, partes FROM favoritos WHERE estado = 'favorito' ORDER BY ordem, id"
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
            partes=json.loads(partes) if partes else [],
            valor_padrao_centavos=grupos[identidade_].dados.valor_centavos
            if identidade_ in grupos
            else valor,
        )
        for id, descricao, tipo, conta_id, categorias, tags, pessoa, valor, ordem, identidade_, partes in linhas
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
        and not any(arquivadas.intersection(p.categoria_ids) for p in grupo.dados.partes)
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
        " categoria_ids, tags, pessoa, valor_centavos, ordem, criado_por, partes)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
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
            json.dumps([p.model_dump(mode="json") for p in dados.partes]),
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
