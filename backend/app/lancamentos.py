"""Contas, categorias e lançamentos simples. Sem chave estrangeira nem trigger (subconjunto do
DSQL, ADR 0009): a API confere as ligações. O id do lançamento nasce no aparelho."""

import logging
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal, get_args
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import psycopg
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from app import faturas
from app.banco import conectar, em_transacao
from app.config import valores_iniciais
from app.login import UsuarioLogado
from app.pessoas import configuradas

router = APIRouter(prefix="/api")
log = logging.getLogger(__name__)


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


def _tags_limpas(nomes: list[str] | None) -> list[str] | None:
    if nomes is None:
        return None
    limpos = [nome.strip() for nome in nomes]
    if "" in limpos:
        raise ValueError("tag sem nome")
    return list({nome.casefold(): nome for nome in limpos}.values())


def _sem_repetidas(ids: list[UUID] | None) -> list[UUID] | None:
    if ids is not None and len(set(ids)) != len(ids):
        raise ValueError("categoria repetida")
    return ids


def _primeiro_dia(mes: date | None) -> date | None:
    return mes and faturas.mes_de(mes)


class DadosDoLancamento(BaseModel):
    id: UUID
    tipo: Literal["despesa", "receita"]
    valor_centavos: int = Field(gt=0)
    data: date
    descricao: str = ""
    # A conta ou o cartão; no cartão, `data` é a data da compra.
    conta_id: UUID
    categoria_ids: list[UUID] = Field(min_length=1)
    # Sem situação, a data decide: futura nasce prevista, de hoje ou do passado, realizada.
    situacao: Literal["previsto", "realizado"] | None = None
    # Pelo nome: a tag que ainda não existe nasce junto com o lançamento.
    tags: list[str] = []
    # O id de uma pessoa do casal; sem ela, o lançamento é do conjunto.
    pessoa: str | None = None
    # Só no cartão: o mês da fatura, que o servidor escolhe pela data da compra e pelo
    # fechamento. Mandar o mês é trocar a fatura à mão (o banco lançou a compra com atraso).
    fatura_mes: date | None = None

    _tags = field_validator("tags")(_tags_limpas)
    _categorias = field_validator("categoria_ids")(_sem_repetidas)
    _fatura = field_validator("fatura_mes")(_primeiro_dia)


class NovoLancamento(DadosDoLancamento):
    # A hora em que a pessoa fez a ação no aparelho; sem ela, a da chegada ao servidor.
    acao_em: datetime | None = None


class Lancamento(DadosDoLancamento):
    situacao: Literal["previsto", "realizado"]
    # O mês em que o lançamento conta (planejamento, categorias, tags, resumo): o mês da fatura
    # no cartão, o da data no resto (ADR 0003). Gravado como o primeiro dia do mês.
    mes: date
    # Previsto cuja data já passou sem confirmação; continua previsto (e contando) até confirmar.
    atrasado: bool
    # Sobe a cada mudança aceita; a edição e a exclusão dizem sobre qual versão foram feitas.
    versao: int
    criado_por: str
    criado_em: datetime
    alterado_por: str
    alterado_em: datetime
    # De onde veio: "app" ou "mobills" (o importado); lançamento antigo, sem marca, é do app.
    fonte: Literal["app", "mobills"] = "app"
    # O lançamento da outra pessoa com mesmo valor, conta e tipo e data a até um dia, que já
    # estava no servidor quando este chegou, e que o casal ainda não conferiu ("Parece repetido").
    parece_repetido_de: UUID | None = None


Campo = Literal[
    "tipo",
    "situacao",
    "valor_centavos",
    "data",
    "descricao",
    "conta_id",
    "categoria_ids",
    "tags",
    "pessoa",
    "fatura_mes",
]
CAMPOS: tuple[Campo, ...] = get_args(Campo)


class AlteracaoDeLancamento(BaseModel):
    """Só os campos que a pessoa mudou, feitos sobre a `versao` que o aparelho tinha; o campo
    ausente fica como está no servidor, com o que o outro lado tiver mudado nele (ADR 0011)."""

    versao: int = Field(ge=0)
    tipo: Literal["despesa", "receita"] | None = None
    valor_centavos: int | None = Field(default=None, gt=0)
    data: date | None = None
    descricao: str | None = None
    conta_id: UUID | None = None
    categoria_ids: list[UUID] | None = Field(default=None, min_length=1)
    # Sem situação, só mudar a data refaz a inferência, se ninguém mudou a situação depois.
    situacao: Literal["previsto", "realizado"] | None = None
    tags: list[str] | None = None
    # Sem o campo, a pessoa fica; vazia, o lançamento passa a ser do conjunto.
    pessoa: str | None = None
    # Troca a fatura à mão; mudar a data ou o cartão sem ele escolhe a fatura de novo.
    fatura_mes: date | None = None
    acao_em: datetime | None = None

    _tags = field_validator("tags")(_tags_limpas)
    _categorias = field_validator("categoria_ids")(_sem_repetidas)
    _fatura = field_validator("fatura_mes")(_primeiro_dia)


