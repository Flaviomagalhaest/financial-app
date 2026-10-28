"""Contas, categorias e lançamentos simples. Sem chave estrangeira nem trigger (subconjunto do
DSQL, ADR 0009): a API confere as ligações. O id do lançamento nasce no aparelho."""

from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator, model_validator

from app.banco import conectar, em_transacao
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
    # Sem o campo, a conta fica como está: renomear não desarquiva.
    arquivada: bool | None = None


class Conta(NovaConta):
    id: UUID
    saldo_centavos: int
    arquivada: bool


class NovaCategoria(BaseModel):
    nome: str = Field(min_length=1)
    tipo: Literal["despesa", "receita", "transferencia"]


class Categoria(NovaCategoria):
    id: UUID
    arquivada: bool = False


class AlteracaoDeCategoria(BaseModel):
    """Só o nome e o arquivamento mudam; o tipo é fixo porque os lançamentos dependem dele."""

    nome: str | None = Field(default=None, min_length=1, pattern=r"\S")
    arquivada: bool | None = None

    @field_validator("nome")
    @classmethod
    def _sem_espacos_nas_pontas(cls, nome: str | None) -> str | None:
        return nome.strip() if nome else nome


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


def url_do_banco(request: Request) -> str | None:
    return request.app.state.url


# Saldo = abertura + realizados (lançamentos e transferências) depois da data de abertura
# (sem abertura, todos, a partir de zero). O que veio antes (ou no dia) da abertura já está no
# valor informado e só serve às estatísticas.
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

    def gravar(conn) -> Conta:
        conn.execute(
            "INSERT INTO contas (id, nome, tipo, saldo_abertura_centavos, data_abertura,"
            " criado_por) VALUES (%s, %s, %s, %s, %s, %s)",
            (id, nova.nome, nova.tipo, nova.saldo_abertura_centavos, nova.data_abertura, usuario),
        )
        return _conta(conn.execute(_SALDO + "WHERE c.id = %s", (id,)).fetchone())

    return em_transacao(url_do_banco(request), gravar)


@router.put("/contas/{id}", response_model=Conta, operation_id="editar_conta")
def editar_conta(
    id: UUID, editada: EdicaoDeConta, usuario: UsuarioLogado, request: Request
) -> Conta:
    """Arquivar tira a conta das opções e mantém o histórico; desarquivar a devolve."""

    def gravar(conn) -> Conta:
        atual = conn.execute("SELECT arquivada_em FROM contas WHERE id = %s", (id,)).fetchone()
        if not atual:
            raise HTTPException(status_code=404, detail="conta não encontrada")
        # Reenviar arquivada=true mantém a data em que foi arquivada.
        arquivada = editada.arquivada if editada.arquivada is not None else bool(atual[0])
        arquivada_em = (atual[0] or datetime.now(UTC)) if arquivada else None
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

    return em_transacao(url_do_banco(request), gravar)


@router.get("/contas", response_model=list[Conta], operation_id="listar_contas")
def listar_contas(
    usuario: UsuarioLogado, request: Request, arquivadas: bool = False
) -> list[Conta]:
    """As arquivadas só vêm com `arquivadas=true`."""
    filtro = "" if arquivadas else "WHERE c.arquivada_em IS NULL "
    with conectar(url_do_banco(request)) as conn:
        linhas = conn.execute(_SALDO + filtro + "ORDER BY c.nome, c.id").fetchall()
    return [_conta(linha) for linha in linhas]


@router.post(
    "/categorias", status_code=201, response_model=Categoria, operation_id="criar_categoria"
)
def criar_categoria(nova: NovaCategoria, usuario: UsuarioLogado, request: Request) -> Categoria:
    id = uuid4()
    em_transacao(
        url_do_banco(request),
        lambda conn: conn.execute(
            "INSERT INTO categorias (id, nome, tipo, criado_por) VALUES (%s, %s, %s, %s)",
            (id, nova.nome, nova.tipo, usuario),
        ),
    )
    return Categoria(id=id, **nova.model_dump())


@router.get("/categorias", response_model=list[Categoria], operation_id="listar_categorias")
def listar_categorias(usuario: UsuarioLogado, request: Request) -> list[Categoria]:
    with conectar(url_do_banco(request)) as conn:
        linhas = conn.execute(
            "SELECT id, nome, tipo, arquivada FROM categorias ORDER BY nome, id"
        ).fetchall()
    return [Categoria(id=i, nome=n, tipo=t, arquivada=a) for i, n, t, a in linhas]


@router.patch("/categorias/{id}", response_model=Categoria, operation_id="alterar_categoria")
def alterar_categoria(
    id: UUID, alteracao: AlteracaoDeCategoria, usuario: UsuarioLogado, request: Request
) -> Categoria:
    """Renomear e arquivar não mexem nos lançamentos: eles apontam para o id da categoria."""
    linha = em_transacao(
        url_do_banco(request),
        lambda conn: conn.execute(
            "UPDATE categorias SET nome = COALESCE(%s, nome), arquivada = COALESCE(%s, arquivada)"
            " WHERE id = %s RETURNING id, nome, tipo, arquivada",
            (alteracao.nome, alteracao.arquivada, id),
        ).fetchone(),
    )
    if not linha:
        raise HTTPException(status_code=404, detail="categoria não encontrada")
    return Categoria(id=linha[0], nome=linha[1], tipo=linha[2], arquivada=linha[3])


