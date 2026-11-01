"""Contas, categorias e lançamentos simples. Sem chave estrangeira nem trigger (subconjunto do
DSQL, ADR 0009): a API confere as ligações. O id do lançamento nasce no aparelho."""

from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from typing import Literal, get_args
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import psycopg
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from app import faturas
from app.banco import conectar, em_transacao
from app.config import valores_iniciais
from app.item_em_que_conta import guardar_item_atual_das_partes, guardar_item_atual_do_lancamento
from app.login import UsuarioLogado
from app.pessoas import configuradas

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


def tags_limpas(nomes: list[str] | None) -> list[str] | None:
    if nomes is None:
        return None
    limpos = [nome.strip() for nome in nomes]
    if "" in limpos:
        raise ValueError("tag sem nome")
    return list({nome.casefold(): nome for nome in limpos}.values())


def sem_repetidas(ids: list[UUID] | None) -> list[UUID] | None:
    if ids is not None and len(set(ids)) != len(ids):
        raise ValueError("categoria repetida")
    return ids


def _primeiro_dia(mes: date | None) -> date | None:
    return mes and faturas.mes_de(mes)


ITEM_FORA_DAS_CATEGORIAS = "o item escolhido não é de uma categoria do lançamento"


class Parte(BaseModel):
    """Um pedaço da compra que junta coisas diferentes, com classificação própria (ADR 0022). Quem
    soma por categoria, tag, pessoa ou item lê a parte; a fatura, o mês e o saldo leem a compra."""

    # Nasce no aparelho, como o do lançamento, e fica enquanto a parte existir.
    id: UUID
    descricao: str = ""
    valor_centavos: int = Field(gt=0)
    categoria_ids: list[UUID] = Field(min_length=1)
    tags: list[str] = []
    # O id de uma pessoa do casal; sem ela, a parte é do conjunto.
    pessoa: str | None = None
    # A escolha do item do planejamento em que a parte conta, como no lançamento (ADR 0006).
    item_categoria_id: UUID | None = None

    _tags = field_validator("tags")(tags_limpas)
    _categorias = field_validator("categoria_ids")(sem_repetidas)

    @field_validator("pessoa")
    @classmethod
    def _conjunto(cls, pessoa: str | None) -> str | None:
        return pessoa or None

    @model_validator(mode="after")
    def _item_de_uma_das_categorias(self):
        if self.item_categoria_id and self.item_categoria_id not in self.categoria_ids:
            raise ValueError(ITEM_FORA_DAS_CATEGORIAS)
        return self


SO_A_VISTA = "por enquanto, só a compra à vista tem partes"
SEM_CLASSIFICACAO_PROPRIA = "a compra com partes não tem categoria, tag nem pessoa próprias"
DUAS_PARTES_OU_MAIS = "a compra tem duas partes ou mais"


def conferir_partes(partes: list[Parte], valor_centavos: int, tipo: str) -> None:
    """As regras das partes que não dependem do banco: duas ou mais, ids diferentes, só na
    despesa, e a soma é o valor da compra."""
    if len(partes) < 2:
        raise ValueError(DUAS_PARTES_OU_MAIS)
    if len({p.id for p in partes}) != len(partes):
        raise ValueError("parte repetida")
    if tipo != "despesa":
        raise ValueError("partes só na despesa")
    soma = sum(p.valor_centavos for p in partes)
    if soma != valor_centavos:
        raise ValueError(f"as partes somam {soma} centavos e a compra, {valor_centavos}")


class DadosDoLancamento(BaseModel):
    id: UUID
    tipo: Literal["despesa", "receita"]
    valor_centavos: int = Field(gt=0)
    data: date
    descricao: str = ""
    # A conta ou o cartão; no cartão, `data` é a data da compra.
    conta_id: UUID
    # Vazia só na compra com partes, que não tem classificação própria, e no estorno avulso, onde
    # a categoria é opcional.
    categoria_ids: list[UUID] = []
    # Sem situação, a data decide: futura nasce prevista, de hoje ou do passado, realizada.
    situacao: Literal["previsto", "realizado"] | None = None
    # Pelo nome: a tag que ainda não existe nasce junto com o lançamento.
    tags: list[str] = []
    # O id de uma pessoa do casal; sem ela, o lançamento é do conjunto.
    pessoa: str | None = None
    # Só no cartão: o mês da fatura, que o servidor escolhe pela data da compra e pelo
    # fechamento. Mandar o mês é trocar a fatura à mão (o banco lançou a compra com atraso).
    fatura_mes: date | None = None
    # O estorno: crédito de uma compra no cartão, ligado a ela (ADR 0016). É uma despesa que
    # diminui, com as mesmas categorias e tags da compra original, na fatura em que aparece.
    estorno_de: UUID | None = None
    # O estorno avulso (ticket 135, ADR 0016): crédito no cartão sem compra ligada, para o que a
    # fatura traz sem compra identificável. Diminui a fatura e o mês como o estorno, mas não tem o
    # limite do valor de uma compra, e a categoria, as tags e a pessoa são opcionais.
    estorno_avulso: bool | None = None
    # A escolha do casal do item do planejamento em que o lançamento conta, pela categoria dele
    # que tem o item; sem ela, conta sozinho quando só uma das categorias tem item no mês
    # (ADR 0006). Escolha explícita nunca muda sozinha.
    item_categoria_id: UUID | None = None
    # As partes da compra à vista que junta coisas diferentes (ADR 0022): duas ou mais, somando o
    # valor dela. Com partes, a compra não tem categoria, tag, pessoa nem item próprios.
    partes: list[Parte] = []

    _tags = field_validator("tags")(tags_limpas)
    _categorias = field_validator("categoria_ids")(sem_repetidas)
    _fatura = field_validator("fatura_mes")(_primeiro_dia)