class CampoEmConflito(BaseModel):
    """Um campo que o outro lado mudou depois da versão do pedido; o valor dele está no
    lançamento que acompanha o conflito."""

    campo: Campo
    alterado_por: str
    alterado_em: datetime
    # A mesma pessoa, de outro aparelho.
    por_voce: bool
    # A regra que mudou o campo (recorrência, automático; tickets 44 e 45); sem ela, uma pessoa.
    origem: str | None = None


class Conflito(BaseModel):
    """Corpo do 409: o lançamento como o servidor o tem e os campos em conflito. Na exclusão, os
    campos são os que o outro lado mudou depois."""

    motivo: str
    lancamento: Lancamento
    campos: list[CampoEmConflito]


class Exclusao(BaseModel):
    """Corpo do 410: a exclusão vence a edição (ADR 0011)."""

    motivo: str = "lançamento excluído"
    excluido_por: str
    excluido_em: datetime
    por_voce: bool


class LancamentoNaoEncontrado(Exception):
    pass


class LancamentoExcluido(Exception):
    def __init__(self, exclusao: Exclusao) -> None:
        self.exclusao = exclusao


class ConflitoDeCampos(Exception):
    def __init__(self, conflito: Conflito) -> None:
        self.conflito = conflito


# O original mais antigo de outra pessoa; some quando o casal mantém os dois ou quando um dos
# dois é excluído (a consulta só vê os não excluídos).
_REPETIDO_DE = f"""(
    SELECT o.id FROM lancamentos o
    WHERE lancamentos.repetido_mantido_em IS NULL AND o.excluido_em IS NULL
      AND lancamentos.fonte IS DISTINCT FROM 'mobills' AND o.fonte IS DISTINCT FROM 'mobills'
      AND o.id <> lancamentos.id AND o.criado_por <> lancamentos.criado_por
      AND o.valor_centavos = lancamentos.valor_centavos AND o.tipo = lancamentos.tipo
      AND o.conta_id = lancamentos.conta_id
      AND abs(o.data - lancamentos.data) <= {int(valores_iniciais()["pareceRepetidoDias"])}
      AND (o.criado_em, o.id) < (lancamentos.criado_em, lancamentos.id)
    ORDER BY o.criado_em, o.id LIMIT 1
) AS repetido_de"""

# Lançamento de antes do ticket 34 não tem versão: está como nasceu, na 1.
_VERSAO = "COALESCE(versao, 1)"
_COLUNAS = (
    "id, tipo, situacao, valor_centavos, data, descricao, conta_id,"
    f" criado_por, criado_em, alterado_por, alterado_em, {_VERSAO}, pessoa, fonte,"
    f" {_REPETIDO_DE},"
    # Gravado pela migration 0026 nos de antes; o COALESCE cobre a API antiga durante o deploy.
    " COALESCE(mes, date_trunc('month', data)::date),"
    " EXISTS (SELECT FROM cartoes WHERE cartoes.id = lancamentos.conta_id)"
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
               WHERE l.conta_id = c.id AND l.situacao = 'realizado' AND l.excluido_em IS NULL
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
            "SELECT id, nome, tipo, arquivada_em IS NOT NULL FROM categorias ORDER BY nome, id"
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
            "UPDATE categorias SET nome = COALESCE(%s, nome),"
            " arquivada_em = CASE WHEN %s::boolean IS NULL THEN arquivada_em"
            " WHEN %s::boolean THEN COALESCE(arquivada_em, now()) END"
            " WHERE id = %s RETURNING id, nome, tipo, arquivada_em IS NOT NULL",
            (alteracao.nome, alteracao.arquivada, alteracao.arquivada, id),
        ).fetchone(),
    )
    if not linha:
        raise HTTPException(status_code=404, detail="categoria não encontrada")
    return Categoria(id=linha[0], nome=linha[1], tipo=linha[2], arquivada=linha[3])


