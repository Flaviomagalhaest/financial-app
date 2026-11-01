"""A busca em todo o histórico (ticket 24, ADR 0013): texto livre e filtros combinados, entre
filtros E, dentro de um filtro OU. Roda no servidor; sem internet, o aparelho filtra só o que
guarda (`web/src/dados/busca.ts`)."""

import unicodedata
from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import faturas, transferencias
from app.banco import conectar
from app.config import valores_iniciais
from app.lancamentos import MES_EM_QUE_CONTA, Lancamento, ler_por_ids, url_do_banco
from app.login import UsuarioLogado
from app.transferencias import Transferencia

router = APIRouter(prefix="/api")

# Linhas por página; a lista não tem teto, a página seguinte continua.
POR_PAGINA: int = valores_iniciais()["buscaPorPagina"]


class FiltroDeFatura(BaseModel):
    """O mês da fatura de um cartão (com as compras dos adicionais dele). Sem cartão, o mês em que
    cada lançamento conta, como na aba Mês: o da fatura no cartão, o da data no resto (ADR 0003)."""

    model_config = ConfigDict(extra="forbid")

    mes: date
    cartao_id: UUID | None = None

    _mes = field_validator("mes")(lambda mes: faturas.mes_de(mes))


class CriteriosDaBusca(BaseModel):
    """Sem um filtro, ele não restringe; um filtro vazio também não."""

    model_config = ConfigDict(extra="forbid")

    # Na descrição, sem acento nem maiúscula.
    texto: str = ""
    valor_minimo_centavos: int | None = Field(default=None, ge=0)
    valor_maximo_centavos: int | None = Field(default=None, ge=0)
    categoria_ids: list[UUID] = []
    # Pelo nome, sem distinguir maiúsculas.
    tags: list[str] = []
    # Somam ao filtro de categorias e ao de tags o que não tem nenhuma.
    sem_categoria: bool = False
    sem_tag: bool = False
    # Contas e cartões.
    conta_ids: list[UUID] = []
    # O id de uma pessoa do casal; `conjunto` soma o que não é de ninguém.
    pessoas: list[str] = []
    conjunto: bool = False
    # Pela data da compra no cartão e pela do lançamento no resto, com os dois dias (ADR 0013).
    periodo_de: date | None = None
    periodo_ate: date | None = None
    fatura: FiltroDeFatura | None = None
    situacoes: list[Literal["previsto", "realizado"]] = []
    tipos: list[Literal["despesa", "receita", "transferencia"]] = []


class ParcelamentoNaBusca(BaseModel):
    """O parcelamento numa linha só, fora do filtro Fatura (ADR 0013)."""

    parcelamento_id: UUID
    descricao: str
    # A data da compra (no boleto, a da 1ª parcela).
    data: date
    # Quantas parcelas o parcelamento tem (o 10 de 3/10).
    parcelas: int
    # A soma das parcelas que a busca achou: o total da compra, se nenhum filtro tirou parcela.
    valor_centavos: int
    # As parcelas que a busca achou, pelo número.
    lancamentos: list[Lancamento]


class PedidoDeBusca(CriteriosDaBusca):
    # A mais recente primeiro (pela data da compra) ou a de maior valor.
    ordem: Literal["recentes", "valor"] = "recentes"
    # A partir de 0.
    pagina: int = Field(default=0, ge=0)


_ORDENS = {
    "recentes": "data DESC, criado_em DESC, chave",
    "valor": "valor DESC, data DESC, criado_em DESC, chave",
}


class LinhaDaBusca(BaseModel):
    """Uma linha do resultado: um lançamento, um parcelamento ou uma transferência."""

    lancamento: Lancamento | None = None
    # Com filtro de categoria, tag ou pessoa, as partes da compra que batem com ele (ADR 0022): a
    # linha vale a soma delas. Sem filtro, ou sem partes, não há.
    partes_achadas: list[UUID] | None = None
    parcelamento: ParcelamentoNaBusca | None = None
    transferencia: Transferencia | None = None


class PorSituacao(BaseModel):
    realizado_centavos: int
    previsto_centavos: int


class TotaisDaBusca(BaseModel):
    """O resumo do resultado inteiro, não só da página. A transferência fica fora das somas; o
    estorno diminui as despesas; o parcelamento conta uma vez, pelas parcelas achadas."""

    # As linhas do resultado, sem as transferências: o parcelamento conta como uma.
    quantidade: int
    despesas: PorSituacao
    receitas: PorSituacao
    # As receitas menos as despesas.
    saldo: PorSituacao