class NovoLancamento(DadosDoLancamento):
    # A hora em que a pessoa fez a ação no aparelho; sem ela, a da chegada ao servidor.
    acao_em: datetime | None = None

    @model_validator(mode="after")
    def _classificacao(self):
        if self.partes:
            if self.categoria_ids or self.tags or self.pessoa or self.item_categoria_id:
                raise ValueError(SEM_CLASSIFICACAO_PROPRIA)
            if self.estorno_de or self.estorno_avulso:
                raise ValueError("estorno não tem partes")
            conferir_partes(self.partes, self.valor_centavos, self.tipo)
            return self
        if not self.categoria_ids and not self.estorno_avulso:
            raise ValueError("lançamento sem categoria")
        if self.item_categoria_id and self.item_categoria_id not in self.categoria_ids:
            raise ValueError(ITEM_FORA_DAS_CATEGORIAS)
        return self

    @model_validator(mode="after")
    def _avulso_sem_compra(self):
        if self.estorno_avulso and self.estorno_de:
            raise ValueError("o estorno avulso não é ligado a uma compra")
        return self


class Lancamento(DadosDoLancamento):
    situacao: Literal["previsto", "realizado"]
    # O mês em que o lançamento conta (planejamento, categorias, tags, resumo): o mês da fatura
    # no cartão, o da data no resto (ADR 0003). Gravado como o primeiro dia do mês.
    mes: date
    # Previsto que pede confirmação e cuja data já passou sem ela; continua previsto (e contando)
    # até confirmar. O automático não pede: a tarefa diária o realiza na data.
    atrasado: bool
    # A regra que gerou o lançamento e o número da ocorrência nela (1, 2...); o avulso não tem.
    recorrencia_id: UUID | None = None
    ocorrencia: int | None = None
    # Vira realizado sozinho na data, sem confirmação (recorrência de valor fixo, parcelamento).
    automatico: bool = False
    # O parcelamento que gerou a parcela, o número dela (3 em 3/10) e o total de parcelas.
    parcelamento_id: UUID | None = None
    parcela: int | None = None
    parcelas: int | None = None
    # Parcela com um campo que uma pessoa mudou só nela ("só esta"): a correção do parcelamento e
    # a mudança de "esta e as próximas" ou "todas" a preservam nesse campo (tickets 47 e 136). Só
    # a parcela tem a marca.
    alterada_a_mao: bool = False
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
    "item_categoria_id",
    # As partes são um campo só no conflito: quem decide escolhe a lista inteira (ADR 0022).
    "partes",
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
    # Vazia só junto com as partes, que tiram a classificação própria da compra (ADR 0022), e no
    # estorno avulso, que pode ficar sem categoria.
    categoria_ids: list[UUID] | None = None
    # Sem situação, só mudar a data refaz a inferência, se ninguém mudou a situação depois.
    situacao: Literal["previsto", "realizado"] | None = None
    tags: list[str] | None = None
    # Sem o campo, a pessoa fica; vazia, o lançamento passa a ser do conjunto.
    pessoa: str | None = None
    # Troca a fatura à mão; mudar a data ou o cartão sem ele escolhe a fatura de novo.
    fatura_mes: date | None = None
    # Escolhe o item em que o lançamento conta; a escolha sai com a categoria dela.
    item_categoria_id: UUID | None = None
    # A lista inteira de partes. Duas ou mais dividem a compra (que perde a classificação
    # própria); uma só é tirar a penúltima: a compra volta a ser uma, com a classificação dela.
    partes: list[Parte] | None = None
    acao_em: datetime | None = None

    _tags = field_validator("tags")(tags_limpas)
    _categorias = field_validator("categoria_ids")(sem_repetidas)
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
VERSAO = "COALESCE(versao, 1)"
# O mês em que o lançamento conta. Gravado pela migration 0034 nos de antes; a data cobre o que
# sobrou dela e o que a API antiga gravar durante o deploy.
MES_EM_QUE_CONTA = "COALESCE(mes, date_trunc('month', data)::date)"
# O valor com o sinal de quem soma despesas (fatura, mês): a despesa soma, o estorno e a receita
# (crédito) diminuem.
VALOR_COM_SINAL = (
    "CASE WHEN lancamentos.tipo = 'despesa' AND NOT "
    + "(lancamentos.estorno_de IS NOT NULL OR COALESCE(lancamentos.estorno_avulso, false))"
    + " THEN lancamentos.valor_centavos ELSE -lancamentos.valor_centavos END"
)
# O valor com o sinal do saldo de uma conta, no lançamento `l`: a receita entra, a despesa sai.
VALOR_NA_CONTA = "CASE l.tipo WHEN 'receita' THEN l.valor_centavos ELSE -l.valor_centavos END"
NO_CARTAO = "EXISTS (SELECT FROM cartoes WHERE cartoes.id = lancamentos.conta_id)"
# Quantas parcelas tem o parcelamento da parcela (o 10 de 3/10); o avulso não tem.
PARCELAS = "(SELECT p.parcelas FROM parcelamentos p WHERE p.id = lancamentos.parcelamento_id)"
# Os campos da parcela que se alteram à mão (ticket 136); a situação é sempre só da parcela.
CAMPOS_DA_PARCELA = (
    "valor_centavos",
    "data",
    "conta_id",
    "fatura_mes",
    "descricao",
    "categoria_ids",
    "tags",
    "pessoa",
    "item_categoria_id",
)
# Uma pessoa mudou (campo sem `origem`) um desses campos só na parcela, que a correção do
# parcelamento não toca. A confirmação sem ajuste só registra a situação, e as regras gravam com
# `origem`: nenhuma conta como edição.
ALTERADA_A_MAO = (
    "(parcelamento_id IS NOT NULL AND EXISTS (SELECT FROM lancamento_campos c"
    " WHERE c.lancamento_id = lancamentos.id AND c.origem IS NULL"
    f" AND c.campo IN ({', '.join(repr(c) for c in CAMPOS_DA_PARCELA)})))"
)


