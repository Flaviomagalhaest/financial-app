"""O backup que a importação grava (ADR 0012): a `Importacao` vira o zip da versão atual do
formato, montado sem banco, e a restauração o grava num banco vazio. Tudo entra com a fonte
"mobills" e um único `criado_por`, do conjunto salvo a pessoa que o de-para der.

O zip sai como o gerador o escreveria do banco restaurado: as mesmas tabelas e colunas (do
esquema da versão), as linhas na ordem da chave e cada valor no texto do Postgres. Os ids vêm do
conteúdo e da ordem da importação, então os mesmos exports dão o mesmo zip.
"""

from datetime import UTC, date, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from app import pessoas
from app.backup import IMPORTADO_DO_MOBILLS, NUMERICOS, esquema, montar_backup
from app.faturas import Titular, datas_padrao
from app.mobills.importacao import FONTE, Importacao, Lancamento

# O `criado_por` de tudo o que veio do Mobills: um só, para o "Parece repetido" (que compara
# autores diferentes) não comparar o histórico com ele mesmo, e para o refazer saber o que é só
# importado (`app.backup.refazer_importacao`).
CRIADO_POR = IMPORTADO_DO_MOBILLS
_ESPACO = uuid5(NAMESPACE_URL, "https://github.com/Flaviomagalhaest/financial-app/mobills")


class ImportacaoComImpedimentos(Exception):
    """A planilha ainda precisa de edição: o backup não sai."""