def hoje() -> date:
    """O dia do casal é o de São Paulo, qualquer que seja o fuso do servidor."""
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date()


def situacao_pela_data(dia: date) -> str:
    return "previsto" if dia > hoje() else "realizado"


def recusar(detalhe: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detalhe)


def conferir_conta(conn, id: UUID, ja_ligada: bool = False) -> None:
    """A conta existe e, arquivada, só segue com quem já estava nela (o histórico se edita)."""
    conta = conn.execute("SELECT arquivada_em FROM contas WHERE id = %s", (id,)).fetchone()
    if not conta:
        raise recusar("conta não encontrada")
    if conta[0] and not ja_ligada:
        raise recusar("conta arquivada")


def _conferir_conta_ou_cartao(conn, id: UUID, ja_ligado: bool) -> None:
    if cartao := faturas.ler_cartao(conn, id):
        if cartao.arquivado and not ja_ligado:
            raise recusar("cartão arquivado")
        return
    conferir_conta(conn, id, ja_ligada=ja_ligado)


def _conferir_ligacoes(
    conn,
    lancamento: DadosDoLancamento,
    conta_atual: UUID | None = None,
    categorias_atuais: frozenset[UUID] = frozenset(),
) -> None:
    """Conta, cartão e categoria arquivados só valem num lançamento que já os tinha."""
    pessoas = configuradas()
    if lancamento.pessoa and pessoas and lancamento.pessoa not in pessoas:
        raise recusar("pessoa não encontrada")
    _conferir_conta_ou_cartao(conn, lancamento.conta_id, lancamento.conta_id == conta_atual)
    tipos = {}
    arquivadas = set()
    for id, tipo, arquivada in conn.execute(
        "SELECT id, tipo, arquivada_em IS NOT NULL FROM categorias WHERE id = ANY(%s)",
        (lancamento.categoria_ids,),
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


def _momento(acao_em: datetime | None) -> datetime:
    """A hora da ação no aparelho; a do relógio do aparelho nunca vale mais que a do servidor."""
    agora = datetime.now(UTC)
    if acao_em is None:
        return agora
    if acao_em.tzinfo is None:
        acao_em = acao_em.replace(tzinfo=UTC)
    return min(acao_em, agora)


def registrar_mudancas(
    conn,
    id: UUID,
    campos: Iterable[str],
    versao: int,
    usuario: str,
    em: datetime,
    origem: str | None = None,
) -> None:
    """Guarda, por campo, a versão em que ele mudou por último e quem o mudou (ADR 0011)."""
    for campo in campos:
        conn.execute(
            "INSERT INTO lancamento_campos"
            " (lancamento_id, campo, versao, alterado_por, alterado_em, origem)"
            " VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (lancamento_id, campo) DO UPDATE"
            " SET versao = excluded.versao, alterado_por = excluded.alterado_por,"
            " alterado_em = excluded.alterado_em, origem = excluded.origem",
            (id, campo, versao, usuario, em, origem),
        )


def subir_versao(conn, id: UUID, de: int, atribuicoes: str, parametros: tuple) -> int:
    """Grava a mudança só se ninguém mudou o lançamento desde a leitura; senão a transação
    recomeça (`em_transacao`) e a nova leitura vê a outra mudança."""
    gravadas = conn.execute(
        f"UPDATE lancamentos SET {atribuicoes}, versao = %s WHERE id = %s AND {_VERSAO} = %s",
        (*parametros, de + 1, id, de),
    ).rowcount
    if not gravadas:
        raise psycopg.errors.SerializationFailure("o lançamento mudou durante a gravação")
    return de + 1


class _VersaoDoCampo(BaseModel):
    versao: int
    alterado_por: str
    alterado_em: datetime
    origem: str | None


def _versoes(conn, lancamento: Lancamento) -> dict[str, _VersaoDoCampo]:
    """Campo sem registro está como nasceu, na versão 1."""
    lidas = {
        campo: _VersaoDoCampo(versao=v, alterado_por=por, alterado_em=em, origem=origem)
        for campo, v, por, em, origem in conn.execute(
            "SELECT campo, versao, alterado_por, alterado_em, origem FROM lancamento_campos"
            " WHERE lancamento_id = %s",
            (lancamento.id,),
        )
    }
    nascido = _VersaoDoCampo(
        versao=1,
        alterado_por=lancamento.criado_por,
        alterado_em=lancamento.criado_em,
        origem=None,
    )
    return {campo: lidas.get(campo, nascido) for campo in CAMPOS}


def _conflito(
    motivo: str, atual: Lancamento, campos: dict[Campo, _VersaoDoCampo], usuario: str
) -> ConflitoDeCampos:
    """O conflito com o lançamento do servidor e quem mudou por último cada campo."""
    return ConflitoDeCampos(
        Conflito(
            motivo=motivo,
            lancamento=atual,
            campos=[
                CampoEmConflito(
                    campo=campo,
                    alterado_por=versao.alterado_por,
                    alterado_em=versao.alterado_em,
                    por_voce=versao.alterado_por == usuario,
                    origem=versao.origem,
                )
                for campo, versao in campos.items()
            ],
        )
    )


def _atual(conn, id: UUID, usuario: str) -> Lancamento:
    """O lançamento como está; o excluído responde com quem o excluiu."""
    linha = conn.execute(
        "SELECT excluido_por, excluido_em FROM lancamentos WHERE id = %s", (id,)
    ).fetchone()
    if not linha:
        raise LancamentoNaoEncontrado()
    por, em = linha
    if em:
        raise LancamentoExcluido(
            Exclusao(excluido_por=por, excluido_em=em, por_voce=por == usuario)
        )
    return _um(conn, id)


def _onde_conta(
    conn, lancamento: DadosDoLancamento, mantida: date | None = None
) -> tuple[date, date | None, bool]:
    """O mês em que conta, o mês da fatura (só no cartão) e se a fatura foi escolhida à mão.

    No cartão, a fatura é a pedida, a `mantida` de uma troca à mão anterior ou a que fecha
    depois da data da compra, e nasce aqui se ainda não existe; no resto, o mês da data.
    """
    cartao = faturas.ler_cartao(conn, lancamento.conta_id)
    if cartao is None:
        if lancamento.fatura_mes:
            raise recusar("fatura só em compra no cartão")
        return faturas.mes_de(lancamento.data), None, False
    if lancamento.fatura_mes:
        (fechamento,) = faturas.fechamentos(conn, cartao.titular, [lancamento.fatura_mes]).values()
        if fechamento and fechamento <= lancamento.data:
            raise recusar("a fatura escolhida fechou antes da compra")
    a_mao = lancamento.fatura_mes or mantida
    mes = a_mao or faturas.mes_da_compra(conn, cartao.titular, lancamento.data)
    faturas.garantir_fatura(conn, cartao.titular, mes)
    return mes, mes, bool(a_mao)


def _com_mudancas(atual: Lancamento, mudancas: dict) -> DadosDoLancamento:
    """O lançamento com as mudanças; a fatura só vale como troca à mão quando foi pedida."""
    return DadosDoLancamento(
        **atual.model_dump(include=set(DadosDoLancamento.model_fields))
        | mudancas
        | {"fatura_mes": mudancas.get("fatura_mes")}
    )


def _fatura_depois(
    conn, atual: Lancamento, depois: DadosDoLancamento, mudancas: dict
) -> tuple[date, bool]:
    """O mês em que conta e a marca da troca à mão de um lançamento que mudou: só a conta (ou o
    cartão), a data e a troca de fatura mexem nela, e a troca à mão fica enquanto o cartão não
    muda. A fatura que mudou entra em `mudancas`, para a versão por campo (ADR 0011)."""
    (a_mao,) = conn.execute(
        "SELECT COALESCE(fatura_a_mao, false) FROM lancamentos WHERE id = %s", (atual.id,)
    ).fetchone()
    if not {"conta_id", "data", "fatura_mes"} & mudancas.keys():
        return atual.mes, a_mao
    mantida = atual.fatura_mes if a_mao and "conta_id" not in mudancas else None
    mes, fatura_mes, a_mao = _onde_conta(conn, depois, mantida)
    if fatura_mes != atual.fatura_mes:
        mudancas["fatura_mes"] = fatura_mes
    return mes, a_mao


def _iguais(campo: Campo, pedido, gravado) -> bool:
    if campo == "categoria_ids":
        return set(pedido) == set(gravado)
    if campo == "tags":
        return {t.casefold() for t in pedido} == {t.casefold() for t in gravado}
    return pedido == gravado


def _criar(conn, novo: NovoLancamento, usuario: str) -> tuple[Lancamento, bool]:
    """Reenviar o mesmo id (a fila repete) devolve o que já está gravado, sem criar de novo."""
    # Reenvio de um lançamento já gravado não falha porque a categoria foi arquivada depois.
    ja_ligadas = frozenset(
        categoria
        for (categoria,) in conn.execute(
            "SELECT categoria_id FROM lancamento_categorias WHERE lancamento_id = %s",
            (novo.id,),
        )
    )
    _conferir_ligacoes(conn, novo, categorias_atuais=ja_ligadas)
    mes, _, a_mao = _onde_conta(conn, novo)
    momento = _momento(novo.acao_em)
    gravados = conn.execute(
        "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, descricao,"
        " conta_id, criado_por, alterado_por, versao, pessoa, criado_em, alterado_em, fonte,"
        " mes, fatura_a_mao)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s, 'app', %s, %s)"
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
            novo.pessoa,
            momento,
            momento,
            mes,
            a_mao,
        ),
    ).rowcount
    if gravados:
        _gravar_categorias(conn, novo.id, novo.categoria_ids)
        _gravar_tags(conn, novo.id, novo.tags, usuario)
    return _atual(conn, novo.id, usuario), bool(gravados)


