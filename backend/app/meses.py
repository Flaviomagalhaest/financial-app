"""As despesas de um mês, para as telas do mês e do fechamento. Despesa conta pelo mês em que o
lançamento conta (no cartão, o da fatura, ADR 0003); o estorno diminui; o ajuste de fatura entra
nas despesas do mês, mas não em categoria nem em tag (ADR 0008)."""

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import faturas, lancamentos
from app.banco import conectar
from app.lancamentos import MES_EM_QUE_CONTA, VALOR_COM_SINAL, url_do_banco
from app.login import UsuarioLogado
from app.planejamento import Mes, Planejamento, planejamento_do_mes, primeiro_dia

router = APIRouter(prefix="/api")


class TotalDeCategoria(BaseModel):
    categoria_id: UUID
    centavos: int


class TotalDeTag(BaseModel):
    tag: str
    centavos: int


class TotaisDoMes(BaseModel):
    mes: str
    # As compras (menos os estornos) e os ajustes de fatura do mês; transferência e pagamento de
    # fatura não entram.
    despesas_centavos: int
    # A parte das despesas que é ajuste de fatura, sem categoria nem tag.
    ajustes_de_fatura_centavos: int
    por_categoria: list[TotalDeCategoria]
    por_tag: list[TotalDeTag]


# Despesa do mês: a que não foi excluída, no mês em que conta. A receita fica de fora.
_DESPESAS_DO_MES = (
    f"FROM lancamentos WHERE lancamentos.excluido_em IS NULL AND lancamentos.tipo = 'despesa'"
    f" AND {MES_EM_QUE_CONTA} = %s"
)


def _totais(conn, mes: str) -> TotaisDoMes:
    dia = primeiro_dia(mes)
    (compras,) = conn.execute(
        f"SELECT COALESCE(SUM({VALOR_COM_SINAL}), 0)::bigint {_DESPESAS_DO_MES}", (dia,)
    ).fetchone()
    ajustes = faturas.ajustes_do_mes(conn, dia)
    por_categoria = conn.execute(
        f"SELECT lc.categoria_id, SUM({VALOR_COM_SINAL})::bigint AS centavos"
        f" FROM lancamento_categorias lc JOIN lancamentos ON lancamentos.id = lc.lancamento_id"
        f" WHERE lancamentos.excluido_em IS NULL AND lancamentos.tipo = 'despesa'"
        f" AND {MES_EM_QUE_CONTA} = %s GROUP BY lc.categoria_id"
        f" ORDER BY centavos DESC, lc.categoria_id",
        (dia,),
    ).fetchall()
    por_tag = conn.execute(
        f"SELECT t.nome, SUM({VALOR_COM_SINAL})::bigint AS centavos"
        f" FROM lancamento_tags lt JOIN lancamentos ON lancamentos.id = lt.lancamento_id"
        f" JOIN tags t ON t.id = lt.tag_id"
        f" WHERE lancamentos.excluido_em IS NULL AND lancamentos.tipo = 'despesa'"
        f" AND {MES_EM_QUE_CONTA} = %s GROUP BY t.nome ORDER BY centavos DESC, t.nome",
        (dia,),
    ).fetchall()
    return TotaisDoMes(
        mes=mes,
        despesas_centavos=compras + ajustes,
        ajustes_de_fatura_centavos=ajustes,
        por_categoria=[TotalDeCategoria(categoria_id=c, centavos=v) for c, v in por_categoria],
        por_tag=[TotalDeTag(tag=t, centavos=v) for t, v in por_tag],
    )


@router.get("/meses/{mes}/totais", response_model=TotaisDoMes, operation_id="ler_totais_do_mes")
def ler_totais(mes: Mes, usuario: UsuarioLogado, request: Request) -> TotaisDoMes:
    with conectar(url_do_banco(request)) as conn:
        return _totais(conn, mes)


class Despesas(BaseModel):
    # As despesas do mês (compras menos estornos), e os ajustes de fatura no realizado.
    realizado_centavos: int
    previsto_centavos: int
    # A soma dos itens do planejamento de categorias de despesa.
    planejado_centavos: int
    # O planejado que sobra depois do realizado e do previsto; nunca abaixo de zero.
    livre_centavos: int