def campos_a_mao(conn, ids: list[UUID]) -> dict[UUID, set[str]]:
    """Por parcela, os campos que uma pessoa mudou só nela."""
    a_mao: dict[UUID, set[str]] = {}
    for lancamento_id, campo in conn.execute(
        "SELECT lancamento_id, campo FROM lancamento_campos"
        " WHERE lancamento_id = ANY(%s) AND origem IS NULL AND campo = ANY(%s)",
        (ids, list(CAMPOS_DA_PARCELA)),
    ):
        a_mao.setdefault(lancamento_id, set()).add(campo)
    return a_mao


_COLUNAS = (
    "id, tipo, situacao, valor_centavos, data, descricao, conta_id,"
    f" criado_por, criado_em, alterado_por, alterado_em, {VERSAO}, pessoa, fonte,"
    " recorrencia_id, ocorrencia, COALESCE(automatico, false),"
    f" {_REPETIDO_DE}, {MES_EM_QUE_CONTA}, {NO_CARTAO}, estorno_de, parcelamento_id, parcela,"
    f" {PARCELAS}, item_categoria_id, {ALTERADA_A_MAO}, COALESCE(estorno_avulso, false)"
)


def url_do_banco(request: Request) -> str | None:
    return request.app.state.url


# Saldo = abertura + realizados (lançamentos e transferências) depois da data de abertura
# (sem abertura, todos, a partir de zero). O que veio antes (ou no dia) da abertura já está no
# valor informado e só serve às estatísticas.
_SALDO = f"""
    SELECT c.id, c.nome, c.tipo, c.saldo_abertura_centavos, c.data_abertura,
           c.arquivada_em IS NOT NULL,
           COALESCE(c.saldo_abertura_centavos, 0) + COALESCE((
               SELECT SUM({VALOR_NA_CONTA})
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


def contas_com_saldo(conn) -> list[Conta]:
    """Todas as contas, arquivadas inclusive, com o saldo; o cartão não é conta."""
    return [_conta(linha) for linha in conn.execute(_SALDO).fetchall()]


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


def conferir_ligacoes(
    conn,
    lancamento,
    conta_atual: UUID | None = None,
    categorias_atuais: frozenset[UUID] = frozenset(),
) -> None:
    """Conta, cartão e categoria arquivados só valem num lançamento que já os tinha. Serve a quem
    tem `tipo`, `conta_id`, `categoria_ids` e `pessoa`: o lançamento e a regra que gera
    lançamentos."""
    _conferir_conta_ou_cartao(conn, lancamento.conta_id, lancamento.conta_id == conta_atual)
    # A compra com partes classifica em cada parte (ADR 0022).
    for classificado in [lancamento, *getattr(lancamento, "partes", [])]:
        _conferir_classificacao(
            conn,
            lancamento.tipo,
            classificado.categoria_ids,
            classificado.pessoa,
            categorias_atuais,
        )


def _conferir_classificacao(
    conn, tipo: str, categoria_ids: list[UUID], pessoa: str | None, atuais: frozenset[UUID]
) -> None:
    pessoas = configuradas()
    if pessoa and pessoas and pessoa not in pessoas:
        raise recusar("pessoa não encontrada")
    tipos = {}
    arquivadas = set()
    for id, tipo_da_categoria, arquivada in conn.execute(
        "SELECT id, tipo, arquivada_em IS NOT NULL FROM categorias WHERE id = ANY(%s)",
        (categoria_ids,),
    ):
        tipos[id] = tipo_da_categoria
        if arquivada:
            arquivadas.add(id)
    for categoria in categoria_ids:
        if categoria not in tipos:
            raise recusar("categoria não encontrada")
        if tipos[categoria] != tipo:
            raise recusar(f"categoria de {tipos[categoria]} num lançamento de {tipo}")
        if categoria in arquivadas and categoria not in atuais:
            raise recusar("categoria arquivada")


def ids_das_tags(conn, nomes: list[str], usuario: str, ja_tinha: set[UUID]) -> list[UUID]:
    """Acha cada tag pelo nome (sem distinguir maiúsculas) ou a cria. Tag arquivada só vale para
    quem já a tinha."""
    existentes = {
        nome.casefold(): (tag, arquivada)
        for tag, nome, arquivada in conn.execute(
            "SELECT id, nome, arquivada_em IS NOT NULL FROM tags"
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
    return ids


def _gravar_tags(conn, id: UUID, nomes: list[str], usuario: str) -> None:
    ja_tinha = {
        linha[0]
        for linha in conn.execute(
            "SELECT tag_id FROM lancamento_tags WHERE lancamento_id = %s", (id,)
        )
    } | tags_das_partes(conn, id)
    ids = ids_das_tags(conn, nomes, usuario, ja_tinha)
    conn.execute("DELETE FROM lancamento_tags WHERE lancamento_id = %s", (id,))
    for tag in ids:
        conn.execute(
            "INSERT INTO lancamento_tags (lancamento_id, tag_id) VALUES (%s, %s)", (id, tag)
        )


def gravar_categorias(conn, id: UUID, categorias: list[UUID]) -> None:
    conn.execute("DELETE FROM lancamento_categorias WHERE lancamento_id = %s", (id,))
    for categoria in categorias:
        conn.execute(
            "INSERT INTO lancamento_categorias (lancamento_id, categoria_id) VALUES (%s, %s)",
            (id, categoria),
        )


def categorias_das_partes(conn, id: UUID) -> frozenset[UUID]:
    """As categorias que as partes de um lançamento já têm: a arquivada segue valendo para quem
    já a tinha."""
    return frozenset(
        c
        for (c,) in conn.execute(
            "SELECT pc.categoria_id FROM parte_categorias pc"
            " JOIN lancamento_partes p ON p.id = pc.parte_id WHERE p.lancamento_id = %s",
            (id,),
        )
    )


def tags_das_partes(conn, id: UUID) -> set[UUID]:
    """As tags que as partes de um lançamento já têm, como `categorias_das_partes`."""
    return {
        t
        for (t,) in conn.execute(
            "SELECT pt.tag_id FROM parte_tags pt"
            " JOIN lancamento_partes p ON p.id = pt.parte_id WHERE p.lancamento_id = %s",
            (id,),
        )
    }


def gravar_partes(conn, id: UUID, partes: list[Parte], usuario: str) -> None:
    """Troca as partes do lançamento pela lista; a parte que fica (o mesmo id) mantém o item em
    que contava, se a categoria dele continua nela (`item_em_que_conta`)."""
    guardar_item_atual_das_partes(conn, "p.lancamento_id = %s", (id,))
    item_atual = dict(
        conn.execute(
            "SELECT id, item_atual_categoria_id FROM lancamento_partes WHERE lancamento_id = %s",
            (id,),
        ).fetchall()
    )
    ja_tinha = tags_das_partes(conn, id)
    ja_tinha |= {
        t
        for (t,) in conn.execute(
            "SELECT tag_id FROM lancamento_tags WHERE lancamento_id = %s", (id,)
        )
    }
    tags_de_cada = [ids_das_tags(conn, p.tags, usuario, ja_tinha) for p in partes]
    apagar_partes(conn, [id])
    for ordem, (parte, tags) in enumerate(zip(partes, tags_de_cada)):
        atual = item_atual.get(parte.id)
        conn.execute(
            "INSERT INTO lancamento_partes (id, lancamento_id, ordem, descricao, valor_centavos,"
            " pessoa, item_categoria_id, item_atual_categoria_id)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                parte.id,
                id,
                ordem,
                parte.descricao,
                parte.valor_centavos,
                parte.pessoa,
                parte.item_categoria_id,
                atual if atual in parte.categoria_ids else None,
            ),
        )
        for categoria in parte.categoria_ids:
            conn.execute(
                "INSERT INTO parte_categorias (parte_id, categoria_id) VALUES (%s, %s)",
                (parte.id, categoria),
            )
        for tag in tags:
            conn.execute(
                "INSERT INTO parte_tags (parte_id, tag_id) VALUES (%s, %s)", (parte.id, tag)
            )


def apagar_partes(conn, ids: list[UUID], so_as_ligacoes: bool = False) -> None:
    """Tira as partes dos lançamentos, com as ligações delas. Com `so_as_ligacoes` (a exclusão),
    as partes ficam, sem as ligações, como as do lançamento."""
    partes = [
        p
        for (p,) in conn.execute(
            "SELECT id FROM lancamento_partes WHERE lancamento_id = ANY(%s)", (ids,)
        )
    ]
    if not partes:
        return
    conn.execute("DELETE FROM parte_categorias WHERE parte_id = ANY(%s)", (partes,))
    conn.execute("DELETE FROM parte_tags WHERE parte_id = ANY(%s)", (partes,))
    if not so_as_ligacoes:
        conn.execute("DELETE FROM lancamento_partes WHERE id = ANY(%s)", (partes,))


def acompanhar_estornos(conn, compra_id: UUID) -> None:
    """Os estornos de uma compra valem o que ela tem agora: categorias, tags (mesmo arquivadas) e o
    item do planejamento. O estorno não guarda classificação própria (ticket 133, ADR 0016): esta
    cópia roda onde a compra muda, e a leitura segue igual para quem soma."""
    estornos = [
        id
        for (id,) in conn.execute(
            "SELECT id FROM lancamentos WHERE estorno_de = %s AND excluido_em IS NULL", (compra_id,)
        )
    ]
    if not estornos:
        return
    conn.execute("DELETE FROM lancamento_categorias WHERE lancamento_id = ANY(%s)", (estornos,))
    conn.execute("DELETE FROM lancamento_tags WHERE lancamento_id = ANY(%s)", (estornos,))
    conn.execute(
        "INSERT INTO lancamento_categorias (lancamento_id, categoria_id)"
        " SELECT e, categoria_id FROM unnest(%s::uuid[]) AS e,"
        " (SELECT categoria_id FROM lancamento_categorias WHERE lancamento_id = %s) AS c",
        (estornos, compra_id),
    )
    conn.execute(
        "INSERT INTO lancamento_tags (lancamento_id, tag_id)"
        " SELECT e, tag_id FROM unnest(%s::uuid[]) AS e,"
        " (SELECT tag_id FROM lancamento_tags WHERE lancamento_id = %s) AS t",
        (estornos, compra_id),
    )
    conn.execute(
        # A escolha do estorno é o item em que a compra conta (a escolha dela ou o item em que
        # contava sozinha): ele diminui o mesmo item e não fica "a escolher" em outro mês.
        "UPDATE lancamentos e SET"
        " item_categoria_id = COALESCE(c.item_categoria_id, c.item_atual_categoria_id),"
        " item_atual_categoria_id = c.item_atual_categoria_id"
        " FROM lancamentos c WHERE c.id = %s AND e.id = ANY(%s)",
        (compra_id, estornos),
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
        f"UPDATE lancamentos SET {atribuicoes}, versao = %s WHERE id = %s AND {VERSAO} = %s",
        (*parametros, de + 1, id, de),
    ).rowcount
    if not gravadas:
        raise psycopg.errors.SerializationFailure("o lançamento mudou durante a gravação")
    return de + 1


def mudar_fatura(conn, id: UUID, versao: int, mes: date, usuario: str, origem: str) -> None:
    """A fatura que o app escolheu de novo (as datas do cartão mudaram): sobe a versão e conta
    como mudança do outro lado, com a origem, na tela de conflito (ADR 0011)."""
    agora = _momento(None)
    guardar_item_atual_do_lancamento(conn, id)  # no mês novo, fica no item em que estava
    nova = subir_versao(
        conn, id, versao, "mes = %s, alterado_por = %s, alterado_em = %s", (mes, usuario, agora)
    )
    registrar_mudancas(conn, id, ["fatura_mes"], nova, usuario, agora, origem=origem)


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
    # No Postgres em READ COMMITTED (local e CI), a exclusão do outro lado pode ser confirmada
    # entre as duas leituras; lida de novo, ela vira o 410. O DSQL lê tudo do mesmo instante.
    lidos = _todos(conn, "id = %s", (id,))
    return lidos[0] if lidos else _atual(conn, id, usuario)


def mes_em_que_conta(conn, conta_id: UUID, data: date, parcela: int | None = None) -> date:
    """O mês em que conta um lançamento pela data: no cartão, o da fatura que fecha depois dela
    (a parcela n, n - 1 faturas depois), que nasce aqui se faltar; no resto, o da data (ADR
    0003). Serve também às regras que geram lançamentos (recorrência e parcelamento)."""
    cartao = faturas.ler_cartao(conn, conta_id)
    if cartao is None:
        return faturas.mes_de(data)
    mes = faturas.mes_da_parcela(conn, cartao.titular, data, parcela)
    faturas.garantir_fatura(conn, cartao.titular, mes)
    return mes


def _onde_conta(
    conn,
    lancamento: DadosDoLancamento,
    mantida: date | None = None,
    parcela: int | None = None,
    criar: bool = True,
) -> tuple[date, date | None, bool]:
    """O mês em que conta, o mês da fatura (só no cartão) e se a fatura foi escolhida à mão.

    No cartão, a fatura é a pedida, a `mantida` de uma troca à mão anterior ou a que fecha
    depois da data da compra (a da `parcela` n, n - 1 faturas depois), e nasce aqui se ainda
    não existe (salvo sem `criar`); no resto, o mês da data.
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
    mes = a_mao or faturas.mes_da_parcela(conn, cartao.titular, lancamento.data, parcela)
    if criar:
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
    conn, atual: Lancamento, depois: DadosDoLancamento, mudancas: dict, criar: bool = True
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
    mes, fatura_mes, a_mao = _onde_conta(conn, depois, mantida, atual.parcela, criar)
    if fatura_mes != atual.fatura_mes:
        mudancas["fatura_mes"] = fatura_mes
    return mes, a_mao