def _editar(conn, id: UUID, alteracao: AlteracaoDeLancamento, usuario: str) -> Lancamento:
    """Aplica os campos pedidos sobre o que o servidor tem. Campo que o outro lado mudou depois
    da versão do pedido, para outro valor, recusa a mudança inteira como conflito; mudança igual
    à gravada não conta."""
    atual = _atual(conn, id, usuario)
    versoes = _versoes(conn, atual)
    pedidas = alteracao.model_dump(exclude={"versao", "acao_em"}, exclude_none=True)
    if "pessoa" in pedidas:
        pedidas["pessoa"] = pedidas["pessoa"] or None
    mudancas = {}
    conflitos: list[Campo] = []
    for campo, valor in pedidas.items():
        if _iguais(campo, valor, getattr(atual, campo)):
            continue
        if versoes[campo].versao > alteracao.versao:
            conflitos.append(campo)
        else:
            mudancas[campo] = valor
    if conflitos:
        raise _conflito(
            "o outro lado mudou os mesmos campos depois",
            atual,
            {c: versoes[c] for c in conflitos},
            usuario,
        )
    # Só mudar a data refaz a situação pela data, se ninguém mudou a situação depois.
    if (
        "data" in mudancas
        and "situacao" not in pedidas
        and versoes["situacao"].versao <= alteracao.versao
        and situacao_pela_data(mudancas["data"]) != atual.situacao
    ):
        mudancas["situacao"] = situacao_pela_data(mudancas["data"])
    if not mudancas:
        return atual
    editado = _com_mudancas(atual, mudancas)
    momento = _momento(alteracao.acao_em)
    _conferir_ligacoes(conn, editado, atual.conta_id, frozenset(atual.categoria_ids))
    mes, a_mao = _fatura_depois(conn, atual, editado, mudancas)
    versao = subir_versao(
        conn,
        id,
        atual.versao,
        "tipo = %s, situacao = %s, valor_centavos = %s, data = %s, descricao = %s,"
        " conta_id = %s, pessoa = %s, mes = %s, fatura_a_mao = %s, alterado_por = %s,"
        " alterado_em = %s",
        (
            editado.tipo,
            editado.situacao,
            editado.valor_centavos,
            editado.data,
            editado.descricao,
            editado.conta_id,
            editado.pessoa,
            mes,
            a_mao,
            usuario,
            momento,
        ),
    )
    registrar_mudancas(conn, id, mudancas, versao, usuario, momento)
    if "categoria_ids" in mudancas:
        _gravar_categorias(conn, id, editado.categoria_ids)
    if "tags" in mudancas:
        _gravar_tags(conn, id, editado.tags, usuario)
    return _um(conn, id)


