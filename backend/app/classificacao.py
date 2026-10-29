"""Manutenção das categorias e das tags (ADR 0006): renomear, arquivar, juntar e excluir."""

from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.banco import conectar, em_transacao
from app.lancamentos import Categoria, url_do_banco
from app.login import UsuarioLogado

router = APIRouter(prefix="/api")


def _categoria(conn, id: UUID) -> Categoria | None:
    linha = conn.execute(
        "SELECT id, nome, tipo, arquivada_em IS NOT NULL FROM categorias WHERE id = %s", (id,)
    ).fetchone()
    return (
        Categoria(id=linha[0], nome=linha[1], tipo=linha[2], arquivada=linha[3]) if linha else None
    )


def _juntar_itens_do_planejamento(conn, origem: UUID, destino: UUID) -> None:
    """O item da origem passa para o destino; nos meses em que os dois têm item, os valores se
    somam num item só (o do destino)."""
    for id, mes, valor in conn.execute(
        "SELECT id, mes, valor_centavos FROM itens_do_planejamento WHERE categoria_id = %s",
        (origem,),
    ).fetchall():
        do_destino = conn.execute(
            "SELECT id FROM itens_do_planejamento WHERE categoria_id = %s AND mes = %s",
            (destino, mes),
        ).fetchone()
        if do_destino:
            conn.execute(
                "UPDATE itens_do_planejamento SET valor_centavos = valor_centavos + %s,"
                " alterado_em = now() WHERE id = %s",
                (valor, do_destino[0]),
            )
            conn.execute("DELETE FROM itens_do_planejamento WHERE id = %s", (id,))
        else:
            conn.execute(
                "UPDATE itens_do_planejamento SET categoria_id = %s, alterado_em = now()"
                " WHERE id = %s",
                (destino, id),
            )


def _juntar_item_do_modelo(conn, origem: UUID, destino: UUID) -> None:
    """Como nos meses: o valor da origem se soma ao do destino, ou passa para ele."""
    da_origem = conn.execute(
        "SELECT valor_centavos FROM modelo_do_planejamento WHERE categoria_id = %s", (origem,)
    ).fetchone()
    if not da_origem:
        return
    conn.execute("DELETE FROM modelo_do_planejamento WHERE categoria_id = %s", (origem,))
    conn.execute(
        "INSERT INTO modelo_do_planejamento (categoria_id, valor_centavos, alterado_por)"
        " VALUES (%s, %s, 'sistema')"
        " ON CONFLICT (categoria_id) DO UPDATE SET"
        " valor_centavos = modelo_do_planejamento.valor_centavos + excluded.valor_centavos,"
        " alterado_em = now()",
        (destino, da_origem[0]),
    )


class Juncao(BaseModel):
    destino_id: UUID


@router.post("/categorias/{id}/juntar", response_model=Categoria, operation_id="juntar_categoria")
def juntar_categoria(
    id: UUID, juncao: Juncao, usuario: UsuarioLogado, request: Request
) -> Categoria:
    """Move os lançamentos, as transferências e os itens do planejamento da categoria para o destino,
    do mesmo tipo, e exclui a origem."""

    def trabalho(conn):
        origem, destino = _categoria(conn, id), _categoria(conn, juncao.destino_id)
        if not origem or not destino:
            raise HTTPException(status_code=404, detail="categoria não encontrada")
        if origem.id == destino.id:
            raise HTTPException(status_code=422, detail="origem e destino são a mesma categoria")
        if origem.tipo != destino.tipo:
            raise HTTPException(status_code=422, detail="categorias de tipos diferentes")
        if destino.arquivada:
            raise HTTPException(status_code=422, detail="categoria de destino arquivada")
        conn.execute(
            "INSERT INTO lancamento_categorias (lancamento_id, categoria_id)"
            " SELECT lancamento_id, %s FROM lancamento_categorias WHERE categoria_id = %s"
            " ON CONFLICT DO NOTHING",
            (destino.id, origem.id),
        )
        conn.execute("DELETE FROM lancamento_categorias WHERE categoria_id = %s", (origem.id,))
        _juntar_itens_do_planejamento(conn, origem.id, destino.id)
        _juntar_item_do_modelo(conn, origem.id, destino.id)
        conn.execute(
            "UPDATE transferencias SET categoria_id = %s WHERE categoria_id = %s",
            (destino.id, origem.id),
        )
        conn.execute("DELETE FROM categorias WHERE id = %s", (origem.id,))
        return destino

    return em_transacao(url_do_banco(request), trabalho)


@router.delete("/categorias/{id}", status_code=204, operation_id="excluir_categoria")
def excluir_categoria(id: UUID, usuario: UsuarioLogado, request: Request) -> Response:
    """Idempotente. Com lançamentos, recusa: arquive ou junte em outra."""

    def trabalho(conn):
        if conn.execute(
            "SELECT 1 FROM lancamento_categorias WHERE categoria_id = %s LIMIT 1", (id,)
        ).fetchone():
            raise HTTPException(status_code=409, detail="categoria com lançamentos")
        if conn.execute(
            "SELECT 1 FROM transferencias WHERE categoria_id = %s LIMIT 1", (id,)
        ).fetchone():
            raise HTTPException(status_code=409, detail="categoria com transferências")
        if conn.execute(
            "SELECT 1 FROM itens_do_planejamento WHERE categoria_id = %s LIMIT 1", (id,)
        ).fetchone():
            raise HTTPException(status_code=409, detail="categoria com item do planejamento")
        if conn.execute(
            "SELECT 1 FROM modelo_do_planejamento WHERE categoria_id = %s", (id,)
        ).fetchone():
            raise HTTPException(status_code=409, detail="categoria no modelo do planejamento")
        conn.execute("DELETE FROM categorias WHERE id = %s", (id,))

    em_transacao(url_do_banco(request), trabalho)
    return Response(status_code=204)