def onde_ficaria(conn, atual: Lancamento, mudancas: dict) -> tuple[UUID | None, date]:
    """O titular do cartão (`None` fora dele) e o mês em que o lançamento contaria com as
    `mudancas`, escolhido como na edição (`_fatura_depois`), sem criar a fatura."""
    mudancas = dict(mudancas)
    depois = _com_mudancas(atual, mudancas)
    mes, _ = _fatura_depois(conn, atual, depois, mudancas, criar=False)
    cartao = faturas.ler_cartao(conn, depois.conta_id)
    return (cartao.titular.id if cartao else None), mes


def valor_com_sinal(lancamento: DadosDoLancamento, valor: int) -> int:
    """O `valor` com o sinal de `VALOR_COM_SINAL` no lançamento: a despesa soma, o estorno e a
    receita diminuem."""
    estorno = lancamento.estorno_de is not None or bool(lancamento.estorno_avulso)
    return valor if lancamento.tipo == "despesa" and not estorno else -valor


def _item_atual_depois(conn, id: UUID, depois: DadosDoLancamento) -> UUID | None:
    """O item em que um lançamento que vai mudar conta antes da mudança, se a categoria dele
    continua no lançamento: a categoria nova ou o mês novo que criam ambiguidade não o tiram do
    item (`item_em_que_conta`)."""
    guardar_item_atual_do_lancamento(conn, id)
    (atual,) = conn.execute(
        "SELECT item_atual_categoria_id FROM lancamentos WHERE id = %s", (id,)
    ).fetchone()
    return atual if atual in depois.categoria_ids else None