def _excluir(
    conn, id: UUID, versao: int | None, usuario: str, acao_em: datetime | None = None
) -> None:
    """Marca a exclusão: sem a marca, a edição que chega depois não saberia que perdeu para
    ela. Com `versao`, excluir o que o outro lado mudou depois é conflito."""
    linha = conn.execute(
        f"SELECT {_VERSAO}, excluido_em FROM lancamentos WHERE id = %s", (id,)
    ).fetchone()
    if not linha or linha[1]:
        return
    if versao is not None and linha[0] > versao:
        atual = _um(conn, id)
        depois = {c: v for c, v in _versoes(conn, atual).items() if v.versao > versao}
        raise _conflito("alterado depois da sua versão", atual, depois, usuario)
    subir_versao(
        conn,
        id,
        linha[0],
        "excluido_em = %s, excluido_por = %s",
        (_momento(acao_em), usuario),
    )
    # Sem lixeira: "Lançar de novo" cria outro lançamento. As ligações saem para a categoria e a
    # tag não contarem como usadas por ele.
    conn.execute("DELETE FROM lancamento_categorias WHERE lancamento_id = %s", (id,))
    conn.execute("DELETE FROM lancamento_tags WHERE lancamento_id = %s", (id,))


def _na_rota[T](request: Request, trabalho: Callable[..., T]) -> T | JSONResponse:
    """Uma rota de um lançamento só: o conflito vira 409 e a exclusão que venceu, 410."""
    try:
        return em_transacao(url_do_banco(request), trabalho)
    except LancamentoNaoEncontrado:
        raise HTTPException(status_code=404, detail="lançamento não encontrado")
    except LancamentoExcluido as e:
        return JSONResponse(e.exclusao.model_dump(mode="json"), status_code=410)
    except ConflitoDeCampos as e:
        return JSONResponse(e.conflito.model_dump(mode="json"), status_code=409)