def gerar_backup_da_importacao(importacao: Importacao, agora: datetime | None = None) -> bytes:
    """O zip do backup; `agora` é o `criado_em` de tudo (e o arquivamento dos cartões)."""
    if importacao.impedimentos:
        raise ImportacaoComImpedimentos("; ".join(importacao.impedimentos))
    agora = (agora or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    linhas = _Linhas(agora)
    configuradas = pessoas.configuradas()

    conta_id = uuid5(_ESPACO, "conta")
    linhas.incluir("contas", id=conta_id, nome=importacao.conta.nome, tipo=importacao.conta.tipo)
    cartoes: dict[str, Titular] = {}
    for cartao in importacao.cartoes:
        cartao_id = uuid5(_ESPACO, f"cartao {cartao.pasta}")
        cartoes[cartao.nome] = Titular(
            cartao_id, cartao.nome, cartao.fechamento, cartao.vencimento, False
        )
        linhas.incluir(
            "cartoes",
            id=cartao_id,
            nome=cartao.nome,
            dia_fechamento=cartao.fechamento,
            dia_vencimento=cartao.vencimento,
            mes_anterior_ao_fechamento=False,
            arquivado_em=agora if cartao.arquivado else None,
        )

    def conta_de(lancamento: Lancamento) -> UUID:
        return cartoes[lancamento.cartao].id if lancamento.cartao else conta_id

    def pessoa_de(lancamento: Lancamento) -> str | None:
        return lancamento.pessoa and pessoas.id_da_pessoa(lancamento.pessoa, configuradas)

    categorias: dict[tuple[str, str], UUID] = {}
    tags: dict[str, UUID] = {}

    def ids_das_categorias(lancamento: Lancamento) -> list[UUID]:
        for nome in lancamento.categorias:
            chave = (lancamento.tipo, nome)
            if chave not in categorias:
                categorias[chave] = uuid5(_ESPACO, f"categoria {lancamento.tipo} {nome}")
                linhas.incluir("categorias", id=categorias[chave], nome=nome, tipo=lancamento.tipo)
        return [categorias[(lancamento.tipo, nome)] for nome in lancamento.categorias]

    def ids_das_tags(lancamento: Lancamento) -> list[UUID]:
        for nome in lancamento.tags:
            if nome.casefold() not in tags:
                tags[nome.casefold()] = uuid5(_ESPACO, f"tag {nome.casefold()}")
                linhas.incluir("tags", id=tags[nome.casefold()], nome=nome)
        return list(dict.fromkeys(tags[nome.casefold()] for nome in lancamento.tags))

    # Cada parcela com o id do app, `uuid5(parcelamento, número)`, para a geração não duplicar.
    # Por lançamento (`_chave`): o parcelamento, o número da parcela e se ela é automática.
    parcela_de: dict[int, tuple[UUID, int, bool]] = {}
    for posicao, parcelamento in enumerate(importacao.parcelamentos):
        if not parcelamento.do_app:
            continue
        parcelamento_id = uuid5(_ESPACO, f"parcelamento {posicao}")
        primeira = parcelamento.primeira
        no_cartao = next((x for x in parcelamento.lancamentos if x.cartao), None)
        linhas.incluir(
            "parcelamentos",
            id=parcelamento_id,
            # As de antes do histórico contam no total com o valor da primeira que veio.
            valor_total_centavos=sum(x.valor_centavos for x in parcelamento.lancamentos)
            + parcelamento.anteriores * primeira.valor_centavos,
            parcelas=parcelamento.total,
            # No cartão, a data da compra; no boleto, a da 1ª parcela.
            data=no_cartao.data if no_cartao else parcelamento.data_da_1a(),
            automatico=no_cartao is not None,
            descricao=parcelamento.descricao,
            conta_id=conta_de(no_cartao or primeira),
            pessoa=pessoa_de(primeira),
            geradas=parcelamento.total,
            alterado_por=CRIADO_POR,
            alterado_em=agora,
        )
        for categoria in ids_das_categorias(primeira):
            linhas.incluir(
                "parcelamento_categorias", parcelamento_id=parcelamento_id, categoria_id=categoria
            )
        for tag in ids_das_tags(primeira):
            linhas.incluir("parcelamento_tags", parcelamento_id=parcelamento_id, tag_id=tag)
        for parcela in parcelamento.lancamentos:
            parcela_de[_chave(parcela)] = (
                parcelamento_id,
                parcela.parcela[0],
                no_cartao is not None,
            )

    meses_por_cartao: dict[str, set[str]] = {
        nome: set(meses) for nome, meses in importacao.meses_das_faturas.items()
    }
    for posicao, lancamento in enumerate(importacao.lancamentos):
        parcelamento_id, parcela, automatico = parcela_de.get(_chave(lancamento), (None,) * 3)
        lancamento_id = (
            uuid5(parcelamento_id, str(parcela))
            if parcelamento_id
            else uuid5(_ESPACO, f"lancamento {posicao}")
        )
        linhas.incluir(
            "lancamentos",
            id=lancamento_id,
            tipo=lancamento.tipo,
            situacao=lancamento.situacao,
            valor_centavos=lancamento.valor_centavos,
            data=lancamento.data,
            descricao=lancamento.descricao,
            conta_id=conta_de(lancamento),
            alterado_por=CRIADO_POR,
            alterado_em=agora,
            versao=1,
            pessoa=pessoa_de(lancamento),
            fonte=FONTE,
            automatico=automatico,
            mes=_dia_1(lancamento.mes),
            parcelamento_id=parcelamento_id,
            parcela=parcela,
        )
        for categoria in ids_das_categorias(lancamento):
            linhas.incluir(
                "lancamento_categorias", lancamento_id=lancamento_id, categoria_id=categoria
            )
        for tag in ids_das_tags(lancamento):
            linhas.incluir("lancamento_tags", lancamento_id=lancamento_id, tag_id=tag)
        if lancamento.cartao:
            meses_por_cartao[lancamento.cartao].add(lancamento.mes)

    ajustes: dict[tuple[str, str], int] = {}
    for ajuste in importacao.ajustes:
        chave = (ajuste.cartao, ajuste.mes)
        ajustes[chave] = ajustes.get(chave, 0) + ajuste.valor_centavos
        meses_por_cartao[ajuste.cartao].add(ajuste.mes)
    for nome, meses in meses_por_cartao.items():
        titular = cartoes[nome]
        ultima_exportada = max(importacao.meses_das_faturas[nome], default="")
        for mes in meses:
            # A fatura exportada nasce fechada e paga, sem datas (o app a lê assim); a que só
            # as parcelas futuras pedem nasce como no app, dos dias padrão do cartão.
            fechamento, vencimento = (
                (None, None) if mes <= ultima_exportada else datas_padrao(titular, _dia_1(mes))
            )
            linhas.incluir(
                "faturas",
                cartao_id=titular.id,
                mes=_dia_1(mes),
                fechamento=fechamento,
                vencimento=vencimento,
                ajuste_centavos=ajustes.get((nome, mes)),
            )
    return linhas.montar()


def _chave(lancamento: Lancamento) -> int:
    # O mesmo objeto está no parcelamento e na lista de lançamentos.
    return id(lancamento)


def _dia_1(mes: str) -> date:
    return date(int(mes[:4]), int(mes[5:]), 1)


class _Linhas:
    """As linhas de cada tabela do esquema, como o gerador as escreveria do banco."""

    def __init__(self, agora: datetime):
        self.agora = agora
        self.esquema = esquema()
        self.tabelas: dict[str, list[dict]] = {tabela: [] for tabela in self.esquema}

    def incluir(self, tabela: str, **valores) -> None:
        colunas = self.esquema[tabela]
        # Os padrões das colunas que o banco preencheria.
        for coluna, padrao in (
            ("criado_por", CRIADO_POR),
            ("criado_em", self.agora),
            ("excluido_pela_regra", False),
            ("classificacao_pendente", ""),
        ):
            if coluna in colunas:
                valores.setdefault(coluna, padrao)
        if fora := set(valores) - set(colunas):
            raise ValueError(f"{tabela} não tem as colunas {sorted(fora)}")
        self.tabelas[tabela].append(valores)

    def montar(self) -> bytes:
        tabelas = {}
        somas = {}
        for tabela in sorted(self.tabelas):
            tipos = self.esquema[tabela]
            linhas = sorted(
                ([_texto(valores.get(c)) for c in tipos] for valores in self.tabelas[tabela]),
                # A chave de cada tabela começa pelas primeiras colunas, e o texto de uuid e de
                # data ordena como o valor.
                key=lambda linha: [v or "" for v in linha],
            )
            tabelas[tabela] = (list(tipos), linhas)
            somas[tabela] = {
                coluna: str(sum(int(linha[i]) for linha in linhas if linha[i] is not None))
                for i, (coluna, tipo) in enumerate(tipos.items())
                if tipo in NUMERICOS
            }
        return montar_backup(tabelas, somas)


def _texto(valor) -> str | None:
    """O valor como `coluna::text` do Postgres; o `timestamptz` em UTC, como o gerador o lê."""
    if valor is None:
        return None
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, datetime):
        return f"{valor.astimezone(UTC):%Y-%m-%d %H:%M:%S}+00"
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor)