class ResultadoDaBusca(BaseModel):
    totais: TotaisDaBusca
    # As linhas da página pedida.
    linhas: list[LinhaDaBusca]
    # Há outra página depois desta.
    tem_mais: bool


_COM_ACENTO = "ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑáàâãäéèêëíìîïóòôõöúùûüçñ"
_SEM_ACENTO = "AAAAAEEEEIIIIOOOOOUUUUCNaaaaaeeeeiiiiooooouuuucn"


def _sem_acento(coluna: str) -> str:
    """A coluna como a busca compara: sem acento e em minúsculas."""
    return f"lower(translate({coluna}, '{_COM_ACENTO}', '{_SEM_ACENTO}'))"


def _normalizado(texto: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c)
    )
    return " ".join(sem_acento.lower().split())


def _como_padrao(texto: str) -> str:
    """O texto como trecho de um LIKE, com os curingas escapados."""
    escapado = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escapado}%"


class _Filtro:
    """As condições (E) de uma tabela e os parâmetros delas, na ordem. `de` é a tabela (com o que
    se junta a ela, e os parâmetros disso em `parametros_do_de`) e `valor`, o valor de cada linha."""

    def __init__(self, *condicoes: str) -> None:
        self.condicoes, self.parametros = list(condicoes), []
        self.de, self.parametros_do_de, self.valor = "lancamentos", [], "lancamentos.valor_centavos"

    @property
    def todos_os_parametros(self) -> list:
        return [*self.parametros_do_de, *self.parametros]

    def exigir(self, condicao: str, *parametros) -> None:
        self.condicoes.append(condicao)
        self.parametros.extend(parametros)

    @property
    def sql(self) -> str:
        return " AND ".join(self.condicoes)


# A classificação de um lançamento sem partes ou de uma parte (ADR 0022): as tabelas e colunas.
_DO_LANCAMENTO = {
    "categorias": "lancamento_categorias x WHERE x.lancamento_id = lancamentos.id",
    "tags": "lancamento_tags x WHERE x.lancamento_id = lancamentos.id",
    "pessoa": "lancamentos.pessoa",
}
_DA_PARTE = {
    "categorias": "parte_categorias x WHERE x.parte_id = p.id",
    "tags": "parte_tags x WHERE x.parte_id = p.id",
    "pessoa": "p.pessoa",
}
_TEM_PARTES = "EXISTS (SELECT FROM lancamento_partes p WHERE p.lancamento_id = lancamentos.id)"
_DO_CARTAO = "IN (SELECT id FROM cartoes WHERE %s IN (id, titular_id))"


def _texto(criterios: CriteriosDaBusca, filtro: _Filtro, tabela: str) -> None:
    if texto := _normalizado(criterios.texto):
        padrao = f"{_sem_acento(f'{tabela}.descricao')} LIKE %s ESCAPE '\\'"
        if tabela != "lancamentos":
            filtro.exigir(padrao, _como_padrao(texto))
            return
        # A compra também se acha pela descrição de uma parte dela.
        filtro.exigir(
            f"({padrao} OR EXISTS (SELECT FROM lancamento_partes p"
            f" WHERE p.lancamento_id = lancamentos.id"
            f" AND {_sem_acento('p.descricao')} LIKE %s ESCAPE '\\'))",
            _como_padrao(texto),
            _como_padrao(texto),
        )


def _da_classificacao(criterios: CriteriosDaBusca, de: dict[str, str]) -> _Filtro | None:
    """Os filtros de categoria, tag e pessoa sobre um lançamento sem partes ou uma parte; sem
    nenhum deles, não há."""
    filtro = _Filtro()
    if criterios.categoria_ids or criterios.sem_categoria:
        filtro.exigir(
            _qualquer(
                criterios.categoria_ids
                and f"EXISTS (SELECT FROM {de['categorias']} AND x.categoria_id = ANY(%s))",
                criterios.sem_categoria and f"NOT EXISTS (SELECT FROM {de['categorias']})",
            ),
            *[criterios.categoria_ids] * bool(criterios.categoria_ids),
        )
    if criterios.tags or criterios.sem_tag:
        filtro.exigir(
            _qualquer(
                criterios.tags
                and f"EXISTS (SELECT FROM {de['tags']} AND x.tag_id IN"
                " (SELECT id FROM tags WHERE lower(nome) = ANY(%s)))",
                criterios.sem_tag and f"NOT EXISTS (SELECT FROM {de['tags']})",
            ),
            *[[t.strip().lower() for t in criterios.tags]] * bool(criterios.tags),
        )
    if criterios.pessoas or criterios.conjunto:
        filtro.exigir(
            _qualquer(
                criterios.pessoas and f"{de['pessoa']} = ANY(%s)",
                criterios.conjunto and f"{de['pessoa']} IS NULL",
            ),
            *[criterios.pessoas] * bool(criterios.pessoas),
        )
    return filtro if filtro.condicoes else None