_EXCLUIDO = {410: {"model": Exclusao, "description": "O lançamento foi excluído"}}
_CONFLITO = {409: {"model": Conflito, "description": "O outro lado mudou depois"}}


@router.post(
    "/lancamentos",
    status_code=201,
    response_model=Lancamento,
    operation_id="criar_lancamento",
    responses=_EXCLUIDO,
)
def criar_lancamento(
    novo: NovoLancamento, usuario: UsuarioLogado, request: Request, response: Response
) -> Lancamento | JSONResponse:
    """Reenviar o mesmo id (a fila repete) devolve o que já está gravado, com 200."""

    def gravar(conn) -> Lancamento:
        criado, gravado = _criar(conn, novo, usuario)
        response.status_code = 201 if gravado else 200
        return criado

    return _na_rota(request, gravar)


def _todos(
    conn, filtro: str = "", parametros: tuple = (), ordem: str = "data DESC, criado_em DESC, id"
) -> list[Lancamento]:
    """Os não excluídos; `filtro` é a condição a mais, sem o WHERE."""
    linhas = conn.execute(
        f"SELECT {_COLUNAS} FROM lancamentos WHERE excluido_em IS NULL"
        f" {'AND ' + filtro if filtro else ''} ORDER BY {ordem}",
        parametros,
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
    tags: dict[UUID, list[str]] = {}
    for lancamento_id, nome in conn.execute(
        "SELECT lt.lancamento_id, t.nome FROM lancamento_tags lt JOIN tags t ON t.id = lt.tag_id"
        f" {'WHERE lt.lancamento_id = ANY(%s)' if filtro else ''} ORDER BY t.nome",
        (ids,) if filtro else (),
    ):
        tags.setdefault(lancamento_id, []).append(nome)
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
            tags=tags.get(l[0], []),
            criado_por=l[7],
            criado_em=l[8],
            alterado_por=l[9],
            alterado_em=l[10],
            versao=l[11],
            pessoa=l[12],
            fonte=l[13] or "app",
            parece_repetido_de=l[14],
            mes=l[15],
            fatura_mes=l[15] if l[16] else None,
        )
        for l in linhas
    ]


def _um(conn, id: UUID) -> Lancamento:
    return _todos(conn, "id = %s", (id,))[0]


@router.get("/lancamentos", response_model=list[Lancamento], operation_id="listar_lancamentos")
def listar_lancamentos(usuario: UsuarioLogado, request: Request) -> list[Lancamento]:
    with conectar(url_do_banco(request)) as conn:
        return _todos(conn)


@router.patch(
    "/lancamentos/{id}",
    response_model=Lancamento,
    operation_id="editar_lancamento",
    responses=_CONFLITO | _EXCLUIDO,
)
def editar_lancamento(
    id: UUID, alteracao: AlteracaoDeLancamento, usuario: UsuarioLogado, request: Request
) -> Lancamento | JSONResponse:
    """Só os campos mudados, sobre uma versão: campos diferentes se mesclam, o mesmo campo
    mudado depois pelo outro lado é 409, e o excluído é 410 (ADR 0011)."""
    return _na_rota(request, lambda conn: _editar(conn, id, alteracao, usuario))