def iguais(campo: Campo, pedido, gravado) -> bool:
    if campo == "partes":
        return list(map(_parte_normalizada, pedido)) == list(map(_parte_normalizada, gravado))
    if campo == "categoria_ids":
        return set(pedido) == set(gravado)
    if campo == "tags":
        return {t.casefold() for t in pedido} == {t.casefold() for t in gravado}
    return pedido == gravado


def _conferir_estorno(
    conn, id: UUID, dados: DadosDoLancamento, original_id: UUID
) -> frozenset[UUID]:
    """O estorno é de uma compra no cartão que ainda existe, vai para um cartão e, somado aos
    outros estornos dela, não passa do valor da compra. Devolve as categorias da compra, que valem
    no estorno mesmo arquivadas (as categorias e tags do estorno são as dela, ticket 133)."""
    if dados.tipo != "despesa" or not faturas.ler_cartao(conn, dados.conta_id):
        raise recusar("estorno é um crédito no cartão")
    original = conn.execute(
        "SELECT tipo, valor_centavos, conta_id, estorno_de FROM lancamentos"
        " WHERE id = %s AND excluido_em IS NULL",
        (original_id,),
    ).fetchone()
    if not original:
        raise recusar("compra original não encontrada")
    tipo, valor, conta, estorno_de = original
    if estorno_de:
        raise recusar("estorno de estorno")
    if conn.execute(
        "SELECT 1 FROM lancamento_partes WHERE lancamento_id = %s LIMIT 1", (original_id,)
    ).fetchone():
        raise recusar("o estorno de uma parte da compra ainda não existe")
    if tipo != "despesa" or not faturas.ler_cartao(conn, conta):
        raise recusar("só compra no cartão tem estorno")
    (outros,) = conn.execute(
        "SELECT COALESCE(SUM(valor_centavos), 0) FROM lancamentos"
        " WHERE estorno_de = %s AND excluido_em IS NULL AND id <> %s",
        (original_id, id),
    ).fetchone()
    if outros + dados.valor_centavos > valor:
        raise recusar("estornos somam mais que a compra")
    return frozenset(
        c
        for (c,) in conn.execute(
            "SELECT categoria_id FROM lancamento_categorias WHERE lancamento_id = %s",
            (original_id,),
        )
    )


