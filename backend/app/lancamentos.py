"""Contas, categorias e lançamentos simples. Sem chave estrangeira nem trigger (subconjunto do
DSQL, ADR 0009): a API confere as ligações. O id do lançamento nasce no aparelho."""

from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator, model_validator

from app.banco import conectar
from app.login import UsuarioLogado

router = APIRouter(prefix="/api")


class NovaConta(BaseModel):
    nome: str = Field(min_length=1)
    tipo: Literal["corrente", "poupanca", "carteira"]
    # Saldo de abertura: o valor da conta na data; os dois vêm juntos ou nenhum.
    saldo_abertura_centavos: int | None = None
    data_abertura: date | None = None

    @model_validator(mode="after")
    def _abertura_completa(self):
        if (self.saldo_abertura_centavos is None) != (self.data_abertura is None):
            raise ValueError("saldo de abertura e data de abertura vêm juntos")
        return self


class EdicaoDeConta(NovaConta):
    arquivada: bool = False


class Conta(NovaConta):
    id: UUID
    saldo_centavos: int
    arquivada: bool


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


# Saldo = abertura + realizados (lançamentos e transferências) depois da data de abertura (sem abertura, todos, a partir de zero).
# O que veio antes (ou no dia) da abertura já está no valor informado e só serve às estatísticas.
_SALDO = """
    SELECT c.id, c.nome, c.tipo, c.saldo_abertura_centavos, c.data_abertura,
           c.arquivada_em IS NOT NULL,
           COALESCE(c.saldo_abertura_centavos, 0) + COALESCE((
               SELECT SUM(CASE l.tipo WHEN 'receita' THEN l.valor_centavos
                                      ELSE -l.valor_centavos END)
               FROM lancamentos l
               WHERE l.conta_id = c.id AND l.situacao = 'realizado'
                 AND (c.data_abertura IS NULL OR l.data > c.data_abertura)
           ), 0) + COALESCE((
               SELECT SUM(CASE WHEN t.conta_destino_id = c.id THEN t.valor_centavos
                               ELSE -t.valor_centavos END)
               FROM transferencias t
               WHERE c.id IN (t.conta_origem_id, t.conta_destino_id) AND t.situacao = 'realizado'
                 AND (c.data_abertura IS NULL OR t.data > c.data_abertura)
           ), 0)::bigint
    FROM contas c
"""


def _conta(linha) -> Conta:
    id, nome, tipo, abertura, data_abertura, arquivada, saldo = linha
    return Conta(
        id=id,
        nome=nome,
        tipo=tipo,
        saldo_abertura_centavos=abertura,
        data_abertura=data_abertura,
        arquivada=arquivada,
        saldo_centavos=saldo,
    )


@router.post("/contas", status_code=201, response_model=Conta, operation_id="criar_conta")
def criar_conta(nova: NovaConta, usuario: UsuarioLogado, request: Request) -> Conta:
    id = uuid4()
    with conectar(_url(request)) as conn:
        conn.execute(
            "INSERT INTO contas (id, nome, tipo, saldo_abertura_centavos, data_abertura,"
            " criado_por) VALUES (%s, %s, %s, %s, %s, %s)",
            (id, nova.nome, nova.tipo, nova.saldo_abertura_centavos, nova.data_abertura, usuario),
        )
        return _conta(conn.execute(_SALDO + "WHERE c.id = %s", (id,)).fetchone())


@router.put("/contas/{id}", response_model=Conta, operation_id="editar_conta")
def editar_conta(
    id: UUID, editada: EdicaoDeConta, usuario: UsuarioLogado, request: Request
) -> Conta:
    """Arquivar tira a conta das opções e mantém o histórico; desarquivar a devolve."""
    with conectar(_url(request)) as conn:
        atual = conn.execute("SELECT arquivada_em FROM contas WHERE id = %s", (id,)).fetchone()
        if not atual:
            raise HTTPException(status_code=404, detail="conta não encontrada")
        # Reenviar arquivada=true mantém a data em que foi arquivada.
        arquivada_em = (atual[0] or datetime.now(UTC)) if editada.arquivada else None
        conn.execute(
            "UPDATE contas SET nome = %s, tipo = %s, saldo_abertura_centavos = %s,"
            " data_abertura = %s, arquivada_em = %s WHERE id = %s",
            (
                editada.nome,
                editada.tipo,
                editada.saldo_abertura_centavos,
                editada.data_abertura,
                arquivada_em,
                id,
            ),
        )
        return _conta(conn.execute(_SALDO + "WHERE c.id = %s", (id,)).fetchone())


@router.get("/contas", response_model=list[Conta], operation_id="listar_contas")
def listar_contas(
    usuario: UsuarioLogado, request: Request, arquivadas: bool = False
) -> list[Conta]:
    """As arquivadas só vêm com `arquivadas=true`."""
    filtro = "" if arquivadas else "WHERE c.arquivada_em IS NULL "
    with conectar(_url(request)) as conn:
        linhas = conn.execute(_SALDO + filtro + "ORDER BY c.nome, c.id").fetchall()
    return [_conta(l) for l in linhas]


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


def _conferir_conta(conn, id: UUID, ja_ligada: bool = False) -> None:
    """A conta existe e, arquivada, só segue com quem já estava nela (o histórico se edita)."""
    conta = conn.execute("SELECT arquivada_em FROM contas WHERE id = %s", (id,)).fetchone()
    if not conta:
        raise _recusar("conta não encontrada")
    if conta[0] and not ja_ligada:
        raise _recusar("conta arquivada")


def _conferir_ligacoes(conn, lancamento: NovoLancamento, conta_atual: UUID | None = None) -> None:
    _conferir_conta(conn, lancamento.conta_id, ja_ligada=lancamento.conta_id == conta_atual)
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
        atual = conn.execute(
            "SELECT data, situacao, conta_id FROM lancamentos WHERE id = %s", (id,)
        ).fetchone()
        if not atual:
            raise HTTPException(status_code=404, detail="lançamento não encontrado")
        data_atual, situacao_atual, conta_atual = atual
        _conferir_ligacoes(conn, editado, conta_atual)
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