class ContasDaSemana(BaseModel):
    """Previstos a confirmar: os atrasados e os dos próximos dias, do mais antigo ao mais novo."""

    lancamentos: list[Lancamento]


@router.get("/contas-da-semana", response_model=ContasDaSemana, operation_id="contas_da_semana")
def contas_da_semana(usuario: UsuarioLogado, request: Request) -> ContasDaSemana:
    ate = hoje() + timedelta(days=valores_iniciais()["contasDaSemanaDias"])
    with conectar(url_do_banco(request)) as conn:
        lancamentos = _todos(
            conn,
            "situacao = 'previsto' AND data <= %s",
            (ate,),
            ordem="data, criado_em, id",
        )
    return ContasDaSemana(lancamentos=lancamentos)


class Confirmacao(BaseModel):
    """O que de fato aconteceu; campo ausente fica como estava no previsto. Com `versao`, o
    ajuste num campo que o outro lado mudou depois dela é conflito, como na edição."""

    versao: int | None = Field(default=None, ge=0)
    valor_centavos: int | None = Field(default=None, gt=0)
    data: date | None = None
    conta_id: UUID | None = None
    acao_em: datetime | None = None


def _confirmar(conn, id: UUID, confirmacao: Confirmacao, usuario: str) -> Lancamento:
    atual = _atual(conn, id, usuario)
    versoes = _versoes(conn, atual)
    ajustes = {
        campo: pedido
        for campo, pedido in confirmacao.model_dump(
            exclude={"versao", "acao_em"}, exclude_none=True
        ).items()
        if pedido != getattr(atual, campo)
    }
    if atual.situacao == "realizado":
        if not ajustes:
            return atual
        # Quem confirmou antes é o outro lado de todos os campos em conflito.
        quem_confirmou = dict.fromkeys(ajustes, versoes["situacao"])
        raise _conflito("já confirmado com outros valores", atual, quem_confirmou, usuario)
    if confirmacao.versao is not None:
        depois = {c: versoes[c] for c in ajustes if versoes[c].versao > confirmacao.versao}
        if depois:
            raise _conflito("o outro lado mudou os mesmos campos depois", atual, depois, usuario)
    if confirmacao.conta_id:
        _conferir_conta_ou_cartao(
            conn, confirmacao.conta_id, confirmacao.conta_id == atual.conta_id
        )
    mes, a_mao = _fatura_depois(conn, atual, _com_mudancas(atual, ajustes), ajustes)
    momento = _momento(confirmacao.acao_em)
    versao = subir_versao(
        conn,
        id,
        atual.versao,
        "situacao = 'realizado', valor_centavos = COALESCE(%s, valor_centavos),"
        " data = COALESCE(%s, data), conta_id = COALESCE(%s, conta_id), mes = %s,"
        " fatura_a_mao = %s, alterado_por = %s, alterado_em = %s",
        (
            confirmacao.valor_centavos,
            confirmacao.data,
            confirmacao.conta_id,
            mes,
            a_mao,
            usuario,
            momento,
        ),
    )
    registrar_mudancas(conn, id, ["situacao", *ajustes], versao, usuario, momento)
    return _um(conn, id)


@router.post(
    "/lancamentos/{id}/confirmar",
    response_model=Lancamento,
    operation_id="confirmar_lancamento",
    responses=_CONFLITO | _EXCLUIDO,
)
def confirmar_lancamento(
    id: UUID, confirmacao: Confirmacao, usuario: UsuarioLogado, request: Request
) -> Lancamento | JSONResponse:
    """Confirmar de novo sem ajuste diferente (a fila reenviou, a outra pessoa confirmou em um
    toque) devolve o gravado; com ajuste diferente é 409 com os campos em conflito e quem
    confirmou, para nada se perder em silêncio."""
    return _na_rota(request, lambda conn: _confirmar(conn, id, confirmacao, usuario))


@router.delete(
    "/lancamentos/{id}",
    status_code=204,
    operation_id="excluir_lancamento",
    responses=_CONFLITO,
)
def excluir_lancamento(
    id: UUID,
    usuario: UsuarioLogado,
    request: Request,
    versao: int | None = None,
    acao_em: datetime | None = None,
) -> Response:
    """Idempotente: excluir o que já não existe também dá 204. Com `versao`, o que o outro lado
    mudou depois dela é 409, para perguntar antes."""
    resposta = _na_rota(request, lambda conn: _excluir(conn, id, versao, usuario, acao_em))
    return resposta if isinstance(resposta, JSONResponse) else Response(status_code=204)