class Receitas(BaseModel):
    realizado_centavos: int
    previsto_centavos: int


class Comparado(BaseModel):
    mes_centavos: int
    anterior_centavos: int
    ano_passado_centavos: int


class LinhaDaComparacao(Comparado):
    categoria_id: UUID


class Comparacao(BaseModel):
    """As despesas do mês por categoria contra o mês anterior e o mesmo mês do ano passado, com o
    realizado e o previsto. O lançamento com várias categorias conta inteiro em cada linha, e o
    total o conta uma vez (com os ajustes de fatura), então as linhas somam mais que o total."""

    anterior: str
    ano_passado: str
    linhas: list[LinhaDaComparacao]
    total: Comparado


class LinhaDoRanking(BaseModel):
    # A categoria (id), a tag (nome) ou a pessoa (id; vazia é o conjunto).
    chave: str | None
    centavos: int
    # Os lançamentos da linha, por data, para a folha que a linha abre.
    lancamento_ids: list[UUID]


class Ranking(BaseModel):
    """Para onde foram as despesas do mês (realizado e previsto, sem o ajuste de fatura), da
    linha maior à menor. Por categoria e por tag o lançamento conta inteiro em cada uma que tem;
    por pessoa, uma vez."""

    por_categoria: list[LinhaDoRanking]
    por_tag: list[LinhaDoRanking]
    por_pessoa: list[LinhaDoRanking]


class ItemAcima(BaseModel):
    categoria_id: UUID
    # O realizado e o previsto que passaram do planejado.
    passou_centavos: int


class Fechamento(BaseModel):
    """O fechamento do mês (glossário), para o texto corrido do mês que já passou. Receitas e
    despesas levam o realizado e o previsto que ficou sem confirmar (`previstos` diz quantos)."""

    receitas_centavos: int
    despesas_centavos: int
    sobra_centavos: int
    # A sobra sobre as receitas, arredondada; sem receitas, não há.
    sobra_percentual: int | None
    # As transferências com categoria (guardar na reserva); o pagamento de fatura não tem.
    guardado_centavos: int
    previstos: int
    # Os itens de despesa que passaram do planejado, do que mais passou ao que menos passou.
    itens_acima: list[ItemAcima]
    itens_de_despesa: int
    # As despesas contra as do mês anterior e as do mesmo mês do ano passado; sem despesa lá, não há.
    variacao_anterior_percentual: int | None
    variacao_ano_passado_percentual: int | None


class LeituraDoMes(BaseModel):
    """Tudo o que a aba Mês mostra de um mês, numa leitura só."""

    mes: str
    # Pelo dia de hoje em São Paulo: o passado mostra o fechamento; o atual e o futuro, a barra.
    situacao: Literal["passado", "atual", "futuro"]
    despesas: Despesas
    receitas: Receitas
    # Os itens do mês e a lista "a escolher", como em `GET /api/planejamento/{mes}`.
    planejamento: Planejamento
    comparacao: Comparacao
    ranking: Ranking
    # Só no mês que já passou.
    fechamento: Fechamento | None


def _por_situacao(conn, tipo: str, dia) -> dict[str, int]:
    somas = {"realizado": 0, "previsto": 0}
    for situacao, centavos in conn.execute(
        f"SELECT situacao, SUM({VALOR_COM_SINAL if tipo == 'despesa' else 'valor_centavos'})"
        f"::bigint FROM lancamentos WHERE excluido_em IS NULL AND tipo = %s"
        f" AND {MES_EM_QUE_CONTA} = %s GROUP BY situacao",
        (tipo, dia),
    ):
        somas[situacao] = centavos
    return somas


def _outro_mes(dia: date, meses: int) -> str:
    """`AAAA-MM` do mês `meses` meses depois (antes, se negativo) de `dia`."""
    indice = dia.year * 12 + dia.month - 1 + meses
    return f"{indice // 12:04d}-{indice % 12 + 1:02d}"