def _do_lancamento(criterios: CriteriosDaBusca) -> _Filtro:
    filtro = _Filtro("lancamentos.excluido_em IS NULL")
    _texto(criterios, filtro, "lancamentos")
    if do_lancamento := _da_classificacao(criterios, _DO_LANCAMENTO):
        # A compra com partes bate pelas partes que batem com todos os filtros de classificação,
        # e vale a soma delas (ADR 0022).
        da_parte = _da_classificacao(criterios, _DA_PARTE)
        assert da_parte
        filtro.de = (
            "lancamentos LEFT JOIN LATERAL (SELECT sum(p.valor_centavos) AS valor,"
            " array_agg(p.id ORDER BY p.ordem) AS ids FROM lancamento_partes p"
            f" WHERE p.lancamento_id = lancamentos.id AND {da_parte.sql}) achadas ON true"
        )
        filtro.parametros_do_de = da_parte.parametros
        filtro.valor = "COALESCE(achadas.valor, lancamentos.valor_centavos)"
        filtro.exigir(
            f"(achadas.ids IS NOT NULL OR (NOT {_TEM_PARTES} AND {do_lancamento.sql}))",
            *do_lancamento.parametros,
        )
    if criterios.conta_ids:
        filtro.exigir("lancamentos.conta_id = ANY(%s)", criterios.conta_ids)
    if criterios.periodo_de:
        filtro.exigir(f"{_data_da_linha(criterios)} >= %s", criterios.periodo_de)
    if criterios.periodo_ate:
        filtro.exigir(f"{_data_da_linha(criterios)} <= %s", criterios.periodo_ate)
    if fatura := criterios.fatura:
        filtro.exigir(f"{MES_EM_QUE_CONTA} = %s", fatura.mes)
        if fatura.cartao_id:
            filtro.exigir(f"lancamentos.conta_id {_DO_CARTAO}", fatura.cartao_id)
    if criterios.situacoes:
        filtro.exigir("lancamentos.situacao = ANY(%s)", criterios.situacoes)
    if criterios.tipos:
        filtro.exigir("lancamentos.tipo = ANY(%s)", criterios.tipos)
    return filtro


def _da_transferencia(criterios: CriteriosDaBusca) -> _Filtro | None:
    """As transferências que a busca acha; `None` quando um filtro já as tira todas: elas não
    têm tag nem pessoa (são do conjunto). O pagamento de fatura só vem com o tipo transferência,
    e o filtro Fatura só acha pagamento de fatura."""
    if criterios.tipos and "transferencia" not in criterios.tipos:
        return None
    if (criterios.tags and not criterios.sem_tag) or (criterios.pessoas and not criterios.conjunto):
        return None
    filtro = _Filtro()
    if not criterios.tipos:
        filtro.exigir(
            "NOT EXISTS (SELECT FROM cartoes WHERE cartoes.id = transferencias.conta_destino_id)"
        )
    _texto(criterios, filtro, "transferencias")
    if criterios.categoria_ids or criterios.sem_categoria:
        filtro.exigir(
            _qualquer(
                criterios.categoria_ids and "transferencias.categoria_id = ANY(%s)",
                criterios.sem_categoria and "transferencias.categoria_id IS NULL",
            ),
            *[criterios.categoria_ids] * bool(criterios.categoria_ids),
        )
    if criterios.conta_ids:
        filtro.exigir(
            "(transferencias.conta_origem_id = ANY(%s) OR transferencias.conta_destino_id = ANY(%s))",
            criterios.conta_ids,
            criterios.conta_ids,
        )
    if criterios.periodo_de:
        filtro.exigir("transferencias.data >= %s", criterios.periodo_de)
    if criterios.periodo_ate:
        filtro.exigir("transferencias.data <= %s", criterios.periodo_ate)
    if fatura := criterios.fatura:
        filtro.exigir("transferencias.fatura_mes = %s", fatura.mes)
        if fatura.cartao_id:
            filtro.exigir(f"transferencias.conta_destino_id {_DO_CARTAO}", fatura.cartao_id)
    if criterios.situacoes:
        filtro.exigir("transferencias.situacao = ANY(%s)", criterios.situacoes)
    return filtro


