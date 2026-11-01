"""Parcelamento: a compra ou a dívida em N parcelas. Ele não é um lançamento (ADR 0004): cada
parcela é um lançamento comum, ligado a ele pelo `parcelamento_id` e pelo número da parcela,
para o valor inteiro nunca contar de uma vez num mês só. No cartão, todas as parcelas têm a data
da compra e a parcela n cai n - 1 faturas depois da fatura da compra; fora dele (o boleto), a
parcela n vence n - 1 meses depois da primeira."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID, uuid5

import psycopg
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app import cartoes, faturas, lancamentos
from app.backup import LINHAS_POR_LOTE
from app.banco import conectar, em_transacao
from app.config import valores_iniciais
from app.lancamentos import (
    conferir_ligacoes,
    excluir,
    gravar_categorias,
    ids_das_tags,
    recusar,
    registrar_mudancas,
    sem_repetidas,
    subir_versao,
    tags_limpas,
    url_do_banco,
)
from app.login import UsuarioLogado
from app.recorrencias import com_o_dia_do_lancamento, dia_do_lancamento_vigente, mais_meses

router = APIRouter(prefix="/api")

# 35 anos de prestações da casa; o limite só protege a geração de um número sem sentido.
MAXIMO_DE_PARCELAS = valores_iniciais()["maximoDeParcelas"]


class DadosDoParcelamento(BaseModel):
    id: UUID
    # Compra ou dívida: as parcelas são despesas. Não é gravado: a receita parcelada, se vier,
    # ganha a coluna.
    tipo: Literal["despesa"] = "despesa"
    parcelas: int = Field(ge=2, le=MAXIMO_DE_PARCELAS)
    # No cartão, a data da compra, a mesma em todas as parcelas; fora dele, a da 1ª parcela.
    data: date
    descricao: str = ""
    # O cartão ou a conta de onde sai o boleto.
    conta_id: UUID
    categoria_ids: list[UUID] = Field(min_length=1)
    tags: list[str] = []
    # O id de uma pessoa do casal, que as parcelas herdam; sem ela, é do conjunto.
    pessoa: str | None = None
    # A escolha do item do planejamento, pela categoria dele, com que as parcelas nascem
    # (ADR 0006).
    item_categoria_id: UUID | None = None
    # O dia (São Paulo) em que o casal lançou no aparelho; sem ele, o da chegada. No boleto, o
    # "antes de hoje" se conta a partir dele e a parcela desse dia nasce realizada (ticket 127).
    dia_do_lancamento: date | None = None

    _tags = field_validator("tags")(tags_limpas)
    _categorias = field_validator("categoria_ids")(sem_repetidas)

    @model_validator(mode="after")
    def _item_de_uma_das_categorias(self):
        if self.item_categoria_id and self.item_categoria_id not in self.categoria_ids:
            raise ValueError(lancamentos.ITEM_FORA_DAS_CATEGORIAS)
        return self


class NovoParcelamento(DadosDoParcelamento):
    # O total (compra sem juros) ou o da parcela (com juros); os centavos que sobram da divisão
    # do total vão na 1ª parcela.
    valor_total_centavos: int | None = Field(default=None, gt=0)
    valor_da_parcela_centavos: int | None = Field(default=None, gt=0)
    # Sem o campo, o do cartão nasce automático e o boleto pede confirmação de cada parcela.
    automatico: bool | None = None

    @model_validator(mode="after")
    def _um_valor(self):
        if (self.valor_total_centavos is None) == (self.valor_da_parcela_centavos is None):
            raise ValueError("informe o valor total ou o da parcela, um dos dois")
        if self.valor_total_centavos is not None and self.valor_total_centavos < self.parcelas:
            raise ValueError("o total não chega a um centavo por parcela")
        return self

    @property
    def total(self) -> int:
        return self.valor_total_centavos or self.valor_da_parcela_centavos * self.parcelas


class Parcelamento(DadosDoParcelamento):
    valor_total_centavos: int
    # A parcela vira realizada sozinha na data, sem confirmação.
    automatico: bool
    criado_por: str
    criado_em: datetime
    alterado_por: str
    alterado_em: datetime
    # As parcelas do boleto que já tinham passado quando ele foi lançado (ticket 87): não viram
    # lançamento, mas contam na numeração e no total.
    parcelas_puladas: int = 0


class AlteracaoDeParcelamento(BaseModel):
    """O que se corrige num parcelamento; campo ausente fica como está. Descrição, categorias,
    tags, pessoa e item valem para todas as parcelas, inclusive as realizadas. Valor, número de
    parcelas e data refazem as parcelas, salvo as que uma pessoa editou à mão; se uma realizada
    mudar ou sair, o pedido só vale com `confirmar_realizadas`."""

    # Sem `None` no tipo: mandar null num campo obrigatório do parcelamento é erro, não "limpar".
    descricao: str = Field(default=None)
    categoria_ids: list[UUID] = Field(default=None, min_length=1)
    tags: list[str] = Field(default=None)
    # Vazia, passa o parcelamento para o conjunto.
    pessoa: str | None = None
    # Vazio tira a escolha; ela também sai com a categoria dela.
    item_categoria_id: UUID | None = None
    # O total novo, ou o da parcela (vale vezes o número de parcelas); só o número de parcelas
    # mantém o total, e as parcelas se dividem de novo.
    valor_total_centavos: int | None = Field(default=None, gt=0)
    valor_da_parcela_centavos: int | None = Field(default=None, gt=0)
    parcelas: int = Field(default=None, ge=2, le=MAXIMO_DE_PARCELAS)
    # Como na criação: no cartão, a data da compra; fora dele, a da 1ª parcela.
    data: date = Field(default=None)
    confirmar_realizadas: bool = False

    _tags = field_validator("tags")(tags_limpas)
    _categorias = field_validator("categoria_ids")(sem_repetidas)

    @model_validator(mode="after")
    def _um_valor(self):
        if self.valor_total_centavos is not None and self.valor_da_parcela_centavos is not None:
            raise ValueError("informe o valor total ou o da parcela, um dos dois")
        return self


class ParcelaQueMuda(BaseModel):
    """Uma parcela realizada que a correção muda ou tira."""

    id: UUID
    parcela: int
    valor_centavos: int
    data: date
    # Como fica; vazios quando ela sai.
    valor_novo_centavos: int | None
    data_nova: date | None
    sai: bool


class AvisoDeRealizadas(BaseModel):
    """A correção mudaria parcelas já realizadas; nada foi gravado. Repetir o pedido com
    `confirmar_realizadas` as muda."""

    motivo: str
    parcelas: list[ParcelaQueMuda]


class RealizadasMudam(Exception):
    """A correção pede confirmação: muda parcelas realizadas."""

    def __init__(self, aviso: AvisoDeRealizadas):
        self.aviso = aviso


_COLUNAS = (
    "id, valor_total_centavos, parcelas, data, automatico, descricao, conta_id, pessoa,"
    " criado_por, criado_em, alterado_por, alterado_em, item_categoria_id, dia_do_lancamento"
)
_NOMES_DAS_COLUNAS = _COLUNAS.replace(" ", "").split(",")


def valor_da_parcela(total: int, parcelas: int, n: int) -> int:
    """O total dividido por igual; os centavos que sobram vão na 1ª."""
    return total // parcelas + (total % parcelas if n == 1 else 0)


def parcelas_puladas(parcelas: int, data: date, hoje: date, no_cartao: bool) -> int:
    """Quantas parcelas do boleto caem antes de `hoje` e não viram lançamento (ticket 87); o
    cartão não pula nenhuma. O app repete esta conta para avisar (ADR 0018); a tabela
    `tabelas-de-teste/puladas.json` vale para os dois."""
    if no_cartao:
        return 0
    return sum(1 for n in range(1, parcelas + 1) if mais_meses(data, n - 1) < hoje)


def realiza_em(conn, conta_id: UUID, parcela: int, mes: date, data: date) -> date:
    """O dia em que a parcela automática vira realizada. No cartão, a parcela n > 1 entra na
    fatura aberta quando a fatura de antes fecha (a importada, sem datas, já está fechada, e
    a que ainda não nasceu fecha no dia padrão); a 1ª e a do boleto, na data."""
    cartao = faturas.ler_cartao(conn, conta_id)
    if cartao is None or parcela == 1:
        return data
    anterior = faturas.somar_meses(mes, -1)
    gravada = conn.execute(
        "SELECT fechamento FROM faturas WHERE cartao_id = %s AND mes = %s",
        (cartao.titular.id, anterior),
    ).fetchone()
    fechamento = gravada[0] if gravada else faturas.datas_padrao(cartao.titular, anterior)[0]
    return fechamento or data


def ler_um(conn, id: UUID) -> Parcelamento | None:
    lidos = _ler(conn, "id = %s", (id,))
    return lidos[0] if lidos else None


def _ler(conn, filtro: str = "", parametros: tuple = ()) -> list[Parcelamento]:
    # Cada parcela gerada tem um lançamento só (o id vem do número), excluída ou não: a que
    # falta foi pulada na geração, e a que a correção levou para antes de hoje saiu pulada
    # (`excluido_pela_regra`).
    linhas = conn.execute(
        f"SELECT {_COLUNAS}, LEAST(geradas, parcelas) - (SELECT count(*) FROM lancamentos l"
        " WHERE l.parcelamento_id = parcelamentos.id AND l.parcela <= parcelamentos.parcelas"
        " AND l.excluido_pela_regra IS NOT TRUE)"
        f" FROM parcelamentos {'WHERE ' + filtro if filtro else ''}"
        " ORDER BY data DESC, descricao, id",
        parametros,
    ).fetchall()
    ids = [linha[0] for linha in linhas]
    categorias: dict[UUID, list[UUID]] = {}
    for parcelamento_id, categoria_id in conn.execute(
        "SELECT parcelamento_id, categoria_id FROM parcelamento_categorias"
        " WHERE parcelamento_id = ANY(%s) ORDER BY categoria_id",
        (ids,),
    ):
        categorias.setdefault(parcelamento_id, []).append(categoria_id)
    tags: dict[UUID, list[str]] = {}
    for parcelamento_id, nome in conn.execute(
        "SELECT pt.parcelamento_id, t.nome FROM parcelamento_tags pt"
        " JOIN tags t ON t.id = pt.tag_id WHERE pt.parcelamento_id = ANY(%s) ORDER BY t.nome",
        (ids,),
    ):
        tags.setdefault(parcelamento_id, []).append(nome)
    return [
        Parcelamento(
            **dict(zip([*_NOMES_DAS_COLUNAS, "parcelas_puladas"], linha)),
            categoria_ids=categorias.get(linha[0], []),
            tags=tags.get(linha[0], []),
        )
        for linha in linhas
    ]


def _gerar_um_lote(conn, id: UUID) -> bool:
    """Grava as próximas parcelas, quantas cabem numa transação, e devolve se pode faltar
    alguma. O id de cada parcela vem do parcelamento e do número dela: gerar de novo não
    duplica. No boleto, a parcela de antes de hoje não vira lançamento (ticket 87); enquanto o
    parcelamento é o que o casal lançou, o "hoje" é o dia do lançamento
    (`dia_do_lancamento_vigente`), e a parcela desse dia nasce realizada. O cartão segue o
    ticket 99. Antes das próximas, nascem as puladas que uma correção trouxe para hoje ou
    depois (ticket 126)."""
    if not (lidos := _ler(conn, "id = %s", (id,))):
        return False  # excluído no meio da geração
    [regra] = lidos
    (geradas,) = conn.execute("SELECT geradas FROM parcelamentos WHERE id = %s", (id,)).fetchone()
    categorias = regra.categoria_ids
    tags = [
        tag
        for (tag,) in conn.execute(
            "SELECT tag_id FROM parcelamento_tags WHERE parcelamento_id = %s", (id,)
        )
    ]
    no_cartao = faturas.ler_cartao(conn, regra.conta_id) is not None
    # O DSQL aceita até 3.000 linhas por transação; no cartão, cada parcela pode criar a fatura.
    por_lote = max(1, LINHAS_POR_LOTE // (2 + len(categorias) + len(tags)))
    proximas = range(geradas + 1, min(regra.parcelas, geradas + por_lote) + 1)
    puladas = _puladas_que_chegaram(conn, regra, geradas)
    if puladas:
        numeros: Sequence[int] = puladas[:por_lote]
    elif proximas:
        _reviver_as_que_a_correcao_tirou(conn, regra, geradas, proximas)
        numeros = proximas
    else:
        return False
    dia_de_hoje = lancamentos.hoje()
    lancado = dia_do_lancamento_vigente(regra)
    desde = lancado or dia_de_hoje
    for n in numeros:
        lancamento_id = uuid5(id, str(n))
        dia = regra.data if no_cartao else mais_meses(regra.data, n - 1)
        if not no_cartao and dia < desde:
            continue
        mes = lancamentos.mes_em_que_conta(conn, regra.conta_id, dia, n)
        # A parcela automática que já chegou nasce realizada; o resto, prevista.
        chegou = realiza_em(conn, regra.conta_id, n, mes, dia) <= dia_de_hoje
        situacao = (
            "realizado"
            if chegou and (regra.automatico or (dia == lancado and not no_cartao))
            else "previsto"
        )
        gravado = conn.execute(
            "INSERT INTO lancamentos (id, tipo, situacao, valor_centavos, data, descricao,"
            " conta_id, criado_por, alterado_por, versao, parcelamento_id, parcela, automatico,"
            " pessoa, fonte, mes, item_categoria_id)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s, 'app', %s, %s)"
            " ON CONFLICT (id) DO NOTHING",
            (
                lancamento_id,
                regra.tipo,
                situacao,
                valor_da_parcela(regra.valor_total_centavos, regra.parcelas, n),
                dia,
                regra.descricao,
                regra.conta_id,
                regra.alterado_por,
                regra.alterado_por,
                id,
                n,
                regra.automatico,
                regra.pessoa,
                mes,
                regra.item_categoria_id,
            ),
        ).rowcount
        if not gravado:
            continue
        for categoria in categorias:
            conn.execute(
                "INSERT INTO lancamento_categorias (lancamento_id, categoria_id) VALUES (%s, %s)",
                (lancamento_id, categoria),
            )
        for tag in tags:
            conn.execute(
                "INSERT INTO lancamento_tags (lancamento_id, tag_id) VALUES (%s, %s)",
                (lancamento_id, tag),
            )
    if puladas:
        return True  # as próximas vêm no lote seguinte
    if not conn.execute(
        "UPDATE parcelamentos SET geradas = %s WHERE id = %s AND geradas = %s",
        (proximas[-1], id, geradas),
    ).rowcount:
        # Outra geração andou junto: a transação recomeça e parte do que ela gravou.
        raise psycopg.errors.SerializationFailure("o parcelamento mudou durante a geração")
    return proximas[-1] < regra.parcelas


def _puladas_que_chegaram(
    conn, regra: Parcelamento, geradas: int, lancamentos_existentes: int | None = None
) -> list[int]:
    """As parcelas do boleto que a geração pulou por estarem antes de hoje (não têm lançamento,
    nem excluído) e que a data corrigida pôs em hoje ou depois. O cartão não pula nenhuma.
    Só lê as parcelas do boleto quando falta alguma: `geradas` maior que o número de
    lançamentos (ticket 131)."""
    if faturas.ler_cartao(conn, regra.conta_id) is not None:
        return []
    if lancamentos_existentes is None:
        (lancamentos_existentes,) = conn.execute(
            "SELECT count(*) FROM lancamentos WHERE parcelamento_id = %s AND parcela <= %s",
            (regra.id, regra.parcelas),
        ).fetchone()
    if lancamentos_existentes >= min(geradas, regra.parcelas):
        return []
    existem = {
        n
        for (n,) in conn.execute(
            "SELECT parcela FROM lancamentos WHERE parcelamento_id = %s", (regra.id,)
        )
    }
    dia_de_hoje = lancamentos.hoje()
    return [
        n
        for n in range(1, min(geradas, regra.parcelas) + 1)
        if n not in existem and mais_meses(regra.data, n - 1) >= dia_de_hoje
    ]


def _reviver_as_que_a_correcao_tirou(
    conn, regra: Parcelamento, geradas: int, proximas: range
) -> None:
    """Uma parcela de depois de `geradas` que já existe, excluída, saiu quando o parcelamento
    encolheu. Se ele cresceu e a geração chega antes do refazer da correção, o `INSERT ... ON
    CONFLICT DO NOTHING` a pularia e ela ficaria excluída para sempre: volta aqui."""
    (ha,) = conn.execute(
        "SELECT EXISTS (SELECT FROM lancamentos WHERE parcelamento_id = %s"
        " AND excluido_em IS NOT NULL AND parcela = ANY(%s))",
        (regra.id, list(proximas)),
    ).fetchone()
    if not ha:
        return
    tags = _tags_do_parcelamento(conn, regra.id)
    agora = datetime.now(UTC)
    for correcao in _correcoes(conn, regra, geradas, {}):
        if correcao.acao in ("reviver", "pular") and correcao.parcela in proximas:
            _aplicar(conn, regra, correcao, tags, regra.alterado_por, agora)


def gerar_as_parcelas(url: str | None, id: UUID) -> None:
    """Gera, em lotes de uma transação cada, as parcelas que faltam. Se parar no meio, o reenvio
    ou a tarefa diária continuam de onde parou."""
    while em_transacao(url, lambda conn: _gerar_um_lote(conn, id)):
        pass


def completar_todos(url: str | None) -> int:
    """Conserta os parcelamentos que um pedido deixou pela metade: gera as parcelas que faltam
    (a geração parou no meio) e refaz as que destoam do parcelamento (a correção parou no
    meio), inclusive a classificação (descrição, categorias, tags, pessoa, item) que o pedido
    trouxe, gravada no parcelamento até o refazer terminar. Devolve quantos consertou."""
    with conectar(url) as conn:
        ids = [id for (id,) in conn.execute("SELECT id FROM parcelamentos")]
    consertados = 0
    for id in ids:
        if not em_transacao(url, lambda conn, id=id: _falta_conserto(conn, id)):
            continue
        consertados += 1
        pendente = em_transacao(url, lambda conn, id=id: _classificacao_pendente(conn, id))
        while em_transacao(url, lambda conn, id=id: _reajustar_do_parcelamento(conn, id)):
            pass
        em_transacao(url, lambda conn, id=id, feita=pendente: _dar_por_refeita(conn, id, feita))
        gerar_as_parcelas(url, id)
    return consertados


# Os campos de classificação a levar às parcelas, cada um com a parcela a partir da qual vale: a
# correção leva a todas (1), e "esta e as próximas" a partir da parcela mudada (ticket 136).
Classificacao = Mapping[str, int]


def _ler_classificacao(texto: str | None) -> dict[str, int]:
    """`descricao,tags@5`: a descrição desde a 1ª, as tags desde a 5ª."""
    lida = {}
    for item in filter(None, (texto or "").split(",")):
        campo, _, desde = item.partition("@")
        lida[campo] = int(desde or 1)
    return lida


def _gravar_classificacao(classificacao: Classificacao) -> str:
    return ",".join(
        sorted(c if desde == 1 else f"{c}@{desde}" for c, desde in classificacao.items())
    )


def _juntar(*classificacoes: Classificacao) -> dict[str, int]:
    """O campo pedido por mais de uma vale desde a menor parcela."""
    juntas: dict[str, int] = {}
    for classificacao in classificacoes:
        for campo, desde in classificacao.items():
            juntas[campo] = min(desde, juntas.get(campo, desde))
    return juntas


def _classificacao_pendente(conn, id: UUID) -> dict[str, int]:
    """Os campos de classificação que correções já gravadas ainda não levaram às parcelas."""
    linha = conn.execute(
        "SELECT classificacao_pendente FROM parcelamentos WHERE id = %s", (id,)
    ).fetchone()
    return _ler_classificacao(linha[0]) if linha else {}


def _dar_por_refeita(conn, id: UUID, feita: Classificacao) -> None:
    """Tira do pendente o que acabou de ser refeito; se outra correção gravou campos novos no
    meio, o pendente mudou e fica para ela."""
    conn.execute(
        "UPDATE parcelamentos SET classificacao_pendente = '' WHERE id = %s"
        " AND coalesce(classificacao_pendente, '') = %s",
        (id, _gravar_classificacao(feita)),
    )


def _falta_conserto(conn, id: UUID) -> bool:
    if not (lidos := _ler(conn, "id = %s", (id,))):
        return False
    [regra] = lidos
    (geradas,) = conn.execute("SELECT geradas FROM parcelamentos WHERE id = %s", (id,)).fetchone()
    pendente = _classificacao_pendente(conn, id)
    return (
        geradas < regra.parcelas
        or bool(pendente)
        or bool(_puladas_que_chegaram(conn, regra, geradas))
        or bool(_correcoes(conn, regra, geradas, pendente))
    )


def _reajustar_do_parcelamento(conn, id: UUID) -> bool:
    """Um lote do conserto da tarefa diária, em nome de quem alterou o parcelamento por último."""
    if not (lidos := _ler(conn, "id = %s", (id,))):
        return False
    return _reajustar_um_lote(conn, id, lidos[0].alterado_por, _classificacao_pendente(conn, id))


def origem(descricao: str) -> str:
    """Como a tela de conflito nomeia a regra que mudou o lançamento ("O da regra ...")."""
    return f"o parcelamento {descricao}".strip()


def _conferir_faturas_das_parcelas(conn, novo: NovoParcelamento, primeira: date) -> None:
    """Nenhuma parcela cai numa fatura paga (ADR 0021). A parcela n cai n - 1 faturas depois da
    primeira, e a paga pode vir depois de uma fechada sem pagamento: confere todas aqui, porque
    a geração em lotes não volta atrás."""
    titular = faturas.ler_cartao(conn, novo.conta_id).titular
    ultima = faturas.somar_meses(primeira, novo.parcelas - 1)
    for fatura in cartoes.faturas_do_titular(conn, titular.id):
        if primeira <= fatura.mes <= ultima and cartoes.paga_pelo_pagamento(fatura):
            raise cartoes.recusa_da_paga(conn, titular.id, fatura.mes)


def gravar(conn, novo: NovoParcelamento, usuario: str) -> tuple[Parcelamento, bool]:
    """Grava o parcelamento sem as parcelas (`gerar_as_parcelas` as gera depois) e devolve se é
    novo. Reenviar o mesmo id (a fila repete) devolve o gravado."""
    if ja := _ler(conn, "id = %s", (novo.id,)):
        return ja[0], False
    conferir_ligacoes(conn, novo)
    no_cartao = faturas.ler_cartao(conn, novo.conta_id) is not None
    if no_cartao and novo.automatico is False:
        raise recusar("o parcelamento no cartão é automático")
    novo = com_o_dia_do_lancamento(novo)
    # Como a recorrência (ticket 87): o boleto que já venceu inteiro não teria parcela nenhuma.
    if not no_cartao and mais_meses(novo.data, novo.parcelas - 1) < novo.dia_do_lancamento:
        raise recusar("o parcelamento termina antes de hoje")
    # A fatura da 1ª parcela (no cartão sem dia de fechamento, não há como escolher) é
    # conferida antes de gravar: senão a regra ficaria sem parcelas, e a tarefa diária
    # tentaria gerá-las todo dia.
    primeira = lancamentos.mes_em_que_conta(conn, novo.conta_id, novo.data)
    if no_cartao:
        _conferir_faturas_das_parcelas(conn, novo, primeira)
    tags = ids_das_tags(conn, novo.tags, usuario, set())
    gravado = conn.execute(
        f"INSERT INTO parcelamentos ({_COLUNAS}, geradas)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now(), %s, now(), %s, %s, 0)"
        # Dois reenvios ao mesmo tempo: o segundo fica com o que o primeiro gravou.
        " ON CONFLICT (id) DO NOTHING",
        (
            novo.id,
            novo.total,
            novo.parcelas,
            novo.data,
            no_cartao or bool(novo.automatico),
            novo.descricao,
            novo.conta_id,
            novo.pessoa,
            usuario,
            usuario,
            novo.item_categoria_id,
            novo.dia_do_lancamento,
        ),
    ).rowcount
    if not gravado:
        return _ler(conn, "id = %s", (novo.id,))[0], False
    for categoria in novo.categoria_ids:
        conn.execute(
            "INSERT INTO parcelamento_categorias (parcelamento_id, categoria_id) VALUES (%s, %s)",
            (novo.id, categoria),
        )
    for tag in tags:
        conn.execute(
            "INSERT INTO parcelamento_tags (parcelamento_id, tag_id) VALUES (%s, %s)",
            (novo.id, tag),
        )
    return _ler(conn, "id = %s", (novo.id,))[0], True


def criar(url: str | None, novo: NovoParcelamento, usuario: str) -> tuple[Parcelamento, bool]:
    """Grava o parcelamento e gera as parcelas; serve à rota e ao lote da fila."""
    criado, gravado = em_transacao(url, lambda conn: gravar(conn, novo, usuario))
    gerar_as_parcelas(url, novo.id)
    # Lido de novo depois da geração: as parcelas puladas só se sabem com ela. Excluído por
    # outra sessão no meio, fica o que foi gravado.
    with conectar(url) as conn:
        lidos = _ler(conn, "id = %s", (novo.id,))
    return (lidos[0] if lidos else criado), gravado


@router.post(
    "/parcelamentos",
    status_code=201,
    response_model=Parcelamento,
    operation_id="criar_parcelamento",
)
def criar_parcelamento(
    novo: NovoParcelamento, usuario: UsuarioLogado, request: Request, response: Response
) -> Parcelamento:
    """Grava o parcelamento e gera todas as parcelas. Reenviar o mesmo id (a fila repete)
    devolve o gravado, com 200, e completa a geração se ela tiver parado no meio."""
    criado, gravado = criar(url_do_banco(request), novo, usuario)
    response.status_code = 201 if gravado else 200
    return criado


@router.get(
    "/parcelamentos", response_model=list[Parcelamento], operation_id="listar_parcelamentos"
)
def listar_parcelamentos(usuario: UsuarioLogado, request: Request) -> list[Parcelamento]:
    with conectar(url_do_banco(request)) as conn:
        return _ler(conn)


def _tags_do_parcelamento(conn, id: UUID) -> list[UUID]:
    return [
        tag
        for (tag,) in conn.execute(
            "SELECT tag_id FROM parcelamento_tags WHERE parcelamento_id = %s", (id,)
        )
    ]


def parcelas_por_lote(regra: Parcelamento) -> int:
    """Quantas parcelas cabem numa transação, pelas linhas que cada uma mexe (a folga do DSQL é
    a mesma da geração)."""
    return max(1, LINHAS_POR_LOTE // (10 + 2 * (len(regra.categoria_ids) + len(regra.tags))))


_Acao = Literal["excluir", "reviver", "atualizar", "pular"]


@dataclass
class _Correcao:
    """O que falta fazer numa parcela para ela ficar como o parcelamento manda: sair, voltar
    (uma que a correção tirou antes), mudar ou sair como pulada (a data nova, no boleto, caiu
    antes de hoje). `valor`, `dia` e `mes` são os de depois."""

    id: UUID
    versao: int
    parcela: int
    acao: _Acao
    mudou: list[str]
    valor: int
    dia: date
    mes: date
    realizada: bool
    valor_antes: int
    dia_antes: date

    @property
    def muda_o_cronograma(self) -> bool:
        return self.acao in ("excluir", "pular") or (self.valor, self.dia) != (
            self.valor_antes,
            self.dia_antes,
        )

    @property
    def aviso(self) -> ParcelaQueMuda:
        sai = self.acao == "excluir"
        return ParcelaQueMuda(
            id=self.id,
            parcela=self.parcela,
            valor_centavos=self.valor_antes,
            data=self.dia_antes,
            valor_novo_centavos=None if sai else self.valor,
            data_nova=None if sai else self.dia,
            sai=sai,
        )


# O que vale para as parcelas quando o pedido o traz, menos onde uma pessoa o mudou à mão.
CLASSIFICACAO = frozenset({"descricao", "categoria_ids", "tags", "pessoa", "item_categoria_id"})
# Os campos da parcela que o valor, o número de parcelas e a data do parcelamento dão.
CRONOGRAMA = frozenset({"valor_centavos", "data", "conta_id", "fatura_mes"})


def _correcoes(
    conn,
    regra: Parcelamento,
    geradas: int,
    classificacao: Classificacao,
    dia_da_correcao: date | None = None,
    mantidas: set[int] | None = None,
    cronograma_pedido: frozenset[str] = frozenset(),
) -> list[_Correcao]:
    """As parcelas que não estão como o parcelamento manda, na ordem do número. A que uma pessoa
    mudou à mão fica como está nos campos que mudou (a conta segura também a data e a fatura), e
    o número dela entra em `mantidas` quando o pedido a mudaria: na classificação pedida, e no
    valor e na data se estão em `cronograma_pedido` (ticket 136). A
    classificação só se refaz no que o pedido trouxe (`classificacao`, cada campo a partir de
    uma parcela), para a descrição corrigida numa parcela só não voltar a cada correção de valor,
    e para a de "esta e as próximas" não chegar às de antes. A parcela que saiu antes, quando o
    parcelamento encolheu, volta se ele crescer de novo (as de depois de `geradas`), com tudo.
    No boleto, nada da correção vira lançamento antes de hoje (ticket 87): a prevista que a data
    nova leva de hoje ou depois para antes sai como pulada (`excluido_pela_regra`), e volta se
    outra correção a trouxer de novo para hoje ou depois. A atrasada (já antes de hoje) segue
    prevista com a data nova; a realizada muda, com a confirmação. O "de hoje ou depois" é do dia
    em que a correção foi pedida (`corrigido_em`), não do dia em que o lote roda: a que para no
    meio termina igual noutro dia (ticket 131)."""
    parcelas = conn.execute(
        f"SELECT id, parcela, data, valor_centavos, descricao, pessoa, situacao,"
        f" excluido_em IS NOT NULL, {lancamentos.VERSAO}, item_categoria_id, mes,"
        " COALESCE(excluido_pela_regra, false)"
        " FROM lancamentos WHERE parcelamento_id = %s"
        " ORDER BY parcela",
        (regra.id,),
    ).fetchall()
    ids = [linha[0] for linha in parcelas]
    a_mao = lancamentos.campos_a_mao(conn, ids)
    mantidas = set() if mantidas is None else mantidas
    categorias: dict[UUID, set[UUID]] = {}
    for lancamento_id, categoria_id in conn.execute(
        "SELECT lancamento_id, categoria_id FROM lancamento_categorias"
        " WHERE lancamento_id = ANY(%s)",
        (ids,),
    ):
        categorias.setdefault(lancamento_id, set()).add(categoria_id)
    tags: dict[UUID, set[str]] = {}
    for lancamento_id, nome in conn.execute(
        "SELECT lt.lancamento_id, t.nome FROM lancamento_tags lt JOIN tags t ON t.id = lt.tag_id"
        " WHERE lt.lancamento_id = ANY(%s)",
        (ids,),
    ):
        tags.setdefault(lancamento_id, set()).add(nome.casefold())
    no_cartao = faturas.ler_cartao(conn, regra.conta_id) is not None
    dia_de_hoje = lancamentos.hoje()
    if dia_da_correcao is None:
        linha = conn.execute(
            "SELECT corrigido_em FROM parcelamentos WHERE id = %s", (regra.id,)
        ).fetchone()
        dia_da_correcao = (linha[0] if linha else None) or dia_de_hoje
    quer = {
        "descricao": regra.descricao,
        "pessoa": regra.pessoa,
        "item_categoria_id": regra.item_categoria_id,
        "categoria_ids": set(regra.categoria_ids),
        "tags": {tag.casefold() for tag in regra.tags},
    }
    feitas = []
    for (
        lancamento_id,
        n,
        dia_antes,
        valor_antes,
        descricao,
        pessoa,
        situacao,
        excluida,
        versao,
        item_categoria_id,
        mes_antes,
        pulada,
    ) in parcelas:
        maos = a_mao.get(lancamento_id, set())
        acao: _Acao = "atualizar"
        if excluida:
            if n > regra.parcelas or not (pulada or geradas < n):
                continue
            acao = "reviver"
        elif n > regra.parcelas:
            # Só valor, data, conta e fatura mudados à mão seguram a parcela que sobra.
            if maos & CRONOGRAMA:
                continue
            acao = "excluir"
        tem = {
            "descricao": descricao,
            "pessoa": pessoa,
            "item_categoria_id": item_categoria_id,
            "categoria_ids": categorias.get(lancamento_id, set()),
            "tags": tags.get(lancamento_id, set()),
        }
        campos = dict.fromkeys(CLASSIFICACAO, 1) if acao == "reviver" else classificacao
        mudou = []
        for campo, querido in quer.items():
            if campo not in campos or n < campos[campo] or querido == tem[campo]:
                continue
            if campo in maos:
                mantidas.add(n)
            else:
                mudou.append(campo)
        valor, dia, mes = valor_antes, dia_antes, mes_antes
        if acao != "excluir":
            pela_regra = valor_da_parcela(regra.valor_total_centavos, regra.parcelas, n)
            no_dia = regra.data if no_cartao else mais_meses(regra.data, n - 1)
            if "valor_centavos" not in maos:
                valor = pela_regra
            elif pela_regra != valor_antes and "valor_centavos" in cronograma_pedido:
                mantidas.add(n)
            if not maos & {"data", "conta_id"}:
                dia = no_dia
            elif no_dia != dia_antes and "data" in cronograma_pedido:
                mantidas.add(n)
            if (dia != dia_antes or acao == "reviver") and not maos & {"fatura_mes", "conta_id"}:
                mes = lancamentos.mes_em_que_conta(conn, regra.conta_id, dia, n)
            if valor != valor_antes:
                mudou.append("valor_centavos")
            if dia != dia_antes:
                mudou.append("data")
            # A fatura que o app escolheu de novo conta como mudança do parcelamento (ADR 0011).
            if no_cartao and mes != mes_antes:
                mudou.append("fatura_mes")
        if not no_cartao and dia < dia_de_hoje:
            if acao == "reviver":
                if pulada:
                    continue
                acao = "pular"  # a que o encolher tirou volta, mas já passou
            elif acao == "atualizar" and situacao == "previsto" and dia_antes >= dia_da_correcao:
                acao = "pular"
        if acao != "atualizar" or mudou:
            feitas.append(
                _Correcao(
                    lancamento_id,
                    versao,
                    n,
                    acao,
                    mudou,
                    valor,
                    dia,
                    mes,
                    situacao == "realizado",
                    valor_antes,
                    dia_antes,
                )
            )
    return feitas


@dataclass
class CorrecaoGravada:
    """A correção gravada no parcelamento: a classificação a refazer nas parcelas e o número das
    que ficam como estavam em algum campo pedido, porque uma pessoa o mudou só nelas."""

    classificacao: dict[str, int]
    mantidas: set[int]


def gravar_correcao(
    conn,
    id: UUID,
    alteracao: AlteracaoDeParcelamento,
    usuario: str,
    desde: int = 1,
    editada: UUID | None = None,
    tambem_mudam: Sequence[ParcelaQueMuda] = (),
) -> CorrecaoGravada:
    """Valida e grava o parcelamento corrigido (recusa antes de gravar, e avisa se uma realizada
    mudaria sem `confirmar_realizadas`); as parcelas são refeitas depois, em lotes. A
    classificação vale a partir da parcela `desde`. Na mudança de uma parcela com alcance (ticket
    136), a `editada` segue o parcelamento nos campos pedidos mesmo que alguém a tenha mudado à
    mão, não entra no aviso nem na contagem, e o aviso leva também as realizadas
    `tambem_mudam`."""
    if not (lidos := _ler(conn, "id = %s", (id,))):
        raise HTTPException(status_code=404, detail="parcelamento não encontrado")
    [atual] = lidos
    (geradas,) = conn.execute("SELECT geradas FROM parcelamentos WHERE id = %s", (id,)).fetchone()
    pedidas = alteracao.model_dump(
        include=alteracao.model_fields_set
        - {"valor_total_centavos", "valor_da_parcela_centavos", "confirmar_realizadas"}
    )
    if atual.item_categoria_id not in pedidas.get("categoria_ids", [atual.item_categoria_id]):
        pedidas.setdefault("item_categoria_id", None)  # a escolha sai com a categoria dela
    parcelas = pedidas.get("parcelas", atual.parcelas)
    if alteracao.valor_total_centavos:
        total = alteracao.valor_total_centavos
    elif alteracao.valor_da_parcela_centavos:
        total = alteracao.valor_da_parcela_centavos * parcelas
    else:
        total = atual.valor_total_centavos
    if total < parcelas:
        raise recusar("o total não chega a um centavo por parcela")
    try:
        nova = Parcelamento(**(atual.model_dump() | pedidas | {"valor_total_centavos": total}))
    except ValidationError as erro:
        raise recusar("; ".join(e["msg"] for e in erro.errors())) from erro
    conferir_ligacoes(conn, nova, atual.conta_id, frozenset(atual.categoria_ids))
    sobram = dict(
        conn.execute(
            "SELECT id, parcela FROM lancamentos WHERE parcelamento_id = %s"
            " AND excluido_em IS NULL AND parcela > %s",
            (id, nova.parcelas),
        ).fetchall()
    )
    a_mao = [
        sobram[lancamento_id]
        for lancamento_id, campos in lancamentos.campos_a_mao(conn, list(sobram)).items()
        if campos & CRONOGRAMA
    ]
    if a_mao:
        raise recusar(
            f"a parcela {max(a_mao)} foi editada à mão: exclua-a antes de tirá-la do parcelamento"
        )
    geradas_depois = min(geradas, nova.parcelas)
    # Junto com o que correções anteriores deixaram pendente: o refazer deste pedido leva tudo.
    classificacao = _juntar(
        dict.fromkeys(CLASSIFICACAO & pedidas.keys(), desde), _classificacao_pendente(conn, id)
    )
    if editada:
        _seguir_o_parcelamento(conn, editada, nova, alteracao.model_fields_set | pedidas.keys())
    mantidas: set[int] = set()
    realizadas = [
        *tambem_mudam,
        *(
            t.aviso
            for t in _correcoes(
                conn,
                nova,
                geradas_depois,
                classificacao,
                lancamentos.hoje(),
                mantidas,
                _cronograma_pedido(alteracao),
            )
            # A que sai pulada sendo realizada já estava excluída (o encolher a tirou): nada muda.
            if t.realizada
            and t.acao not in ("reviver", "pular")
            and t.muda_o_cronograma
            and t.id != editada
        ),
    ]
    if editada:
        (numero,) = conn.execute(
            "SELECT parcela FROM lancamentos WHERE id = %s", (editada,)
        ).fetchone()
        mantidas.discard(numero)
    if realizadas and not alteracao.confirmar_realizadas:
        raise RealizadasMudam(
            AvisoDeRealizadas(
                motivo="a correção muda parcelas que já foram realizadas", parcelas=realizadas
            )
        )
    tags_de_antes = set(_tags_do_parcelamento(conn, id))
    tags = ids_das_tags(conn, nova.tags, usuario, tags_de_antes)
    if not conn.execute(
        "UPDATE parcelamentos SET valor_total_centavos = %s, parcelas = %s, data = %s,"
        " descricao = %s, pessoa = %s, item_categoria_id = %s, geradas = %s, alterado_por = %s,"
        " classificacao_pendente = %s, corrigido_em = %s, alterado_em = now()"
        " WHERE id = %s AND geradas = %s",
        (
            nova.valor_total_centavos,
            nova.parcelas,
            nova.data,
            nova.descricao,
            nova.pessoa,
            nova.item_categoria_id,
            geradas_depois,
            usuario,
            _gravar_classificacao(classificacao),
            lancamentos.hoje(),
            id,
            geradas,
        ),
    ).rowcount:
        raise psycopg.errors.SerializationFailure("o parcelamento mudou durante a correção")
    if set(nova.categoria_ids) != set(atual.categoria_ids):
        conn.execute("DELETE FROM parcelamento_categorias WHERE parcelamento_id = %s", (id,))
        for categoria in nova.categoria_ids:
            conn.execute(
                "INSERT INTO parcelamento_categorias (parcelamento_id, categoria_id)"
                " VALUES (%s, %s)",
                (id, categoria),
            )
    if set(tags) != tags_de_antes:
        conn.execute("DELETE FROM parcelamento_tags WHERE parcelamento_id = %s", (id,))
        for tag in tags:
            conn.execute(
                "INSERT INTO parcelamento_tags (parcelamento_id, tag_id) VALUES (%s, %s)",
                (id, tag),
            )
    return CorrecaoGravada(classificacao, mantidas)


def _cronograma_pedido(alteracao: AlteracaoDeParcelamento) -> frozenset[str]:
    """O valor e a data das parcelas que a correção pede para refazer."""
    pedidos = alteracao.model_fields_set
    campos = set()
    if pedidos & {"valor_total_centavos", "valor_da_parcela_centavos", "parcelas"}:
        campos.add("valor_centavos")
    if "data" in pedidos:
        campos.add("data")
    return frozenset(campos)


# O campo pedido ao parcelamento e os da parcela que ele refaz.
_CAMPOS_DA_CORRECAO = {
    "valor_total_centavos": ("valor_centavos",),
    "valor_da_parcela_centavos": ("valor_centavos",),
    "parcelas": ("valor_centavos",),
    "data": ("data", "fatura_mes"),
}


def _seguir_o_parcelamento(conn, editada: UUID, regra: Parcelamento, pedidos) -> None:
    """Tira a marca de "alterada à mão" da parcela editada nos campos que o pedido muda: ela
    passa a seguir o parcelamento neles, e a correção a refaz como as outras."""
    campos = [c for p in pedidos for c in _CAMPOS_DA_CORRECAO.get(p, (p,))]
    conn.execute(
        "UPDATE lancamento_campos SET origem = %s"
        " WHERE lancamento_id = %s AND origem IS NULL AND campo = ANY(%s)",
        (origem(regra.descricao), editada, campos),
    )


def _aplicar(
    conn,
    regra: Parcelamento,
    correcao: _Correcao,
    tags: list[UUID],
    usuario: str,
    agora: datetime,
) -> None:
    """Põe uma parcela como o parcelamento manda: sai, volta, muda ou sai como pulada."""
    if correcao.acao in ("excluir", "pular"):
        excluir(conn, correcao.id, None, usuario)
        if correcao.acao == "pular":
            conn.execute(
                "UPDATE lancamentos SET excluido_pela_regra = true WHERE id = %s", (correcao.id,)
            )
        return
    atribuicoes = "valor_centavos = %s, data = %s, mes = %s, alterado_por = %s, alterado_em = %s"
    parametros: tuple = (correcao.valor, correcao.dia, correcao.mes, usuario, agora)
    for campo in ("descricao", "pessoa", "item_categoria_id"):
        if campo in correcao.mudou:
            atribuicoes += f", {campo} = %s"
            parametros += (getattr(regra, campo),)
    if correcao.acao == "reviver":
        atribuicoes += ", excluido_em = NULL, excluido_por = NULL, excluido_pela_regra = false"
    if {"categoria_ids", "fatura_mes"} & set(correcao.mudou) or correcao.acao == "reviver":
        # No mês novo ou com a categoria nova, a parcela fica no item em que estava.
        lancamentos.guardar_item_atual_do_lancamento(conn, correcao.id)
        (item_atual,) = conn.execute(
            "SELECT item_atual_categoria_id FROM lancamentos WHERE id = %s", (correcao.id,)
        ).fetchone()
        atribuicoes += ", item_atual_categoria_id = %s"
        parametros += (item_atual if item_atual in regra.categoria_ids else None,)
    nova = subir_versao(conn, correcao.id, correcao.versao, atribuicoes, parametros)
    registrar_mudancas(
        conn, correcao.id, correcao.mudou, nova, usuario, agora, origem=origem(regra.descricao)
    )
    if "categoria_ids" in correcao.mudou:
        gravar_categorias(conn, correcao.id, regra.categoria_ids)
    if "tags" in correcao.mudou:
        conn.execute("DELETE FROM lancamento_tags WHERE lancamento_id = %s", (correcao.id,))
        for tag in tags:
            conn.execute(
                "INSERT INTO lancamento_tags (lancamento_id, tag_id) VALUES (%s, %s)",
                (correcao.id, tag),
            )


def _reajustar_um_lote(conn, id: UUID, usuario: str, classificacao: Classificacao) -> bool:
    """Põe as parcelas de acordo com o parcelamento de hoje, até um lote, e devolve se pode faltar
    alguma. A que já está como ele manda não conta, por isso o lote seguinte sempre anda."""
    if not (lidos := _ler(conn, "id = %s", (id,))):
        return False
    [regra] = lidos
    (geradas,) = conn.execute("SELECT geradas FROM parcelamentos WHERE id = %s", (id,)).fetchone()
    trabalho = _correcoes(conn, regra, geradas, classificacao)
    tags = _tags_do_parcelamento(conn, id)
    agora = datetime.now(UTC)
    por_lote = parcelas_por_lote(regra)
    for correcao in trabalho[:por_lote]:
        _aplicar(conn, regra, correcao, tags, usuario, agora)
    return len(trabalho) > por_lote


_AVISO = {409: {"model": AvisoDeRealizadas, "description": "A correção muda parcelas realizadas"}}


class ParcelamentoCorrigido(Parcelamento):
    # Quantas parcelas ficaram como estavam em algum campo da correção, porque uma pessoa o
    # mudou só nelas (ticket 136).
    parcelas_mantidas: int


def refazer_as_parcelas(url: str | None, id: UUID, usuario: str, classificacao) -> None:
    """Depois de gravada a correção, põe as parcelas de acordo, em lotes, e gera as que faltam."""
    # Import aqui: `automaticos` importa este módulo.
    from app import automaticos

    while em_transacao(url, lambda conn: _reajustar_um_lote(conn, id, usuario, classificacao)):
        pass
    # Antes de gerar: a geração já cria as parcelas com a classificação inteira.
    em_transacao(url, lambda conn: _dar_por_refeita(conn, id, classificacao))
    gerar_as_parcelas(url, id)
    # A parcela automática que a data nova já alcançou se realiza agora, como na criação.
    automaticos.realizar_automaticos(url, id)


@router.patch(
    "/parcelamentos/{id}",
    response_model=ParcelamentoCorrigido,
    operation_id="alterar_parcelamento",
    responses=_AVISO,
)
def alterar_parcelamento(
    id: UUID, alteracao: AlteracaoDeParcelamento, usuario: UsuarioLogado, request: Request
) -> ParcelamentoCorrigido | JSONResponse:
    """Corrige o parcelamento e põe as parcelas de acordo; a que uma pessoa mudou à mão fica como
    está nos campos que mudou, e a resposta diz quantas ficaram assim. Se uma parcela realizada
    mudar ou sair, responde 409 com o aviso e não grava nada até o pedido vir com
    `confirmar_realizadas`. Se parar no meio, repetir o pedido continua."""
    url = url_do_banco(request)
    try:
        mudanca = em_transacao(url, lambda conn: gravar_correcao(conn, id, alteracao, usuario))
    except RealizadasMudam as e:
        return JSONResponse(e.aviso.model_dump(mode="json"), status_code=409)
    refazer_as_parcelas(url, id, usuario, mudanca.classificacao)
    with conectar(url) as conn:
        if not (lidos := _ler(conn, "id = %s", (id,))):
            # Excluído por outra sessão no meio do refazer: as parcelas saíram com ele.
            raise HTTPException(status_code=404, detail="parcelamento não encontrado")
        return ParcelamentoCorrigido(
            **lidos[0].model_dump(), parcelas_mantidas=len(mudanca.mantidas)
        )


def _excluir_um_lote(conn, id: UUID, usuario: str) -> bool:
    """Exclui, até um lote, as parcelas do parcelamento, as realizadas também, e devolve se pode
    faltar alguma."""
    if not (lidos := _ler(conn, "id = %s", (id,))):
        return False
    por_lote = parcelas_por_lote(lidos[0])
    a_excluir = [
        lancamento_id
        for (lancamento_id,) in conn.execute(
            "SELECT id FROM lancamentos WHERE parcelamento_id = %s AND excluido_em IS NULL"
            " ORDER BY parcela LIMIT %s",
            (id, por_lote + 1),
        )
    ]
    for lancamento_id in a_excluir[:por_lote]:
        excluir(conn, lancamento_id, None, usuario)
    return len(a_excluir) > por_lote


@router.delete("/parcelamentos/{id}", status_code=204, operation_id="excluir_parcelamento")
def excluir_parcelamento(id: UUID, usuario: UsuarioLogado, request: Request) -> Response:
    """Idempotente. Exclui o parcelamento inteiro: todas as parcelas, também as realizadas e as
    que uma pessoa editou à mão (a exclusão de um lançamento é a de sempre: quem o edita depois
    recebe o aviso de excluído)."""
    url = url_do_banco(request)

    def fechar(conn) -> None:
        # Com todas as parcelas dadas por geradas, a tarefa diária não gera novas enquanto as de
        # agora saem.
        conn.execute("UPDATE parcelamentos SET geradas = parcelas WHERE id = %s", (id,))

    em_transacao(url, fechar)
    while em_transacao(url, lambda conn: _excluir_um_lote(conn, id, usuario)):
        pass

    def tirar(conn) -> None:
        conn.execute("DELETE FROM parcelamento_categorias WHERE parcelamento_id = %s", (id,))
        conn.execute("DELETE FROM parcelamento_tags WHERE parcelamento_id = %s", (id,))
        conn.execute("DELETE FROM parcelamentos WHERE id = %s", (id,))

    em_transacao(url, tirar)
    return Response(status_code=204)


class Antecipacao(BaseModel):
    """O pagamento adiantado das últimas parcelas que ainda não foram pagas."""

    # Quantas parcelas, tiradas do fim.
    parcelas: int = Field(ge=1)
    # O dia do pagamento; sem ele, hoje. Não pode ser futuro.
    data: date | None = None
    # O que foi pago pelas parcelas juntas (o desconto é a diferença); sem o campo, o valor
    # delas. Os centavos que sobram da divisão vão na primeira das antecipadas.
    valor_total_centavos: int | None = Field(default=None, gt=0)


class Quitacao(BaseModel):
    """O pagamento de uma vez de tudo o que falta."""

    data: date | None = None
    valor_total_centavos: int | None = Field(default=None, gt=0)


def _antecipar(
    conn, id: UUID, quantas: int | None, data: date | None, valor: int | None, usuario: str
) -> list[UUID]:
    """Realiza as últimas `quantas` parcelas previstas (todas, se `quantas` é `None`) no dia do
    pagamento, com o valor pago dividido entre elas. No cartão, a parcela conta na fatura em
    que foi paga (a que fecha depois do dia), marcada como troca à mão para as datas do
    cartão e a data da compra não a levarem de volta à fatura dela."""
    gravado = conn.execute(
        "SELECT geradas, parcelas FROM parcelamentos WHERE id = %s", (id,)
    ).fetchone()
    if not gravado:
        raise HTTPException(status_code=404, detail="parcelamento não encontrado")
    (geradas, total) = gravado
    dia = data or lancamentos.hoje()
    if dia > lancamentos.hoje():
        raise lancamentos.recusar("a antecipação é de um pagamento que já aconteceu")
    if geradas < total:
        raise lancamentos.recusar("as parcelas ainda estão sendo geradas")
    previstas = conn.execute(
        f"SELECT id, {lancamentos.VERSAO}, valor_centavos, conta_id, parcela FROM lancamentos"
        " WHERE parcelamento_id = %s AND situacao = 'previsto' AND excluido_em IS NULL"
        " ORDER BY parcela DESC",
        (id,),
    ).fetchall()
    quantas = len(previstas) if quantas is None else quantas
    if not previstas or quantas > len(previstas):
        raise lancamentos.recusar("não há tantas parcelas por pagar")
    escolhidas = previstas[:quantas][::-1]
    devido = sum(linha[2] for linha in escolhidas)
    pago = devido if valor is None else valor
    if pago < quantas:
        raise lancamentos.recusar("o valor não chega a um centavo por parcela")
    momento = datetime.now(UTC)
    for posicao, (lancamento_id, versao, _, conta_id, _) in enumerate(escolhidas, start=1):
        fatura = lancamentos.mes_em_que_conta(conn, conta_id, dia)
        no_cartao = faturas.ler_cartao(conn, conta_id) is not None
        lancamentos.guardar_item_atual_do_lancamento(conn, lancamento_id)
        nova = lancamentos.subir_versao(
            conn,
            lancamento_id,
            versao,
            "situacao = 'realizado', valor_centavos = %s, data = %s, mes = %s,"
            " fatura_a_mao = %s, alterado_por = %s, alterado_em = %s",
            (
                valor_da_parcela(pago, quantas, posicao),
                dia,
                fatura,
                no_cartao,
                usuario,
                momento,
            ),
        )
        campos = ["situacao", "valor_centavos", "data"] + (["fatura_mes"] if no_cartao else [])
        lancamentos.registrar_mudancas(conn, lancamento_id, campos, nova, usuario, momento)
    return [linha[0] for linha in escolhidas]


def _responder(url: str | None, antecipadas: list[UUID]) -> list[lancamentos.Lancamento]:
    with conectar(url) as conn:
        return sorted(
            lancamentos.ler_por_ids(conn, antecipadas), key=lambda parcela: parcela.parcela
        )


@router.post(
    "/parcelamentos/{id}/antecipacoes",
    response_model=list[lancamentos.Lancamento],
    operation_id="antecipar_parcelas",
)
def antecipar_parcelas(
    id: UUID, antecipacao: Antecipacao, usuario: UsuarioLogado, request: Request
) -> list[lancamentos.Lancamento]:
    """Paga adiantado as últimas K parcelas por pagar, no dia de hoje ou em outro, pelo valor
    informado (o desconto). Devolve as parcelas antecipadas."""
    url = url_do_banco(request)
    antecipadas = em_transacao(
        url,
        cartoes.protegida(
            lambda conn: _antecipar(
                conn,
                id,
                antecipacao.parcelas,
                antecipacao.data,
                antecipacao.valor_total_centavos,
                usuario,
            )
        ),
    )
    return _responder(url, antecipadas)


@router.post(
    "/parcelamentos/{id}/quitacao",
    response_model=list[lancamentos.Lancamento],
    operation_id="quitar_parcelamento",
)
def quitar_parcelamento(
    id: UUID, quitacao: Quitacao, usuario: UsuarioLogado, request: Request
) -> list[lancamentos.Lancamento]:
    """Paga de uma vez todas as parcelas que faltam. Devolve as parcelas quitadas."""
    url = url_do_banco(request)
    quitadas = em_transacao(
        url,
        cartoes.protegida(
            lambda conn: _antecipar(
                conn, id, None, quitacao.data, quitacao.valor_total_centavos, usuario
            )
        ),
    )
    return _responder(url, quitadas)