def criar(conn, novo: NovoLancamento, usuario: str) -> tuple[Lancamento, bool]:
    """Reenviar o mesmo id (a fila repete) devolve o que já está gravado, sem criar de novo."""
    # Reenvio de um lançamento já gravado não falha porque a categoria foi arquivada depois.
    ja_ligadas = frozenset(
        categoria
        for (categoria,) in conn.execute(
            "SELECT categoria_id FROM lancamento_categorias WHERE lancamento_id = %s",
            (novo.id,),
        )
    ) | categorias_das_partes(conn, novo.id)
    if (
        novo.estorno_de
        and not conn.execute("SELECT 1 FROM lancamentos WHERE id = %s", (novo.id,)).fetchone()
    ):
        da_compra = _conferir_estorno(conn, novo.id, novo, novo.estorno_de)
        # O estorno não tem categoria nem tag próprias: vale o que a compra tem (arquivadas
        # incluídas), e o que a pessoa mandou nesses campos não conta.
        novo = novo.model_copy(update={"categoria_ids": sorted(da_compra)})
        ja_ligadas |= da_compra
    if novo.estorno_avulso and (
        novo.tipo != "despesa" or not faturas.ler_cartao(conn, novo.conta_id)
    ):
        raise recusar("estorno é um crédito no cartão")
    conferir_ligacoes(conn, novo, categorias_atuais=ja_ligadas)
    mes, _, a_mao = _onde_conta(conn, novo)
    momento = _momento(novo.acao_em)
    escolhida = None if novo.estorno_de else novo.item_categoria_id
    gravados = conn.execute(
        "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, descricao,"
        " conta_id, criado_por, alterado_por, versao, pessoa, criado_em, alterado_em, fonte,"
        " mes, fatura_a_mao, estorno_de, item_categoria_id, estorno_avulso)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s, 'app', %s, %s, %s, %s, %s)"
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
            novo.estorno_de,
            escolhida,
            bool(novo.estorno_avulso),
        ),
    ).rowcount
    if gravados and novo.estorno_de:
        guardar_item_atual_do_lancamento(conn, novo.estorno_de)
        acompanhar_estornos(conn, novo.estorno_de)
    elif gravados:
        gravar_categorias(conn, novo.id, novo.categoria_ids)
        _gravar_tags(conn, novo.id, novo.tags, usuario)
        if novo.partes:
            gravar_partes(conn, novo.id, novo.partes, usuario)
    return _atual(conn, novo.id, usuario), bool(gravados)