def _agrupar(criterios: CriteriosDaBusca) -> bool:
    """Fora do filtro Fatura, o parcelamento é uma linha; nele, cada parcela é uma."""
    return criterios.fatura is None


def _data_da_linha(criterios: CriteriosDaBusca) -> str:
    """A data da compra: a do parcelamento quando ele é uma linha (no boleto, a 1ª parcela)."""
    if not _agrupar(criterios):
        return "lancamentos.data"
    return (
        "COALESCE((SELECT p.data FROM parcelamentos p"
        " WHERE p.id = lancamentos.parcelamento_id), lancamentos.data)"
    )


def _filtro_de_valor(criterios: CriteriosDaBusca) -> tuple[str, list]:
    """O valor da linha: a soma das parcelas do parcelamento, ou o da parcela no filtro Fatura."""
    condicoes, parametros = [], []
    if criterios.valor_minimo_centavos is not None:
        condicoes.append("valor >= %s")
        parametros.append(criterios.valor_minimo_centavos)
    if criterios.valor_maximo_centavos is not None:
        condicoes.append("valor <= %s")
        parametros.append(criterios.valor_maximo_centavos)
    return " AND ".join(condicoes) or "true", parametros


def _qualquer(*condicoes: str | bool) -> str:
    """Dentro de um filtro é OU."""
    return "(" + " OR ".join(c for c in condicoes if c) + ")"


def _soma(tipo: str, situacao: str, valor: str) -> str:
    if tipo == "despesa":
        valor = f"CASE WHEN lancamentos.estorno_de IS NULL THEN {valor} ELSE -{valor} END"
    return (
        f"COALESCE(sum(CASE WHEN lancamentos.tipo = '{tipo}'"
        f" AND lancamentos.situacao = '{situacao}' THEN {valor} END), 0)"
    )


_SOMAS = [(t, s) for t in ("despesa", "receita") for s in ("realizado", "previsto")]


def _linhas(criterios: CriteriosDaBusca) -> tuple[str, list]:
    """Uma linha por lançamento, parcelamento ou transferência, com o valor dela e as somas."""
    do_lancamento, da_transferencia = _do_lancamento(criterios), _da_transferencia(criterios)
    agrupar = _agrupar(criterios)
    chave = "COALESCE(lancamentos.parcelamento_id, lancamentos.id)" if agrupar else "lancamentos.id"
    parcelado = "bool_or(lancamentos.parcelamento_id IS NOT NULL)" if agrupar else "false"
    somas = ", ".join(f"{_soma(t, s, do_lancamento.valor)} AS {t}_{s}" for t, s in _SOMAS)
    # A transferência é uma linha, fora das somas.
    transferencias_sql, parametros_das_transferencias = "", []
    if da_transferencia:
        transferencias_sql = (
            " UNION ALL SELECT id, false, true, data, criado_em, valor_centavos,"
            f" {', '.join('0' for _ in _SOMAS)} FROM transferencias"
            f" WHERE {da_transferencia.sql or 'true'}"
        )
        parametros_das_transferencias = da_transferencia.parametros
    valor, parametros_do_valor = _filtro_de_valor(criterios)
    linhas = (
        f"(SELECT * FROM ("
        f" SELECT {chave} AS chave, {parcelado} AS parcelado, false AS transferencia,"
        f" min({_data_da_linha(criterios)}) AS data, max(lancamentos.criado_em) AS criado_em,"
        f" sum({do_lancamento.valor}) AS valor, {somas}"
        f" FROM {do_lancamento.de} WHERE {do_lancamento.sql} GROUP BY 1"
        f"{transferencias_sql}"
        f") todas WHERE {valor}) linhas"
    )
    return linhas, [
        *do_lancamento.todos_os_parametros,
        *parametros_das_transferencias,
        *parametros_do_valor,
    ]


def lancamentos_do_resultado(conn, criterios: CriteriosDaBusca) -> tuple[list[UUID], list[UUID]]:
    """O resultado inteiro, sem página e sem as transferências: os lançamentos avulsos e os
    parcelamentos que ele traz (a edição em lote, ticket 61)."""
    linhas, parametros = _linhas(criterios)
    avulsos, parcelamentos = [], []
    for chave, parcelado in conn.execute(
        f"SELECT chave, parcelado FROM {linhas} WHERE NOT transferencia", parametros
    ):
        (parcelamentos if parcelado else avulsos).append(chave)
    return avulsos, parcelamentos