@router.post(
    "/lancamentos/{id}/manter-os-dois",
    response_model=Lancamento,
    operation_id="manter_os_dois",
    responses=_EXCLUIDO,
)
def manter_os_dois(id: UUID, usuario: UsuarioLogado, request: Request) -> Lancamento | JSONResponse:
    """O casal conferiu o "Parece repetido" e os dois lançamentos ficam. Não é uma mudança do
    lançamento: não sobe a versão nem entra no conflito."""

    def gravar(conn) -> Lancamento:
        _atual(conn, id, usuario)
        conn.execute(
            "UPDATE lancamentos SET repetido_mantido_em = COALESCE(repetido_mantido_em, now())"
            " WHERE id = %s",
            (id,),
        )
        return _um(conn, id)

    return _na_rota(request, gravar)


LIMITE_DO_LOTE = 100


class AcaoCriar(BaseModel):
    acao: Literal["criar"]
    lancamento: NovoLancamento


class AcaoEditar(BaseModel):
    acao: Literal["editar"]
    id: UUID
    alteracao: AlteracaoDeLancamento


class AcaoExcluir(BaseModel):
    acao: Literal["excluir"]
    id: UUID
    # A versão que o aparelho tinha; sem ela, exclui de qualquer jeito.
    versao: int | None = None
    acao_em: datetime | None = None


Acao = AcaoCriar | AcaoEditar | AcaoExcluir


class Lote(BaseModel):
    acoes: list[Annotated[Acao, Field(discriminator="acao")]] = Field(
        min_length=1, max_length=LIMITE_DO_LOTE
    )


class Resultado(BaseModel):
    """`recusada` traz o motivo para mostrar; `conflito` traz o lançamento do servidor e os
    campos em conflito; `descartada` é a edição de algo já excluído, com quem excluiu."""

    resultado: Literal["aceita", "conflito", "recusada", "descartada"]
    motivo: str | None = None
    lancamento: Lancamento | None = None
    campos: list[CampoEmConflito] | None = None
    exclusao: Exclusao | None = None


class ResultadoDoLote(BaseModel):
    resultados: list[Resultado]


def _aplicar(acao: Acao, usuario: str, request: Request) -> Resultado:
    """As mesmas regras das rotas de um lançamento só; a recusa de uma não para as outras.

    Banco fora do ar ou disputa perdida derrubam o lote inteiro, que o aparelho reenvia; outro
    erro fica só nesta ação, recusada, para não travar a fila para sempre.
    """
    try:
        return em_transacao(url_do_banco(request), lambda conn: _aplicar_na(conn, acao, usuario))
    except LancamentoNaoEncontrado:
        return Resultado(resultado="recusada", motivo="lançamento não encontrado")
    except LancamentoExcluido as e:
        return Resultado(resultado="descartada", motivo=e.exclusao.motivo, exclusao=e.exclusao)
    except ConflitoDeCampos as e:
        conflito = e.conflito
        return Resultado(
            resultado="conflito",
            motivo=conflito.motivo,
            lancamento=conflito.lancamento,
            campos=conflito.campos,
        )
    except HTTPException as erro:
        if erro.status_code == 422:
            return Resultado(resultado="recusada", motivo=erro.detail)
        raise
    except psycopg.OperationalError:
        raise
    except Exception:
        log.exception("ação do lote falhou")
        return Resultado(resultado="recusada", motivo="erro no servidor")


def _aplicar_na(conn, acao: Acao, usuario: str) -> Resultado:
    match acao:
        case AcaoCriar(lancamento=novo):
            return Resultado(resultado="aceita", lancamento=_criar(conn, novo, usuario)[0])
        case AcaoEditar(id=id, alteracao=alteracao):
            return Resultado(resultado="aceita", lancamento=_editar(conn, id, alteracao, usuario))
        case AcaoExcluir(id=id, versao=versao, acao_em=acao_em):
            _excluir(conn, id, versao, usuario, acao_em)
            return Resultado(resultado="aceita")


@router.post("/lancamentos/lote", response_model=ResultadoDoLote, operation_id="enviar_lote")
def enviar_lote(lote: Lote, usuario: UsuarioLogado, request: Request) -> ResultadoDoLote:
    """A fila do aparelho: as ações na ordem, cada uma na sua transação, um resultado por ação."""
    return ResultadoDoLote(resultados=[_aplicar(a, usuario, request) for a in lote.acoes])