def editar(conn, id: UUID, alteracao: AlteracaoDeLancamento, usuario: str) -> Lancamento:
    """Aplica os campos pedidos sobre o que o servidor tem. Campo que o outro lado mudou depois
    da versão do pedido, para outro valor, recusa a mudança inteira como conflito; mudança igual
    à gravada não conta."""
    atual = _atual(conn, id, usuario)
    versoes = _versoes(conn, atual)
    pedidas = alteracao.model_dump(exclude={"versao", "acao_em"}, exclude_none=True)
    if "pessoa" in pedidas:
        pedidas["pessoa"] = pedidas["pessoa"] or None
    if alteracao.partes is not None:
        pedidas |= _o_que_as_partes_mudam(alteracao.partes, pedidas)
    mudancas = {}
    conflitos: list[Campo] = []
    for campo, valor in pedidas.items():
        if iguais(campo, valor, getattr(atual, campo)):
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
    categorias = mudancas.get("categoria_ids", atual.categoria_ids)
    if mudancas.get("item_categoria_id") not in (None, *categorias):
        raise recusar(ITEM_FORA_DAS_CATEGORIAS)
    if "item_categoria_id" not in mudancas and atual.item_categoria_id not in (None, *categorias):
        # A escolha explícita sai com a categoria dela.
        mudancas["item_categoria_id"] = None
    if not mudancas:
        return atual
    editado = _com_mudancas(atual, mudancas)
    if editado.partes:
        _conferir_compra_com_partes(conn, atual, editado)
    elif not editado.categoria_ids and not atual.estorno_avulso:
        raise recusar("lançamento sem categoria")
    if atual.estorno_de:
        if "tipo" in mudancas:
            raise recusar("estorno é um crédito no cartão")
        if {"categoria_ids", "tags"} & mudancas.keys():
            raise recusar("estorno leva as mesmas categorias e tags da compra")
        if "item_categoria_id" in mudancas:
            raise recusar("estorno conta no item do planejamento em que a compra conta")
        if {"valor_centavos", "conta_id"} & mudancas.keys():
            _conferir_estorno(conn, id, editado, atual.estorno_de)
    if atual.estorno_avulso and (
        editado.tipo != "despesa" or not faturas.ler_cartao(conn, editado.conta_id)
    ):
        raise recusar("estorno é um crédito no cartão")
    momento = _momento(alteracao.acao_em)
    ja_ligadas = frozenset(atual.categoria_ids) | categorias_das_partes(conn, id)
    conferir_ligacoes(conn, editado, atual.conta_id, ja_ligadas)
    mes, a_mao = _fatura_depois(conn, atual, editado, mudancas)
    item_atual = _item_atual_depois(conn, id, editado)
    versao = subir_versao(
        conn,
        id,
        atual.versao,
        "tipo = %s, situacao = %s, valor_centavos = %s, data = %s, descricao = %s,"
        " conta_id = %s, pessoa = %s, mes = %s, fatura_a_mao = %s, item_categoria_id = %s,"
        " item_atual_categoria_id = %s, alterado_por = %s, alterado_em = %s",
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
            editado.item_categoria_id,
            item_atual,
            usuario,
            momento,
        ),
    )
    registrar_mudancas(conn, id, mudancas, versao, usuario, momento)
    if "categoria_ids" in mudancas:
        gravar_categorias(conn, id, editado.categoria_ids)
    if "tags" in mudancas:
        _gravar_tags(conn, id, editado.tags, usuario)
    if "partes" in mudancas:
        gravar_partes(conn, id, editado.partes, usuario)
    acompanhar_estornos(conn, id)
    return _um(conn, id)


def _o_que_as_partes_mudam(partes: list[Parte], pedidas: dict) -> dict:
    """Os campos que mudam com as partes pedidas, para valerem também no conflito: dividir tira a
    classificação própria da compra; uma parte só (tirar a penúltima) devolve a dela à compra,
    que volta a ser uma, com o valor dela. Sem partes, a compra volta a ser uma com a
    classificação que o pedido traz."""
    if not partes:
        if not pedidas.get("categoria_ids"):
            raise recusar("sem as partes, a compra volta a ter categoria: mande as categorias dela")
        return {"partes": []}
    if len(partes) == 1:
        [fica] = partes
        return {
            "partes": [],
            "categoria_ids": fica.categoria_ids,
            "tags": fica.tags,
            "pessoa": fica.pessoa,
            "item_categoria_id": fica.item_categoria_id,
        }
    if any(pedidas.get(c) for c in ("categoria_ids", "tags", "pessoa", "item_categoria_id")):
        raise recusar(SEM_CLASSIFICACAO_PROPRIA)
    return {
        "partes": partes,
        "categoria_ids": [],
        "tags": [],
        "pessoa": None,
        "item_categoria_id": None,
    }


def _conferir_compra_com_partes(conn, atual: Lancamento, editado: DadosDoLancamento) -> None:
    """A compra com partes depois da mudança: sem classificação própria, com as partes somando o
    valor dela, à vista (a parcela e a recorrência têm partes nos tickets 139 e 140) e sem estorno
    (o estorno de uma parte é do ticket 138)."""
    if editado.categoria_ids or editado.tags or editado.pessoa or editado.item_categoria_id:
        raise recusar(SEM_CLASSIFICACAO_PROPRIA)
    try:
        conferir_partes(editado.partes, editado.valor_centavos, editado.tipo)
    except ValueError as e:
        raise recusar(str(e))
    if atual.parcelamento_id or atual.recorrencia_id:
        raise recusar(SO_A_VISTA)
    if atual.estorno_de or atual.estorno_avulso:
        raise recusar("estorno não tem partes")
    if conn.execute(
        "SELECT 1 FROM lancamentos WHERE estorno_de = %s AND excluido_em IS NULL LIMIT 1",
        (atual.id,),
    ).fetchone():
        raise recusar("a compra tem estorno; exclua o estorno antes de dividi-la em partes")


def _parte_normalizada(parte) -> tuple:
    p = parte if isinstance(parte, Parte) else Parte.model_construct(**parte)
    return (
        str(p.id),
        p.descricao,
        p.valor_centavos,
        frozenset(map(str, p.categoria_ids)),
        frozenset(t.casefold() for t in p.tags),
        p.pessoa or None,
        p.item_categoria_id and str(p.item_categoria_id),
    )


def conferir_sem_estorno(conn, ids: list[UUID]) -> None:
    """A compra com estorno não se exclui: exclui-se o estorno antes (ticket 133, ADR 0016)."""
    if conn.execute(
        "SELECT 1 FROM lancamentos WHERE estorno_de = ANY(%s) AND excluido_em IS NULL LIMIT 1",
        (ids,),
    ).fetchone():
        raise recusar("a compra tem estorno; exclua o estorno antes")


