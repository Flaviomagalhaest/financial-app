"""Contas, categorias e lançamentos simples. Sem chave estrangeira nem trigger (subconjunto do
DSQL, ADR 0009): a API confere as ligações. O id do lançamento nasce no aparelho."""

from datetime import date, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from app.banco import conectar, em_transacao
from app.config import valores_iniciais
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
    # Previsto cuja data já passou sem confirmação; continua previsto (e contando) até confirmar.
    atrasado: bool
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
    em_transacao(
        _url(request),
        lambda conn: conn.execute(
            "INSERT INTO contas (id, nome, tipo, criado_por) VALUES (%s, %s, %s, %s)",
            (id, nova.nome, nova.tipo, usuario),
        ),
    )
    return Conta(id=id, **nova.model_dump())


class ContaComSaldo(Conta):
    # Só o realizado mexe no saldo; o previsto entra na projeção (ADR 0004).
    saldo_centavos: int


@router.get("/contas", response_model=list[ContaComSaldo], operation_id="listar_contas")
def listar_contas(usuario: UsuarioLogado, request: Request) -> list[ContaComSaldo]:
    with conectar(_url(request)) as conn:
        linhas = conn.execute(
            "SELECT c.id, c.nome, c.tipo, COALESCE(SUM(CASE l.tipo WHEN 'receita'"
            " THEN l.valor_centavos ELSE -l.valor_centavos END), 0)"
            " FROM contas c LEFT JOIN lancamentos l"
            " ON l.conta_id = c.id AND l.situacao = 'realizado'"
            " GROUP BY c.id, c.nome, c.tipo ORDER BY c.nome, c.id"
        ).fetchall()
    return [ContaComSaldo(id=i, nome=n, tipo=t, saldo_centavos=s) for i, n, t, s in linhas]


@router.post(
    "/categorias", status_code=201, response_model=Categoria, operation_id="criar_categoria"
)
def criar_categoria(nova: NovaCategoria, usuario: UsuarioLogado, request: Request) -> Categoria:
    id = uuid4()
    em_transacao(
        _url(request),
        lambda conn: conn.execute(
            "INSERT INTO categorias (id, nome, tipo, criado_por) VALUES (%s, %s, %s, %s)",
            (id, nova.nome, nova.tipo, usuario),
        ),
    )
    return Categoria(id=id, **nova.model_dump())


@router.get("/categorias", response_model=list[Categoria], operation_id="listar_categorias")
def listar_categorias(usuario: UsuarioLogado, request: Request) -> list[Categoria]:
    with conectar(_url(request)) as conn:
        linhas = conn.execute("SELECT id, nome, tipo FROM categorias ORDER BY nome, id").fetchall()
    return [Categoria(id=i, nome=n, tipo=t) for i, n, t in linhas]


def hoje() -> date:
    """O dia do casal é o de São Paulo, qualquer que seja o fuso do servidor."""
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date()


def _situacao_pela_data(dia: date) -> str:
    return "previsto" if dia > hoje() else "realizado"


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

    def gravar(conn) -> Lancamento:
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
        response.status_code = 201 if gravados else 200
        return _um(conn, novo.id)

    return em_transacao(_url(request), gravar)


def _todos(
    conn, filtro: str = "", parametros: tuple = (), ordem: str = "data DESC, criado_em DESC, id"
) -> list[Lancamento]:
    linhas = conn.execute(
        f"SELECT {_COLUNAS} FROM lancamentos {filtro} ORDER BY {ordem}", parametros
    ).fetchall()
    # Com filtro, só as categorias dos lançamentos lidos.
    ids = [l[0] for l in linhas]
    categorias: dict[UUID, list[UUID]] = {}
    for lancamento_id, categoria_id in conn.execute(
        "SELECT lancamento_id, categoria_id FROM lancamento_categorias"
        f" {'WHERE lancamento_id = ANY(%s)' if filtro else ''} ORDER BY categoria_id",
        (ids,) if filtro else (),
    ):
        categorias.setdefault(lancamento_id, []).append(categoria_id)
    dia = hoje()
    return [
        Lancamento(
            id=l[0],
            tipo=l[1],
            situacao=l[2],
            atrasado=l[2] == "previsto" and l[4] < dia,
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


def _um(conn, id: UUID) -> Lancamento:
    return _todos(conn, "WHERE id = %s", (id,))[0]


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

    def gravar(conn) -> Lancamento:
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
        return _um(conn, id)

    return em_transacao(_url(request), gravar)


class ContasDaSemana(BaseModel):
    """Previstos a confirmar: os atrasados e os dos próximos dias, do mais antigo ao mais novo."""

    lancamentos: list[Lancamento]


@router.get("/contas-da-semana", response_model=ContasDaSemana, operation_id="contas_da_semana")
def contas_da_semana(usuario: UsuarioLogado, request: Request) -> ContasDaSemana:
    ate = hoje() + timedelta(days=valores_iniciais()["contasDaSemanaDias"])
    with conectar(_url(request)) as conn:
        lancamentos = _todos(
            conn,
            "WHERE situacao = 'previsto' AND data <= %s",
            (ate,),
            ordem="data, criado_em, id",
        )
    return ContasDaSemana(lancamentos=lancamentos)


class Confirmacao(BaseModel):
    """O que de fato aconteceu; campo ausente fica como estava no previsto."""

    valor_centavos: int | None = Field(default=None, gt=0)
    data: date | None = None
    conta_id: UUID | None = None


@router.post(
    "/lancamentos/{id}/confirmar", response_model=Lancamento, operation_id="confirmar_lancamento"
)
def confirmar_lancamento(
    id: UUID, confirmacao: Confirmacao, usuario: UsuarioLogado, request: Request
) -> Lancamento:
    """Confirmar de novo (a fila reenviou, a outra pessoa confirmou antes) devolve o gravado."""

    def gravar(conn) -> Lancamento:
        atual = conn.execute("SELECT situacao FROM lancamentos WHERE id = %s", (id,)).fetchone()
        if not atual:
            raise HTTPException(status_code=404, detail="lançamento não encontrado")
        if atual[0] == "realizado":
            return _um(conn, id)
        if (
            confirmacao.conta_id
            and not conn.execute(
                "SELECT 1 FROM contas WHERE id = %s", (confirmacao.conta_id,)
            ).fetchone()
        ):
            raise _recusar("conta não encontrada")
        conn.execute(
            "UPDATE lancamentos SET situacao = 'realizado',"
            " valor_centavos = COALESCE(%s, valor_centavos), data = COALESCE(%s, data),"
            " conta_id = COALESCE(%s, conta_id), alterado_por = %s, alterado_em = now()"
            " WHERE id = %s",
            (confirmacao.valor_centavos, confirmacao.data, confirmacao.conta_id, usuario, id),
        )
        return _um(conn, id)

    return em_transacao(_url(request), gravar)


@router.delete("/lancamentos/{id}", status_code=204, operation_id="excluir_lancamento")
def excluir_lancamento(id: UUID, usuario: UsuarioLogado, request: Request) -> Response:
    """Idempotente: excluir o que já não existe também dá 204."""

    def excluir(conn) -> None:
        conn.execute("DELETE FROM lancamento_categorias WHERE lancamento_id = %s", (id,))
        conn.execute("DELETE FROM lancamentos WHERE id = %s", (id,))

    em_transacao(_url(request), excluir)
    return Response(status_code=204)
