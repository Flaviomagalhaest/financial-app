"""Contas, categorias e lançamentos simples. Sem chave estrangeira nem trigger (subconjunto do
DSQL, ADR 0009): a API confere as ligações. O id do lançamento nasce no aparelho."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from app.banco import conectar
from app.login import UsuarioLogado

router = APIRouter(prefix="/api")


class NovaConta(BaseModel):
    nome: str = Field(min_length=1)
    tipo: Literal["corrente", "poupanca", "carteira"]


class Conta(NovaConta):
    id: UUID


class NovaCategoria(BaseModel):
    nome: str = Field(min_length=1)
    tipo: Literal["despesa", "receita", "transferencia"]


class Categoria(NovaCategoria):
    id: UUID
    arquivada: bool = False


class NovoLancamento(BaseModel):
    id: UUID
    tipo: Literal["despesa", "receita"]
    valor_centavos: int = Field(gt=0)
    data: date
    descricao: str = ""
    conta_id: UUID
    categoria_ids: list[UUID] = Field(min_length=1)
    # Sem situação, a data decide: futura nasce prevista, de hoje ou do passado, realizada.
    situacao: Literal["previsto", "realizado"] | None = None
    # Pelo nome: a tag que ainda não existe nasce junto com o lançamento.
    tags: list[str] = []

    @field_validator("tags")
    @classmethod
    def _tags_limpas(cls, nomes: list[str]) -> list[str]:
        limpos = [nome.strip() for nome in nomes]
        if "" in limpos:
            raise ValueError("tag sem nome")
        return list({nome.casefold(): nome for nome in limpos}.values())

    @field_validator("categoria_ids")
    @classmethod
    def _sem_repetidas(cls, ids: list[UUID]) -> list[UUID]:
        if len(set(ids)) != len(ids):
            raise ValueError("categoria repetida")
        return ids


class Lancamento(NovoLancamento):
    situacao: Literal["previsto", "realizado"]
    criado_por: str
    criado_em: datetime
    alterado_por: str
    alterado_em: datetime


_COLUNAS = (
    "id, tipo, situacao, valor_centavos, data, descricao, conta_id,"
    " criado_por, criado_em, alterado_por, alterado_em"
)


def _url(request: Request) -> str | None:
    return request.app.state.url


@router.post("/contas", status_code=201, response_model=Conta, operation_id="criar_conta")
def criar_conta(nova: NovaConta, usuario: UsuarioLogado, request: Request) -> Conta:
    id = uuid4()
    with conectar(_url(request)) as conn:
        conn.execute(
            "INSERT INTO contas (id, nome, tipo, criado_por) VALUES (%s, %s, %s, %s)",
            (id, nova.nome, nova.tipo, usuario),
        )
    return Conta(id=id, **nova.model_dump())


@router.get("/contas", response_model=list[Conta], operation_id="listar_contas")
def listar_contas(usuario: UsuarioLogado, request: Request) -> list[Conta]:
    with conectar(_url(request)) as conn:
        linhas = conn.execute("SELECT id, nome, tipo FROM contas ORDER BY nome, id").fetchall()
    return [Conta(id=i, nome=n, tipo=t) for i, n, t in linhas]


@router.post(
    "/categorias", status_code=201, response_model=Categoria, operation_id="criar_categoria"
)
def criar_categoria(nova: NovaCategoria, usuario: UsuarioLogado, request: Request) -> Categoria:
    id = uuid4()
    with conectar(_url(request)) as conn:
        conn.execute(
            "INSERT INTO categorias (id, nome, tipo, criado_por) VALUES (%s, %s, %s, %s)",
            (id, nova.nome, nova.tipo, usuario),
        )
    return Categoria(id=id, **nova.model_dump())


def buscar_categoria(conn, id: UUID) -> Categoria | None:
    linha = conn.execute(
        "SELECT id, nome, tipo, arquivada_em IS NOT NULL FROM categorias WHERE id = %s", (id,)
    ).fetchone()
    return (
        Categoria(id=linha[0], nome=linha[1], tipo=linha[2], arquivada=linha[3]) if linha else None
    )


@router.get("/categorias", response_model=list[Categoria], operation_id="listar_categorias")
def listar_categorias(usuario: UsuarioLogado, request: Request) -> list[Categoria]:
    with conectar(_url(request)) as conn:
        linhas = conn.execute(
            "SELECT id, nome, tipo, arquivada_em IS NOT NULL FROM categorias ORDER BY nome, id"
        ).fetchall()
    return [Categoria(id=i, nome=n, tipo=t, arquivada=a) for i, n, t, a in linhas]


def _situacao_pela_data(dia: date) -> str:
    return "previsto" if dia > datetime.now(ZoneInfo("America/Sao_Paulo")).date() else "realizado"


def _recusar(detalhe: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detalhe)


def _conferir_ligacoes(conn, lancamento: NovoLancamento) -> None:
    """Categoria arquivada só vale para quem já a tinha: sai das opções, não do histórico."""
    if not conn.execute("SELECT 1 FROM contas WHERE id = %s", (lancamento.conta_id,)).fetchone():
        raise _recusar("conta não encontrada")
    tipos = {}
    arquivadas = set()
    for id, tipo, arquivada in conn.execute(
        "SELECT id, tipo, arquivada_em IS NOT NULL FROM categorias WHERE id = ANY(%s)",
        (lancamento.categoria_ids,),
    ):
        tipos[id] = tipo
        if arquivada:
            arquivadas.add(id)
    ja_tinha = {
        linha[0]
        for linha in conn.execute(
            "SELECT categoria_id FROM lancamento_categorias WHERE lancamento_id = %s",
            (lancamento.id,),
        )
    }
    for categoria in lancamento.categoria_ids:
        if categoria not in tipos:
            raise _recusar("categoria não encontrada")
        if categoria in arquivadas and categoria not in ja_tinha:
            raise _recusar("categoria arquivada")
        if tipos[categoria] != lancamento.tipo:
            raise _recusar(f"categoria de {tipos[categoria]} num lançamento de {lancamento.tipo}")


def _gravar_tags(conn, id: UUID, nomes: list[str], usuario: str) -> None:
    """Acha cada tag pelo nome (sem distinguir maiúsculas) ou a cria. Tag arquivada só vale para
    quem já a tinha."""
    existentes = {
        nome.casefold(): (tag, arquivada)
        for tag, nome, arquivada in conn.execute(
            "SELECT id, nome, arquivada_em IS NOT NULL FROM tags"
        )
    }
    ja_tinha = {
        linha[0]
        for linha in conn.execute(
            "SELECT tag_id FROM lancamento_tags WHERE lancamento_id = %s", (id,)
        )
    }
    ids = []
    for nome in nomes:
        if nome.casefold() in existentes:
            tag, arquivada = existentes[nome.casefold()]
            if arquivada and tag not in ja_tinha:
                raise _recusar(f"tag arquivada: {nome}")
        else:
            tag = uuid4()
            conn.execute(
                "INSERT INTO tags (id, nome, criado_por) VALUES (%s, %s, %s)", (tag, nome, usuario)
            )
        ids.append(tag)
    conn.execute("DELETE FROM lancamento_tags WHERE lancamento_id = %s", (id,))
    for tag in ids:
        conn.execute(
            "INSERT INTO lancamento_tags (lancamento_id, tag_id) VALUES (%s, %s)", (id, tag)
        )


def _gravar_categorias(conn, id: UUID, categorias: list[UUID]) -> None:
    conn.execute("DELETE FROM lancamento_categorias WHERE lancamento_id = %s", (id,))
    for categoria in categorias:
        conn.execute(
            "INSERT INTO lancamento_categorias (lancamento_id, categoria_id) VALUES (%s, %s)",
            (id, categoria),
        )


@router.post(
    "/lancamentos", status_code=201, response_model=Lancamento, operation_id="criar_lancamento"
)
def criar_lancamento(
    novo: NovoLancamento, usuario: UsuarioLogado, request: Request, response: Response
) -> Lancamento:
    """Reenviar o mesmo id (a fila repete) devolve o que já está gravado, com 200."""
    with conectar(_url(request)) as conn:
        _conferir_ligacoes(conn, novo)
        gravados = conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, descricao,"
            " conta_id, criado_por, alterado_por) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (id) DO NOTHING",
            (
                novo.id,
                novo.tipo,
                novo.situacao or _situacao_pela_data(novo.data),
                novo.valor_centavos,
                novo.data,
                novo.descricao,
                novo.conta_id,
                usuario,
                usuario,
            ),
        ).rowcount
        if gravados:
            _gravar_categorias(conn, novo.id, novo.categoria_ids)
            _gravar_tags(conn, novo.id, novo.tags, usuario)
        else:
            response.status_code = 200
        return _todos(conn, novo.id)[0]


def _todos(conn, id: UUID | None = None) -> list[Lancamento]:
    filtro, parametros = ("WHERE id = %s", (id,)) if id else ("", ())
    linhas = conn.execute(
        f"SELECT {_COLUNAS} FROM lancamentos {filtro} ORDER BY data DESC, criado_em DESC, id",
        parametros,
    ).fetchall()
    categorias: dict[UUID, list[UUID]] = {}
    for lancamento_id, categoria_id in conn.execute(
        "SELECT lancamento_id, categoria_id FROM lancamento_categorias"
        f" {'WHERE lancamento_id = %s' if id else ''} ORDER BY categoria_id",
        parametros,
    ):
        categorias.setdefault(lancamento_id, []).append(categoria_id)
    tags: dict[UUID, list[str]] = {}
    for lancamento_id, nome in conn.execute(
        "SELECT lt.lancamento_id, t.nome FROM lancamento_tags lt JOIN tags t ON t.id = lt.tag_id"
        f" {'WHERE lt.lancamento_id = %s' if id else ''} ORDER BY t.nome",
        parametros,
    ):
        tags.setdefault(lancamento_id, []).append(nome)
    return [
        Lancamento(
            id=l[0],
            tipo=l[1],
            situacao=l[2],
            valor_centavos=l[3],
            data=l[4],
            descricao=l[5],
            conta_id=l[6],
            categoria_ids=categorias.get(l[0], []),
            tags=tags.get(l[0], []),
            criado_por=l[7],
            criado_em=l[8],
            alterado_por=l[9],
            alterado_em=l[10],
        )
        for l in linhas
    ]


@router.get("/lancamentos", response_model=list[Lancamento], operation_id="listar_lancamentos")
def listar_lancamentos(usuario: UsuarioLogado, request: Request) -> list[Lancamento]:
    with conectar(_url(request)) as conn:
        return _todos(conn)


@router.put("/lancamentos/{id}", response_model=Lancamento, operation_id="editar_lancamento")
def editar_lancamento(
    id: UUID, editado: NovoLancamento, usuario: UsuarioLogado, request: Request
) -> Lancamento:
    if editado.id != id:
        raise _recusar("o id do corpo difere do id da URL")
    with conectar(_url(request)) as conn:
        _conferir_ligacoes(conn, editado)
        atual = conn.execute(
            "SELECT data, situacao FROM lancamentos WHERE id = %s", (id,)
        ).fetchone()
        if not atual:
            raise HTTPException(status_code=404, detail="lançamento não encontrado")
        data_atual, situacao_atual = atual
        # Sem situação no pedido, só mudar a data refaz a inferência; senão a atual fica.
        if editado.situacao:
            situacao = editado.situacao
        elif editado.data != data_atual:
            situacao = _situacao_pela_data(editado.data)
        else:
            situacao = situacao_atual
        conn.execute(
            "UPDATE lancamentos SET tipo = %s, situacao = %s, valor_centavos = %s, data = %s,"
            " descricao = %s, conta_id = %s, alterado_por = %s, alterado_em = now()"
            " WHERE id = %s",
            (
                editado.tipo,
                situacao,
                editado.valor_centavos,
                editado.data,
                editado.descricao,
                editado.conta_id,
                usuario,
                id,
            ),
        )
        _gravar_categorias(conn, id, editado.categoria_ids)
        _gravar_tags(conn, id, editado.tags, usuario)
        return _todos(conn, id)[0]


@router.delete("/lancamentos/{id}", status_code=204, operation_id="excluir_lancamento")
def excluir_lancamento(id: UUID, usuario: UsuarioLogado, request: Request) -> Response:
    """Idempotente: excluir o que já não existe também dá 204."""
    with conectar(_url(request)) as conn:
        conn.execute("DELETE FROM lancamento_categorias WHERE lancamento_id = %s", (id,))
        conn.execute("DELETE FROM lancamento_tags WHERE lancamento_id = %s", (id,))
        conn.execute("DELETE FROM lancamentos WHERE id = %s", (id,))
    return Response(status_code=204)
