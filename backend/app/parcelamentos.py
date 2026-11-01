"""Parcelamento: a compra ou a dívida em N parcelas. Ele não é um lançamento (ADR 0004): cada
parcela é um lançamento comum, ligado a ele pelo `parcelamento_id` e pelo número da parcela,
para o valor inteiro nunca contar de uma vez num mês só. No cartão, todas as parcelas têm a data
da compra e a parcela n cai n - 1 faturas depois da fatura da compra; fora dele (o boleto), a
parcela n vence n - 1 meses depois da primeira."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
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


# O alcance da edição aberta numa parcela (ticket 142): só ela, ela e as de depois, ou todas,
# inclusive as realizadas.
Alcance = Literal["esta", "proximas", "todas"]
# O que só muda no alcance "todas": refaz as parcelas.
CRONOGRAMA = frozenset({"valor_total_centavos", "valor_da_parcela_centavos", "parcelas", "data"})


class AlteracaoDeParcelamento(BaseModel):
    """O que se corrige num parcelamento; campo ausente fica como está. Descrição, categorias,
    tags, pessoa e item valem para as parcelas do `alcance`, inclusive as editadas à mão. Valor,
    número de parcelas e data só mudam no alcance "todas" e refazem as parcelas, salvo as que uma
    pessoa editou à mão. Se uma parcela realizada mudar ou sair, o pedido só vale com
    `confirmar_realizadas`."""

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
    # Sem o campo, "todas". "esta" e "proximas" contam a partir da `parcela`, o número da parcela
    # em que a edição foi aberta.
    alcance: Alcance = "todas"
    parcela: int | None = Field(default=None, ge=1)

    _tags = field_validator("tags")(tags_limpas)
    _categorias = field_validator("categoria_ids")(sem_repetidas)

    @model_validator(mode="after")
    def _um_valor(self):
        if self.valor_total_centavos is not None and self.valor_da_parcela_centavos is not None:
            raise ValueError("informe o valor total ou o da parcela, um dos dois")
        return self

    @model_validator(mode="after")
    def _alcance_com_a_parcela(self):
        if self.alcance == "todas":
            return self
        if self.parcela is None:
            raise ValueError(f'o alcance "{self.alcance}" precisa do número da parcela')
        if CRONOGRAMA & self.model_fields_set:
            raise ValueError('o total, o número de parcelas e a data só mudam no alcance "todas"')
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
    # Os campos que mudam nela (valor_centavos, data, fatura_mes, descricao, categoria_ids, tags,
    # pessoa, item_categoria_id); vazio quando ela sai.
    mudou: list[str] = []


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
    for correcao in _correcoes(conn, regra, geradas, _Classificacao()):
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
        _refazer_o_pendente(url, id)
        gerar_as_parcelas(url, id)
    return consertados


def _refazer_o_pendente(url: str | None, id: UUID) -> None:
    """Termina de pôr as parcelas como o parcelamento manda, com a classificação que ficou
    pendente, em nome de quem o alterou por último."""
    pendente = em_transacao(url, lambda conn: _classificacao_pendente(conn, id))
    while em_transacao(url, lambda conn: _reajustar_do_parcelamento(conn, id)):
        pass
    em_transacao(url, lambda conn: _dar_por_refeita(conn, id, pendente))


@dataclass(frozen=True)
class _Classificacao:
    """Os campos de classificação que uma correção leva às parcelas, da parcela `desde` em
    diante (o alcance "proximas" do ticket 142; "todas" é desde a 1ª)."""

    campos: frozenset[str] = frozenset()
    desde: int = 1

    def __bool__(self) -> bool:
        return bool(self.campos)

    def da_parcela(self, n: int) -> frozenset[str]:
        return self.campos if n >= self.desde else frozenset()

    def com(self, outra: "_Classificacao") -> "_Classificacao":
        """Junta a de um pedido à que ficou pendente. Duas com início diferente só se encontram
        quando dois pedidos correm juntos: vale a que começa antes."""
        if not (self and outra):
            return self or outra
        return _Classificacao(self.campos | outra.campos, min(self.desde, outra.desde))

    def gravada(self) -> str:
        """Como fica em `classificacao_pendente`: "descricao,tags", com "@N" no fim quando
        começa depois da 1ª parcela (o texto de antes do ticket 142 continua valendo)."""
        campos = ",".join(sorted(self.campos))
        return f"{campos}@{self.desde}" if campos and self.desde > 1 else campos

    @classmethod
    def lida(cls, texto: str | None) -> "_Classificacao":
        campos, _, desde = (texto or "").partition("@")
        return cls(frozenset(filter(None, campos.split(","))), int(desde or 1))


def _classificacao_pendente(conn, id: UUID) -> _Classificacao:
    """A classificação que correções já gravadas ainda não levaram às parcelas."""
    linha = conn.execute(
        "SELECT classificacao_pendente FROM parcelamentos WHERE id = %s", (id,)
    ).fetchone()
    return _Classificacao.lida(linha[0] if linha else None)


def _dar_por_refeita(conn, id: UUID, feita: _Classificacao) -> None:
    """Tira do pendente o que acabou de ser refeito; se outra correção gravou campos novos no
    meio, o pendente mudou e fica para ela."""
    conn.execute(
        "UPDATE parcelamentos SET classificacao_pendente = '' WHERE id = %s"
        " AND coalesce(classificacao_pendente, '') = %s",
        (id, feita.gravada()),
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


def _por_lote(regra: Parcelamento) -> int:
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
    mes_antes: date

    @property
    def muda_o_cronograma(self) -> bool:
        return self.acao in ("excluir", "pular") or (self.valor, self.dia) != (
            self.valor_antes,
            self.dia_antes,
        )

    @property
    def muda_alguma_coisa(self) -> bool:
        """Muda o cronograma ou a classificação (ticket 142: o alcance que atinge uma realizada
        pede confirmação)."""
        return self.muda_o_cronograma or bool(CLASSIFICACAO & set(self.mudou))

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
            mudou=[] if sai else self.mudou,
        )


# O que vale para todas as parcelas quando o pedido o traz, as editadas à mão também.
CLASSIFICACAO = frozenset({"descricao", "categoria_ids", "tags", "pessoa", "item_categoria_id"})


def _correcoes(
    conn,
    regra: Parcelamento,
    geradas: int,
    classificacao: "_Classificacao",
    dia_da_correcao: date | None = None,
) -> list[_Correcao]:
    """As parcelas que não estão como o parcelamento manda, na ordem do número. A que uma pessoa
    editou à mão (valor, data, conta ou fatura) fica como está nessas coisas. A classificação só
    se refaz no que o pedido trouxe (`classificacao`), e só nas parcelas do alcance dele, para a
    descrição que uma pessoa corrigiu numa parcela só não voltar a cada correção de valor. A parcela que saiu antes, quando o
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
        f" {lancamentos.ALTERADA_A_MAO}, COALESCE(excluido_pela_regra, false)"
        " FROM lancamentos WHERE parcelamento_id = %s"
        " ORDER BY parcela",
        (regra.id,),
    ).fetchall()
    ids = [linha[0] for linha in parcelas]
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
        a_mao,
        pulada,
    ) in parcelas:
        acao: _Acao = "atualizar"
        if excluida:
            if n > regra.parcelas or not (pulada or geradas < n):
                continue
            acao = "reviver"
        elif n > regra.parcelas:
            if a_mao:
                continue
            acao = "excluir"
        tem = {
            "descricao": descricao,
            "pessoa": pessoa,
            "item_categoria_id": item_categoria_id,
            "categoria_ids": categorias.get(lancamento_id, set()),
            "tags": tags.get(lancamento_id, set()),
        }
        campos = CLASSIFICACAO if acao == "reviver" else classificacao.da_parcela(n)
        # Com as categorias novas, sai o item da parcela que não é de nenhuma delas.
        if "categoria_ids" in campos and tem["item_categoria_id"] not in quer["categoria_ids"]:
            campos |= {"item_categoria_id"}
        mudou = [campo for campo in quer if campo in campos and quer[campo] != tem[campo]]
        valor, dia, mes = valor_antes, dia_antes, mes_antes
        if acao != "excluir" and not a_mao:
            valor = valor_da_parcela(regra.valor_total_centavos, regra.parcelas, n)
            dia = regra.data if no_cartao else mais_meses(regra.data, n - 1)
            if dia != dia_antes or acao == "reviver":
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
                    mes_antes,
                )
            )
    return feitas