class Tag(BaseModel):
    id: UUID
    nome: str
    arquivada: bool = False


def _tag(conn, id: UUID) -> Tag | None:
    linha = conn.execute(
        "SELECT id, nome, arquivada_em IS NOT NULL FROM tags WHERE id = %s", (id,)
    ).fetchone()
    return Tag(id=linha[0], nome=linha[1], arquivada=linha[2]) if linha else None


@router.get("/tags", response_model=list[Tag], operation_id="listar_tags")
def listar_tags(usuario: UsuarioLogado, request: Request) -> list[Tag]:
    with conectar(url_do_banco(request)) as conn:
        linhas = conn.execute(
            "SELECT id, nome, arquivada_em IS NOT NULL FROM tags ORDER BY nome, id"
        ).fetchall()
    return [Tag(id=i, nome=n, arquivada=a) for i, n, a in linhas]


class NovaTag(BaseModel):
    nome: str = Field(min_length=1)


class MudancaDeTag(BaseModel):
    nome: str | None = Field(default=None, min_length=1)
    arquivada: bool | None = None


def _nome_em_uso(conn, nome: str, exceto: UUID | None = None) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM tags WHERE lower(nome) = lower(%s) AND id IS DISTINCT FROM %s",
            (nome.strip(), exceto),
        ).fetchone()
        is not None
    )


@router.post("/tags", status_code=201, response_model=Tag, operation_id="criar_tag")
def criar_tag(nova: NovaTag, usuario: UsuarioLogado, request: Request) -> Tag:
    nome, id = nova.nome.strip(), uuid4()

    def trabalho(conn):
        if not nome or _nome_em_uso(conn, nome):
            raise HTTPException(status_code=409, detail="já existe uma tag com esse nome")
        conn.execute(
            "INSERT INTO tags (id, nome, criado_por) VALUES (%s, %s, %s)", (id, nome, usuario)
        )

    em_transacao(url_do_banco(request), trabalho)
    return Tag(id=id, nome=nome)


@router.patch("/tags/{id}", response_model=Tag, operation_id="mudar_tag")
def mudar_tag(id: UUID, mudanca: MudancaDeTag, usuario: UsuarioLogado, request: Request) -> Tag:
    def trabalho(conn):
        if not _tag(conn, id):
            raise HTTPException(status_code=404, detail="tag não encontrada")
        if mudanca.nome is not None:
            nome = mudanca.nome.strip()
            if not nome:
                raise HTTPException(status_code=422, detail="tag sem nome")
            if _nome_em_uso(conn, nome, id):
                raise HTTPException(status_code=409, detail="já existe uma tag com esse nome")
            conn.execute("UPDATE tags SET nome = %s WHERE id = %s", (nome, id))
        if mudanca.arquivada is not None:
            conn.execute(
                "UPDATE tags SET arquivada_em = "
                + ("now()" if mudanca.arquivada else "NULL")
                + " WHERE id = %s",
                (id,),
            )
        return _tag(conn, id)

    return em_transacao(url_do_banco(request), trabalho)


@router.post("/tags/{id}/juntar", response_model=Tag, operation_id="juntar_tag")
def juntar_tag(id: UUID, juncao: Juncao, usuario: UsuarioLogado, request: Request) -> Tag:
    """Move os lançamentos da tag para o destino e exclui a origem."""

    def trabalho(conn):
        origem, destino = _tag(conn, id), _tag(conn, juncao.destino_id)
        if not origem or not destino:
            raise HTTPException(status_code=404, detail="tag não encontrada")
        if origem.id == destino.id:
            raise HTTPException(status_code=422, detail="origem e destino são a mesma tag")
        if destino.arquivada:
            raise HTTPException(status_code=422, detail="tag de destino arquivada")
        conn.execute(
            "INSERT INTO lancamento_tags (lancamento_id, tag_id)"
            " SELECT lancamento_id, %s FROM lancamento_tags WHERE tag_id = %s"
            " ON CONFLICT DO NOTHING",
            (destino.id, origem.id),
        )
        conn.execute("DELETE FROM lancamento_tags WHERE tag_id = %s", (origem.id,))
        conn.execute("DELETE FROM tags WHERE id = %s", (origem.id,))
        return destino

    return em_transacao(url_do_banco(request), trabalho)


@router.delete("/tags/{id}", status_code=204, operation_id="excluir_tag")
def excluir_tag(id: UUID, usuario: UsuarioLogado, request: Request) -> Response:
    """Idempotente. Com lançamentos, recusa: arquive ou junte em outra."""

    def trabalho(conn):
        if conn.execute(
            "SELECT 1 FROM lancamento_tags WHERE tag_id = %s LIMIT 1", (id,)
        ).fetchone():
            raise HTTPException(status_code=409, detail="tag com lançamentos")
        conn.execute("DELETE FROM tags WHERE id = %s", (id,))

    em_transacao(url_do_banco(request), trabalho)
    return Response(status_code=204)