def _comparacao(conn, dia: date) -> Comparacao:
    anterior, ano_passado = _outro_mes(dia, -1), _outro_mes(dia, -12)
    periodos = [_totais(conn, m) for m in (_outro_mes(dia, 0), anterior, ano_passado)]
    por_categoria: dict[UUID, list[int]] = {}
    for posicao, totais in enumerate(periodos):
        for total in totais.por_categoria:
            por_categoria.setdefault(total.categoria_id, [0, 0, 0])[posicao] = total.centavos
    linhas = sorted(
        por_categoria.items(), key=lambda linha: ([-v for v in linha[1]], str(linha[0]))
    )
    return Comparacao(
        anterior=anterior,
        ano_passado=ano_passado,
        linhas=[
            LinhaDaComparacao(
                categoria_id=categoria,
                mes_centavos=valores[0],
                anterior_centavos=valores[1],
                ano_passado_centavos=valores[2],
            )
            for categoria, valores in linhas
        ],
        total=Comparado(
            mes_centavos=periodos[0].despesas_centavos,
            anterior_centavos=periodos[1].despesas_centavos,
            ano_passado_centavos=periodos[2].despesas_centavos,
        ),
    )


def _linhas_do_ranking(grupos: dict[str | None, list[tuple[UUID, int]]]) -> list[LinhaDoRanking]:
    linhas = [
        LinhaDoRanking(
            chave=chave,
            centavos=sum(valor for _, valor in lancamentos_da_linha),
            lancamento_ids=[id for id, _ in lancamentos_da_linha],
        )
        for chave, lancamentos_da_linha in grupos.items()
    ]
    return sorted(linhas, key=lambda linha: (-linha.centavos, linha.chave or ""))


def _ranking(conn, dia: date) -> Ranking:
    despesas = conn.execute(
        f"SELECT lancamentos.id, {VALOR_COM_SINAL}, lancamentos.pessoa {_DESPESAS_DO_MES}"
        " ORDER BY lancamentos.data, lancamentos.criado_em, lancamentos.id",
        (dia,),
    ).fetchall()
    ids = [id for id, _, _ in despesas]
    categorias: dict[UUID, list[UUID]] = {}
    for lancamento_id, categoria_id in conn.execute(
        "SELECT lancamento_id, categoria_id FROM lancamento_categorias"
        " WHERE lancamento_id = ANY(%s)",
        (ids,),
    ):
        categorias.setdefault(lancamento_id, []).append(categoria_id)
    tags: dict[UUID, list[str]] = {}
    for lancamento_id, nome in conn.execute(
        "SELECT lt.lancamento_id, t.nome FROM lancamento_tags lt JOIN tags t ON t.id = lt.tag_id"
        " WHERE lt.lancamento_id = ANY(%s)",
        (ids,),
    ):
        tags.setdefault(lancamento_id, []).append(nome)
    por_categoria: dict[str | None, list[tuple[UUID, int]]] = {}
    por_tag: dict[str | None, list[tuple[UUID, int]]] = {}
    por_pessoa: dict[str | None, list[tuple[UUID, int]]] = {}
    for id, valor, pessoa in despesas:
        for categoria_id in categorias.get(id, []):
            por_categoria.setdefault(str(categoria_id), []).append((id, valor))
        for nome in tags.get(id, []):
            por_tag.setdefault(nome, []).append((id, valor))
        por_pessoa.setdefault(pessoa, []).append((id, valor))
    return Ranking(
        por_categoria=_linhas_do_ranking(por_categoria),
        por_tag=_linhas_do_ranking(por_tag),
        por_pessoa=_linhas_do_ranking(por_pessoa),
    )


def _porcentagem(parte: int, todo: int) -> int | None:
    return round(parte * 100 / todo) if todo else None