def buscar(conn, criterios: PedidoDeBusca) -> ResultadoDaBusca:
    do_lancamento = _do_lancamento(criterios)
    linhas, parametros_das_linhas = _linhas(criterios)
    quantidade, *centavos = conn.execute(
        f"SELECT count(*) FILTER (WHERE NOT transferencia), {', '.join(f'COALESCE(sum({t}_{s}), 0)::bigint' for t, s in _SOMAS)}"
        f" FROM {linhas}",
        parametros_das_linhas,
    ).fetchone()
    soma = dict(zip(_SOMAS, centavos))
    pagina = conn.execute(
        f"SELECT chave, parcelado, transferencia FROM {linhas} ORDER BY {_ORDENS[criterios.ordem]}"
        " LIMIT %s OFFSET %s",
        [*parametros_das_linhas, POR_PAGINA + 1, criterios.pagina * POR_PAGINA],
    ).fetchall()
    tem_mais = len(pagina) > POR_PAGINA
    pagina = pagina[:POR_PAGINA]
    parcelamentos = _parcelamentos(conn, do_lancamento, [c for c, e_parc, _ in pagina if e_parc])
    avulsos = [c for c, e_parc, e_transferencia in pagina if not e_parc and not e_transferencia]
    por_id = {l.id: l for l in ler_por_ids(conn, avulsos)}
    achadas = _partes_achadas(conn, do_lancamento, [i for i, l in por_id.items() if l.partes])
    das_transferencias = {
        t.id: t for t in transferencias.ler_por_ids(conn, [c for c, _, e in pagina if e])
    }
    return ResultadoDaBusca(
        totais=TotaisDaBusca(
            quantidade=quantidade,
            despesas=_por_situacao(soma, "despesa"),
            receitas=_por_situacao(soma, "receita"),
            saldo=PorSituacao(
                **{
                    f"{s}_centavos": soma["receita", s] - soma["despesa", s]
                    for s in ("realizado", "previsto")
                }
            ),
        ),
        linhas=[
            LinhaDaBusca(parcelamento=parcelamentos[c])
            if e_parc
            else LinhaDaBusca(transferencia=das_transferencias[c])
            if e_transferencia
            else LinhaDaBusca(lancamento=por_id[c], partes_achadas=achadas.get(c))
            for c, e_parc, e_transferencia in pagina
        ],
        tem_mais=tem_mais,
    )


def _partes_achadas(conn, do_lancamento: _Filtro, ids: list[UUID]) -> dict[UUID, list[UUID]]:
    """Das compras com partes, as partes que batem com os filtros de classificação."""
    if not ids or do_lancamento.de == "lancamentos":
        return {}
    return dict(
        conn.execute(
            f"SELECT lancamentos.id, achadas.ids FROM {do_lancamento.de}"
            " WHERE lancamentos.id = ANY(%s) AND achadas.ids IS NOT NULL",
            [*do_lancamento.parametros_do_de, ids],
        ).fetchall()
    )


def _por_situacao(soma: dict[tuple[str, str], int], tipo: str) -> PorSituacao:
    return PorSituacao(
        realizado_centavos=soma[tipo, "realizado"], previsto_centavos=soma[tipo, "previsto"]
    )


def _parcelamentos(
    conn, do_lancamento: _Filtro, ids: list[UUID]
) -> dict[UUID, ParcelamentoNaBusca]:
    """Os parcelamentos, com as parcelas que a busca achou."""
    if not ids:
        return {}
    achadas = [
        id
        for (id,) in conn.execute(
            f"SELECT lancamentos.id FROM {do_lancamento.de} WHERE {do_lancamento.sql}"
            " AND lancamentos.parcelamento_id = ANY(%s)",
            [*do_lancamento.todos_os_parametros, ids],
        )
    ]
    parcelas: dict[UUID, list[Lancamento]] = {}
    for parcela in sorted(ler_por_ids(conn, achadas), key=lambda l: l.parcela or 0):
        parcelas.setdefault(parcela.parcelamento_id, []).append(parcela)
    return {
        id: ParcelamentoNaBusca(
            parcelamento_id=id,
            descricao=descricao,
            data=data,
            parcelas=total,
            valor_centavos=sum(p.valor_centavos for p in parcelas[id]),
            lancamentos=parcelas[id],
        )
        for id, descricao, data, total in conn.execute(
            "SELECT id, descricao, data, parcelas FROM parcelamentos WHERE id = ANY(%s)", (ids,)
        )
    }


@router.post("/busca", response_model=ResultadoDaBusca, operation_id="buscar")
def buscar_lancamentos(
    criterios: PedidoDeBusca, usuario: UsuarioLogado, request: Request
) -> ResultadoDaBusca:
    with conectar(url_do_banco(request)) as conn:
        return buscar(conn, criterios)