def situacao_pela_data(dia: date) -> str:
    return "previsto" if dia > datetime.now(ZoneInfo("America/Sao_Paulo")).date() else "realizado"


def recusar(detalhe: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detalhe)


def conferir_conta(conn, id: UUID, ja_ligada: bool = False) -> None:
    """A conta existe e, arquivada, só segue com quem já estava nela (o histórico se edita)."""
    conta = conn.execute("SELECT arquivada_em FROM contas WHERE id = %s", (id,)).fetchone()
    if not conta:
        raise recusar("conta não encontrada")
    if conta[0] and not ja_ligada:
        raise recusar("conta arquivada")


def _conferir_ligacoes(
    conn,
    lancamento: NovoLancamento,
    conta_atual: UUID | None = None,
    categorias_atuais: frozenset[UUID] = frozenset(),
) -> None:
    """Conta e categoria arquivadas só valem num lançamento que já as tinha."""
    conferir_conta(conn, lancamento.conta_id, ja_ligada=lancamento.conta_id == conta_atual)
    tipos = {}
    arquivadas = set()
    for id, tipo, arquivada in conn.execute(
        "SELECT id, tipo, arquivada FROM categorias WHERE id = ANY(%s)", (lancamento.categoria_ids,)
    ):
        tipos[id] = tipo
        if arquivada:
            arquivadas.add(id)
    for categoria in lancamento.categoria_ids:
        if categoria not in tipos:
            raise recusar("categoria não encontrada")
        if tipos[categoria] != lancamento.tipo:
            raise recusar(f"categoria de {tipos[categoria]} num lançamento de {lancamento.tipo}")
        if categoria in arquivadas and categoria not in categorias_atuais:
            raise recusar("categoria arquivada")


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
                raise recusar(f"tag arquivada: {nome}")
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

    def gravar(conn) -> Lancamento:
        # Reenvio de um lançamento já gravado não falha porque a categoria foi arquivada depois.
        ja_ligadas = frozenset(
            categoria
            for (categoria,) in conn.execute(
                "SELECT categoria_id FROM lancamento_categorias WHERE lancamento_id = %s",
                (novo.id,),
            )
        )
        _conferir_ligacoes(conn, novo, categorias_atuais=ja_ligadas)
        gravados = conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, descricao,"
            " conta_id, criado_por, alterado_por) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (id) DO NOTHING",
            (
                novo.id,
                novo.tipo,
                novo.situacao or situacao_pela_data(novo.data),
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
        response.status_code = 201 if gravados else 200
        return _todos(conn, novo.id)[0]

    return em_transacao(url_do_banco(request), gravar)


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
    with conectar(url_do_banco(request)) as conn:
        return _todos(conn)


@router.put("/lancamentos/{id}", response_model=Lancamento, operation_id="editar_lancamento")
def editar_lancamento(
    id: UUID, editado: NovoLancamento, usuario: UsuarioLogado, request: Request
) -> Lancamento:
    if editado.id != id:
        raise recusar("o id do corpo difere do id da URL")

    def gravar(conn) -> Lancamento:
        categorias_atuais = frozenset(
            categoria
            for (categoria,) in conn.execute(
                "SELECT categoria_id FROM lancamento_categorias WHERE lancamento_id = %s", (id,)
            )
        )
        atual = conn.execute(
            "SELECT data, situacao, conta_id FROM lancamentos WHERE id = %s", (id,)
        ).fetchone()
        if not atual:
            raise HTTPException(status_code=404, detail="lançamento não encontrado")
        data_atual, situacao_atual, conta_atual = atual
        _conferir_ligacoes(conn, editado, conta_atual, categorias_atuais)
        # Sem situação no pedido, só mudar a data refaz a inferência; senão a atual fica.
        if editado.situacao:
            situacao = editado.situacao
        elif editado.data != data_atual:
            situacao = situacao_pela_data(editado.data)
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

    return em_transacao(url_do_banco(request), gravar)


@router.delete("/lancamentos/{id}", status_code=204, operation_id="excluir_lancamento")
def excluir_lancamento(id: UUID, usuario: UsuarioLogado, request: Request) -> Response:
    """Idempotente: excluir o que já não existe também dá 204."""

    def excluir(conn) -> None:
        conn.execute("DELETE FROM lancamento_categorias WHERE lancamento_id = %s", (id,))
        conn.execute("DELETE FROM lancamento_tags WHERE lancamento_id = %s", (id,))
        conn.execute("DELETE FROM lancamentos WHERE id = %s", (id,))

    em_transacao(url_do_banco(request), excluir)
    return Response(status_code=204)