def _fechamento(
    conn,
    dia: date,
    despesas: Despesas,
    receitas: Receitas,
    planejamento: Planejamento,
    comparacao: Comparacao,
) -> Fechamento:
    (guardado,) = conn.execute(
        "SELECT COALESCE(SUM(valor_centavos), 0)::bigint FROM transferencias"
        " WHERE categoria_id IS NOT NULL AND data >= %s AND data < %s",
        (dia, primeiro_dia(_outro_mes(dia, 1))),
    ).fetchone()
    (previstos,) = conn.execute(
        f"SELECT count(*) FROM lancamentos WHERE excluido_em IS NULL AND situacao = 'previsto'"
        f" AND {MES_EM_QUE_CONTA} = %s",
        (dia,),
    ).fetchone()
    de_despesa = {
        id
        for (id,) in conn.execute(
            "SELECT id FROM categorias WHERE tipo = 'despesa' AND id = ANY(%s)",
            ([i.categoria_id for i in planejamento.itens],),
        )
    }
    itens = [i for i in planejamento.itens if i.categoria_id in de_despesa]
    acima = sorted(
        (
            ItemAcima(categoria_id=i.categoria_id, passou_centavos=-i.ainda_da_para_gastar_centavos)
            for i in itens
            if i.ainda_da_para_gastar_centavos < 0
        ),
        key=lambda item: (-item.passou_centavos, str(item.categoria_id)),
    )
    total = comparacao.total
    receitas_do_mes = receitas.realizado_centavos + receitas.previsto_centavos
    despesas_do_mes = despesas.realizado_centavos + despesas.previsto_centavos
    return Fechamento(
        receitas_centavos=receitas_do_mes,
        despesas_centavos=despesas_do_mes,
        sobra_centavos=receitas_do_mes - despesas_do_mes,
        sobra_percentual=_porcentagem(receitas_do_mes - despesas_do_mes, receitas_do_mes),
        guardado_centavos=guardado,
        previstos=previstos,
        itens_acima=acima,
        itens_de_despesa=len(itens),
        variacao_anterior_percentual=_porcentagem(
            total.mes_centavos - total.anterior_centavos, total.anterior_centavos
        ),
        variacao_ano_passado_percentual=_porcentagem(
            total.mes_centavos - total.ano_passado_centavos, total.ano_passado_centavos
        ),
    )


def _ler_mes(conn, mes: str) -> LeituraDoMes:
    dia = primeiro_dia(mes)
    hoje = lancamentos.hoje().replace(day=1)
    despesas = _por_situacao(conn, "despesa", dia)
    despesas["realizado"] += faturas.ajustes_do_mes(conn, dia)
    receitas = _por_situacao(conn, "receita", dia)
    (planejado,) = conn.execute(
        "SELECT COALESCE(SUM(i.valor_centavos), 0)::bigint FROM itens_do_planejamento i"
        " JOIN categorias c ON c.id = i.categoria_id WHERE i.mes = %s AND c.tipo = 'despesa'",
        (dia,),
    ).fetchone()
    situacao = "passado" if dia < hoje else "atual" if dia == hoje else "futuro"
    resumo_das_despesas = Despesas(
        realizado_centavos=despesas["realizado"],
        previsto_centavos=despesas["previsto"],
        planejado_centavos=planejado,
        livre_centavos=max(planejado - despesas["realizado"] - despesas["previsto"], 0),
    )
    resumo_das_receitas = Receitas(
        realizado_centavos=receitas["realizado"], previsto_centavos=receitas["previsto"]
    )
    planejamento = planejamento_do_mes(conn, mes)
    comparacao = _comparacao(conn, dia)
    return LeituraDoMes(
        mes=mes,
        situacao=situacao,
        despesas=resumo_das_despesas,
        receitas=resumo_das_receitas,
        planejamento=planejamento,
        comparacao=comparacao,
        ranking=_ranking(conn, dia),
        fechamento=_fechamento(
            conn, dia, resumo_das_despesas, resumo_das_receitas, planejamento, comparacao
        )
        if situacao == "passado"
        else None,
    )


@router.get("/meses/{mes}", response_model=LeituraDoMes, operation_id="ler_mes")
def ler_mes(mes: Mes, usuario: UsuarioLogado, request: Request) -> LeituraDoMes:
    with conectar(url_do_banco(request)) as conn:
        return _ler_mes(conn, mes)