def _mudar(
    conn, id: UUID, alteracao: AlteracaoDeParcelamento, usuario: str
) -> _Classificacao | None:
    """Valida e grava o parcelamento corrigido (recusa antes de gravar, e avisa se uma realizada
    mudaria sem `confirmar_realizadas`); as parcelas são refeitas depois, em lotes. Devolve a
    classificação que o pedido trouxe, ou `None` no alcance "esta", que já mudou a parcela."""
    if not (lidos := _ler(conn, "id = %s", (id,))):
        raise HTTPException(status_code=404, detail="parcelamento não encontrado")
    [atual] = lidos
    (geradas,) = conn.execute("SELECT geradas FROM parcelamentos WHERE id = %s", (id,)).fetchone()
    pedidas = alteracao.model_dump(
        include=alteracao.model_fields_set
        - {
            "valor_total_centavos",
            "valor_da_parcela_centavos",
            "confirmar_realizadas",
            "alcance",
            "parcela",
        }
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
    if alteracao.alcance == "esta":
        campos = _Classificacao(frozenset(CLASSIFICACAO & pedidas.keys()), alteracao.parcela)
        _mudar_so_esta(conn, nova, geradas, alteracao, campos, usuario)
        return None
    (a_mao,) = conn.execute(
        f"SELECT max(parcela) FROM lancamentos WHERE parcelamento_id = %s"
        f" AND excluido_em IS NULL AND {lancamentos.ALTERADA_A_MAO}",
        (id,),
    ).fetchone()
    if a_mao and a_mao > nova.parcelas:
        raise recusar(
            f"a parcela {a_mao} foi editada à mão: exclua-a antes de tirá-la do parcelamento"
        )
    geradas_depois = min(geradas, nova.parcelas)
    # Junto com o que correções anteriores deixaram pendente: o refazer deste pedido leva tudo.
    desde = alteracao.parcela if alteracao.alcance == "proximas" else 1
    if desde > atual.parcelas:
        raise recusar(f"a parcela {desde} não está no parcelamento")
    pedida = _Classificacao(frozenset(CLASSIFICACAO & pedidas.keys()), desde)
    classificacao = pedida.com(_classificacao_pendente(conn, id))
    realizadas = [
        t.aviso
        for t in _correcoes(conn, nova, geradas_depois, classificacao, lancamentos.hoje())
        # A que sai pulada sendo realizada já estava excluída (o encolher a tirou): nada muda.
        if t.realizada and t.acao not in ("reviver", "pular") and t.muda_alguma_coisa
    ]
    if realizadas and not alteracao.confirmar_realizadas:
        raise RealizadasMudam(_aviso_de_realizadas(realizadas))
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
            classificacao.gravada(),
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
    return classificacao


def _mudar_so_esta(
    conn,
    nova: Parcelamento,
    geradas: int,
    alteracao: AlteracaoDeParcelamento,
    campos: _Classificacao,
    usuario: str,
) -> None:
    """O alcance "esta": a classificação pedida vai só para a parcela da edição, e o parcelamento
    fica como estava. Valor, data e fatura dela não mudam."""
    n = alteracao.parcela
    tinha = conn.execute(
        "SELECT id FROM lancamentos WHERE parcelamento_id = %s AND parcela = %s"
        " AND excluido_em IS NULL",
        (nova.id, n),
    ).fetchone()
    if not tinha:
        raise recusar(f"a parcela {n} não está no parcelamento")
    achada = next(
        (
            c
            for c in _correcoes(conn, nova, geradas, campos, lancamentos.hoje())
            if c.parcela == n and c.acao == "atualizar"
        ),
        None,
    )
    mudou = [campo for campo in (achada.mudou if achada else []) if campo in CLASSIFICACAO]
    if not mudou:
        return
    correcao = replace(
        achada, mudou=mudou, valor=achada.valor_antes, dia=achada.dia_antes, mes=achada.mes_antes
    )
    if correcao.realizada and not alteracao.confirmar_realizadas:
        raise RealizadasMudam(_aviso_de_realizadas([correcao.aviso]))
    ja_tinha = {
        tag
        for (tag,) in conn.execute(
            "SELECT tag_id FROM lancamento_tags WHERE lancamento_id = %s", (tinha[0],)
        )
    }
    tags = ids_das_tags(conn, nova.tags, usuario, ja_tinha)
    _aplicar(conn, nova, correcao, tags, usuario, datetime.now(UTC))


def _aviso_de_realizadas(parcelas: list[ParcelaQueMuda]) -> AvisoDeRealizadas:
    return AvisoDeRealizadas(
        motivo="a correção muda parcelas já realizadas, e com elas o histórico do que já aconteceu",
        parcelas=parcelas,
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


def _reajustar_um_lote(conn, id: UUID, usuario: str, classificacao: _Classificacao) -> bool:
    """Põe as parcelas de acordo com o parcelamento de hoje, até um lote, e devolve se pode faltar
    alguma. A que já está como ele manda não conta, por isso o lote seguinte sempre anda."""
    if not (lidos := _ler(conn, "id = %s", (id,))):
        return False
    [regra] = lidos
    (geradas,) = conn.execute("SELECT geradas FROM parcelamentos WHERE id = %s", (id,)).fetchone()
    trabalho = _correcoes(conn, regra, geradas, classificacao)
    tags = _tags_do_parcelamento(conn, id)
    agora = datetime.now(UTC)
    por_lote = _por_lote(regra)
    for correcao in trabalho[:por_lote]:
        _aplicar(conn, regra, correcao, tags, usuario, agora)
    return len(trabalho) > por_lote


_AVISO = {409: {"model": AvisoDeRealizadas, "description": "A correção muda parcelas realizadas"}}


@router.patch(
    "/parcelamentos/{id}",
    response_model=Parcelamento,
    operation_id="alterar_parcelamento",
    responses=_AVISO,
)
def alterar_parcelamento(
    id: UUID, alteracao: AlteracaoDeParcelamento, usuario: UsuarioLogado, request: Request
) -> Parcelamento | JSONResponse:
    """Corrige o parcelamento e põe as parcelas de acordo; a que uma pessoa editou à mão fica como
    está. Se uma parcela realizada mudar ou sair, responde 409 com o aviso e não grava nada até o
    pedido vir com `confirmar_realizadas`. Se parar no meio, repetir o pedido continua."""
    # Import aqui: `automaticos` importa este módulo.
    from app import automaticos

    url = url_do_banco(request)
    pendente = em_transacao(url, lambda conn: _classificacao_pendente(conn, id))
    if pendente and (alteracao.alcance != "todas" or pendente.desde > 1):
        # Uma correção anterior parou no meio com outro alcance: juntas, uma levaria a outra
        # para parcelas fora do alcance dela. Termina a de antes, que já foi aceita.
        _refazer_o_pendente(url, id)
    try:
        classificacao = em_transacao(url, lambda conn: _mudar(conn, id, alteracao, usuario))
    except RealizadasMudam as e:
        return JSONResponse(e.aviso.model_dump(mode="json"), status_code=409)
    if classificacao is None:  # o alcance "esta" já mudou a parcela
        return _o_corrigido(url, id)
    while em_transacao(url, lambda conn: _reajustar_um_lote(conn, id, usuario, classificacao)):
        pass
    # Antes de gerar: a geração já cria as parcelas com a classificação inteira.
    em_transacao(url, lambda conn: _dar_por_refeita(conn, id, classificacao))
    gerar_as_parcelas(url, id)
    # A parcela automática que a data nova já alcançou se realiza agora, como na criação.
    automaticos.realizar_automaticos(url, id)
    return _o_corrigido(url, id)


def _o_corrigido(url: str | None, id: UUID) -> Parcelamento:
    with conectar(url) as conn:
        if not (lidos := _ler(conn, "id = %s", (id,))):
            # Excluído por outra sessão no meio do refazer: as parcelas saíram com ele.
            raise HTTPException(status_code=404, detail="parcelamento não encontrado")
        return lidos[0]


def _excluir_um_lote(conn, id: UUID, usuario: str) -> bool:
    """Exclui, até um lote, as parcelas do parcelamento, as realizadas também, e devolve se pode
    faltar alguma."""
    if not (lidos := _ler(conn, "id = %s", (id,))):
        return False
    por_lote = _por_lote(lidos[0])
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


class AvisoDeExclusao(BaseModel):
    """Excluir o parcelamento apagaria parcelas já pagas ou editadas à mão; nada foi apagado.
    Repetir o pedido com `confirmar_realizadas` apaga. As editadas à mão também entram nas
    outras contas quando são de fatura paga ou realizadas."""

    motivo: str
    # Quantas parcelas saem, de qualquer tipo.
    parcelas: int
    # No cartão, as da fatura que já recebeu pagamento.
    de_fatura_paga: int
    # As realizadas fora da fatura paga: no cartão, as da fatura aberta; no boleto, as pagas.
    realizadas: int
    editadas_a_mao: int


class ExclusaoPedeConfirmacao(Exception):
    def __init__(self, aviso: AvisoDeExclusao):
        self.aviso = aviso


def _aviso_de_exclusao(conn, id: UUID) -> AvisoDeExclusao | None:
    """O que a exclusão apagaria de já pago ou editado à mão; `None` se só há previstas."""
    linhas = conn.execute(
        f"SELECT conta_id, {lancamentos.MES_EM_QUE_CONTA}, situacao, {lancamentos.ALTERADA_A_MAO}"
        " FROM lancamentos WHERE parcelamento_id = %s AND excluido_em IS NULL",
        (id,),
    ).fetchall()
    pagas: dict[UUID, set[date]] = {}
    for conta_id in {linha[0] for linha in linhas}:
        cartao = faturas.ler_cartao(conn, conta_id)
        pagas[conta_id] = (
            {
                f.mes
                for f in cartoes.faturas_do_titular(conn, cartao.titular.id)
                if cartoes.paga_pelo_pagamento(f)
            }
            if cartao
            else set()
        )
    de_fatura_paga = sum(1 for conta_id, mes, *_ in linhas if mes in pagas[conta_id])
    realizadas = sum(
        1
        for conta_id, mes, situacao, _ in linhas
        if situacao == "realizado" and mes not in pagas[conta_id]
    )
    editadas = sum(1 for *_, a_mao in linhas if a_mao)
    if not (de_fatura_paga or realizadas or editadas):
        return None
    return AvisoDeExclusao(
        motivo="isto apaga lançamentos já pagos e pode desconfigurar o histórico",
        parcelas=len(linhas),
        de_fatura_paga=de_fatura_paga,
        realizadas=realizadas,
        editadas_a_mao=editadas,
    )


@router.delete(
    "/parcelamentos/{id}",
    status_code=204,
    operation_id="excluir_parcelamento",
    responses={
        409: {
            "model": AvisoDeExclusao,
            "description": "A exclusão apaga parcelas pagas ou editadas à mão",
        }
    },
)
def excluir_parcelamento(
    id: UUID, usuario: UsuarioLogado, request: Request, confirmar_realizadas: bool = False
) -> Response:
    """Idempotente. Exclui o parcelamento inteiro: todas as parcelas, também as realizadas e as
    que uma pessoa editou à mão (a exclusão de um lançamento é a de sempre: quem o edita depois
    recebe o aviso de excluído). Se alguma parcela é de fatura paga, realizada ou editada à mão,
    responde 409 com quantas de cada tipo e não apaga nada até o pedido vir com
    `confirmar_realizadas` (ticket 142)."""
    url = url_do_banco(request)

    def fechar(conn) -> None:
        if not confirmar_realizadas and (aviso := _aviso_de_exclusao(conn, id)):
            raise ExclusaoPedeConfirmacao(aviso)
        # Com todas as parcelas dadas por geradas, a tarefa diária não gera novas enquanto as de
        # agora saem.
        conn.execute("UPDATE parcelamentos SET geradas = parcelas WHERE id = %s", (id,))

    try:
        em_transacao(url, fechar)
    except ExclusaoPedeConfirmacao as e:
        return JSONResponse(e.aviso.model_dump(mode="json"), status_code=409)
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
