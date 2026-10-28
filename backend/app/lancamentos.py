"""Contas, categorias e lançamentos simples. Sem chave estrangeira nem trigger (subconjunto do
DSQL, ADR 0009): a API confere as ligações. O id do lançamento nasce no aparelho."""

from datetime import date, datetime
from typing import Annotated, Literal
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


@router.get("/categorias", response_model=list[Categoria], operation_id="listar_categorias")
def listar_categorias(usuario: UsuarioLogado, request: Request) -> list[Categoria]:
    with conectar(_url(request)) as conn:
        linhas = conn.execute("SELECT id, nome, tipo FROM categorias ORDER BY nome, id").fetchall()
    return [Categoria(id=i, nome=n, tipo=t) for i, n, t in linhas]


def _situacao_pela_data(dia: date) -> str:
    return "previsto" if dia > datetime.now(ZoneInfo("America/Sao_Paulo")).date() else "realizado"


def _recusar(detalhe: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detalhe)


def _conferir_ligacoes(conn, lancamento: NovoLancamento) -> None:
    if not conn.execute("SELECT 1 FROM contas WHERE id = %s", (lancamento.conta_id,)).fetchone():
        raise _recusar("conta não encontrada")
    tipos = {
        id: tipo
        for id, tipo in conn.execute(
            "SELECT id, tipo FROM categorias WHERE id = ANY(%s)", (lancamento.categoria_ids,)
        )
    }
    for categoria in lancamento.categoria_ids:
        if categoria not in tipos:
            raise _recusar("categoria não encontrada")
        if tipos[categoria] != lancamento.tipo:
            raise _recusar(f"categoria de {tipos[categoria]} num lançamento de {lancamento.tipo}")


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
        return _todos(conn, id)[0]


@router.delete("/lancamentos/{id}", status_code=204, operation_id="excluir_lancamento")
def excluir_lancamento(id: UUID, usuario: UsuarioLogado, request: Request) -> Response:
    """Idempotente: excluir o que já não existe também dá 204."""
    with conectar(_url(request)) as conn:
        conn.execute("DELETE FROM lancamento_categorias WHERE lancamento_id = %s", (id,))
        conn.execute("DELETE FROM lancamentos WHERE id = %s", (id,))
    return Response(status_code=204)


LIMITE_DO_LOTE = 100


class AcaoCriar(BaseModel):
    acao: Literal["criar"]
    lancamento: NovoLancamento


class AcaoEditar(BaseModel):
    acao: Literal["editar"]
    lancamento: NovoLancamento


class AcaoExcluir(BaseModel):
    acao: Literal["excluir"]
    id: UUID


class Lote(BaseModel):
    acoes: list[Annotated[AcaoCriar | AcaoEditar | AcaoExcluir, Field(discriminator="acao")]] = (
        Field(min_length=1, max_length=LIMITE_DO_LOTE)
    )


class Resultado(BaseModel):
    """`recusada` traz o motivo para mostrar; `descartada` é a edição de algo já excluído; o
    `conflito` (mesmo campo mudado pelo outro lado, ADR 0011) chega com o ticket 34."""

    resultado: Literal["aceita", "conflito", "recusada", "descartada"]
    motivo: str | None = None
    lancamento: Lancamento | None = None


class ResultadoDoLote(BaseModel):
    resultados: list[Resultado]


def _aplicar(acao, usuario: str, request: Request) -> Resultado:
    """As mesmas regras das rotas de um lançamento só; a recusa de uma não para as outras."""
    try:
        return _aplicar_rota(acao, usuario, request)
    except HTTPException as erro:
        if erro.status_code == 404:
            return Resultado(resultado="descartada", motivo="lançamento excluído")
        if erro.status_code == 422:
            return Resultado(resultado="recusada", motivo=erro.detail)
        raise


def _aplicar_rota(acao, usuario: str, request: Request) -> Resultado:
    match acao:
        case AcaoCriar(lancamento=novo):
            criado = criar_lancamento(novo, usuario, request, Response())
            return Resultado(resultado="aceita", lancamento=criado)
        case AcaoEditar(lancamento=editado):
            return Resultado(
                resultado="aceita",
                lancamento=editar_lancamento(editado.id, editado, usuario, request),
            )
        case AcaoExcluir(id=id):
            excluir_lancamento(id, usuario, request)
            return Resultado(resultado="aceita")


@router.post("/lancamentos/lote", response_model=ResultadoDoLote, operation_id="enviar_lote")
def enviar_lote(lote: Lote, usuario: UsuarioLogado, request: Request) -> ResultadoDoLote:
    """A fila do aparelho: as ações na ordem, cada uma na sua transação, um resultado por ação."""
    return ResultadoDoLote(resultados=[_aplicar(a, usuario, request) for a in lote.acoes])