def excluir(
    conn, id: UUID, versao: int | None, usuario: str, acao_em: datetime | None = None
) -> None:
    """Marca a exclusão: sem a marca, a edição que chega depois não saberia que perdeu para
    ela. Com `versao`, excluir o que o outro lado mudou depois é conflito."""
    linha = conn.execute(
        f"SELECT {VERSAO}, excluido_em FROM lancamentos WHERE id = %s", (id,)
    ).fetchone()
    if not linha:
        return
    if not linha[1]:
        conferir_sem_estorno(conn, [id])
    if linha[1]:
        # A pessoa que exclui o que a regra da recorrência já tirou (a exclusão que estava
        # offline) pulou o mês: a geração não o traz de volta.
        conn.execute("UPDATE lancamentos SET excluido_pela_regra = false WHERE id = %s", (id,))
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
    apagar_partes(conn, [id], so_as_ligacoes=True)


def na_rota[T](
    request: Request, trabalho: Callable[..., T], corrigida: tuple[UUID, date] | None = None
) -> T | JSONResponse:
    """Uma rota de lançamentos, com as regras da fatura paga (só a `corrigida` muda, na correção
    de fatura): o conflito vira 409 e a exclusão que venceu, 410."""
    from app import cartoes

    try:
        return em_transacao(url_do_banco(request), cartoes.protegida(trabalho, corrigida))
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
        criado, gravado = criar(conn, novo, usuario)
        response.status_code = 201 if gravado else 200
        return criado

    return na_rota(request, gravar)


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
    partes = ler_partes(conn, ids if filtro else None)
    dia = hoje()
    return [
        Lancamento(
            id=l[0],
            tipo=l[1],
            situacao=l[2],
            atrasado=l[2] == "previsto" and l[4] < dia and not l[16],
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
            recorrencia_id=l[14],
            ocorrencia=l[15],
            automatico=l[16],
            parece_repetido_de=l[17],
            mes=l[18],
            fatura_mes=l[18] if l[19] else None,
            estorno_de=l[20],
            parcelamento_id=l[21],
            parcela=l[22],
            parcelas=l[23],
            item_categoria_id=l[24],
            alterada_a_mao=l[25],
            estorno_avulso=l[26],
            partes=partes.get(l[0], []),
        )
        for l in linhas
    ]


def ler_partes(conn, ids: list[UUID] | None = None) -> dict[UUID, list[Parte]]:
    """As partes de cada lançamento, na ordem; sem `ids`, as de todos."""
    filtro = "WHERE p.lancamento_id = ANY(%s)" if ids is not None else ""
    parametros = (ids,) if ids is not None else ()
    linhas = conn.execute(
        "SELECT p.id, p.lancamento_id, p.descricao, p.valor_centavos, p.pessoa,"
        f" p.item_categoria_id FROM lancamento_partes p {filtro} ORDER BY p.lancamento_id, p.ordem",
        parametros,
    ).fetchall()
    if not linhas:
        return {}
    categorias: dict[UUID, list[UUID]] = {}
    for parte_id, categoria_id in conn.execute(
        "SELECT pc.parte_id, pc.categoria_id FROM parte_categorias pc"
        f" JOIN lancamento_partes p ON p.id = pc.parte_id {filtro} ORDER BY pc.categoria_id",
        parametros,
    ):
        categorias.setdefault(parte_id, []).append(categoria_id)
    tags: dict[UUID, list[str]] = {}
    for parte_id, nome in conn.execute(
        "SELECT pt.parte_id, t.nome FROM parte_tags pt JOIN tags t ON t.id = pt.tag_id"
        f" JOIN lancamento_partes p ON p.id = pt.parte_id {filtro} ORDER BY t.nome",
        parametros,
    ):
        tags.setdefault(parte_id, []).append(nome)
    por_lancamento: dict[UUID, list[Parte]] = {}
    for id, lancamento_id, descricao, valor, pessoa, item in linhas:
        por_lancamento.setdefault(lancamento_id, []).append(
            Parte.model_construct(
                id=id,
                descricao=descricao,
                valor_centavos=valor,
                categoria_ids=categorias.get(id, []),
                tags=tags.get(id, []),
                pessoa=pessoa,
                item_categoria_id=item,
            )
        )
    return por_lancamento


def ler_por_ids(conn, ids: list[UUID]) -> list[Lancamento]:
    """Os lançamentos não excluídos com esses ids."""
    return _todos(conn, "id = ANY(%s)", (ids,))


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
    return na_rota(request, lambda conn: editar(conn, id, alteracao, usuario))


def contas_da_semana_de_hoje(conn) -> list[Lancamento]:
    """Os atrasados e os previstos até `contasDaSemanaDias` dias a partir de hoje."""
    ate = hoje() + timedelta(days=valores_iniciais()["contasDaSemanaDias"])
    return _todos(
        conn,
        "situacao = 'previsto' AND NOT COALESCE(automatico, false) AND data <= %s",
        (ate,),
        ordem="data, criado_em, id",
    )


class Confirmacao(BaseModel):
    """O que de fato aconteceu; campo ausente fica como estava no previsto. Com `versao`, o
    ajuste num campo que o outro lado mudou depois dela é conflito, como na edição."""

    versao: int | None = Field(default=None, ge=0)
    valor_centavos: int | None = Field(default=None, gt=0)
    data: date | None = None
    conta_id: UUID | None = None
    acao_em: datetime | None = None


def confirmar(conn, id: UUID, confirmacao: Confirmacao, usuario: str) -> Lancamento:
    """O previsto vira realizado com os ajustes; serve à rota e à fila (ticket 83)."""
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
    if mes != atual.mes:
        guardar_item_atual_do_lancamento(conn, id)  # no mês novo, fica no item em que estava
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
    return na_rota(request, lambda conn: confirmar(conn, id, confirmacao, usuario))


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
    resposta = na_rota(request, lambda conn: excluir(conn, id, versao, usuario, acao_em))
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

    return na_rota(request, gravar)
