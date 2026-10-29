"""Backup: zip com um CSV por tabela, ids originais e um manifesto (ADR 0012).

O gerador só lê o banco. Ele descobre as tabelas sozinho, então uma tabela nova entra no
backup sem mudar este módulo; o controle de migrations fica de fora. A restauração grava o zip
num banco vazio com as tabelas das migrations.
"""

import csv
import graphlib
import io
import json
import zipfile
from collections.abc import Callable
from decimal import Decimal

import psycopg

VERSAO_FORMATO = 13
# O DSQL aceita até 3.000 linhas e 10 MiB por transação: a restauração grava em lotes, e o
# texto do CSV conta para a folga dos bytes.
LINHAS_POR_LOTE = 1000
BYTES_POR_LOTE = 4 * 1024 * 1024

# Tabelas de um backup aberto: nome -> (colunas, linhas), cada valor no texto do Postgres.
Tabelas = dict[str, tuple[list[str], list[list[str | None]]]]


def _da_versao_1_para_a_2(manifesto: dict, tabelas: Tabelas) -> tuple[dict, Tabelas]:
    """A versão 2 tem as primeiras tabelas do domínio (ticket 32). O backup da 1 de `prod` é de
    antes delas, e elas entram vazias; o do `dev` pode já trazê-las, e fica como está."""
    novas = {
        "contas": ["id", "nome", "tipo", "criado_por", "criado_em"],
        "categorias": ["id", "nome", "tipo", "criado_por", "criado_em"],
        "lancamentos": [
            "id",
            "tipo",
            "situacao",
            "valor_centavos",
            "data",
            "descricao",
            "conta_id",
            "criado_por",
            "criado_em",
            "alterado_por",
            "alterado_em",
        ],
        "lancamento_categorias": ["lancamento_id", "categoria_id"],
    }
    somas = {"lancamentos": {"valor_centavos": "0"}}
    for tabela, colunas in novas.items():
        if tabela not in tabelas:
            tabelas[tabela] = (colunas, [])
            manifesto["tabelas"][tabela] = {"linhas": 0, "somas": somas.get(tabela, {})}
    return manifesto, tabelas


def _da_versao_2_para_a_3(manifesto: dict, tabelas: Tabelas) -> tuple[dict, Tabelas]:
    """A versão 3 tem o registro das exportações a pedido (ticket 66): backup antigo entra sem
    nenhum pedido registrado, e o que já trouxer a tabela fica como está."""
    if "exportacoes" not in tabelas:
        tabelas["exportacoes"] = (["id", "usuario", "formato", "criada_em"], [])
        manifesto["tabelas"]["exportacoes"] = {"linhas": 0, "somas": {}}
    return manifesto, tabelas


def _da_versao_3_para_a_4(manifesto: dict, tabelas: Tabelas) -> tuple[dict, Tabelas]:
    """A versão 4 (ticket 36) dá às contas saldo de abertura, data de abertura e arquivamento, e
    traz a tabela de transferências. Nas contas antigas as colunas novas ficam vazias."""
    colunas, linhas = tabelas["contas"]
    if "saldo_abertura_centavos" not in colunas:
        novas = ["saldo_abertura_centavos", "data_abertura", "arquivada_em"]
        tabelas["contas"] = (colunas + novas, [linha + [None] * len(novas) for linha in linhas])
        manifesto["tabelas"]["contas"]["somas"] = {"saldo_abertura_centavos": "0"}
    if "transferencias" not in tabelas:
        tabelas["transferencias"] = (
            [
                "id",
                "situacao",
                "valor_centavos",
                "data",
                "descricao",
                "conta_origem_id",
                "conta_destino_id",
                "categoria_id",
                "criado_por",
                "criado_em",
                "alterado_por",
                "alterado_em",
            ],
            [],
        )
        manifesto["tabelas"]["transferencias"] = {"linhas": 0, "somas": {"valor_centavos": "0"}}
    return manifesto, tabelas


def _da_versao_4_para_a_5(manifesto: dict, tabelas: Tabelas) -> tuple[dict, Tabelas]:
    """A versão 5 tem `arquivada_em` nas categorias (ticket 74): backup antigo entra com todas
    ativas, e o que já trouxer a coluna fica como está."""
    colunas, linhas = tabelas["categorias"]
    if "arquivada_em" not in colunas:
        tabelas["categorias"] = ([*colunas, "arquivada_em"], [[*linha, None] for linha in linhas])
    return manifesto, tabelas


def _da_versao_5_para_a_6(manifesto: dict, tabelas: Tabelas) -> tuple[dict, Tabelas]:
    """A versão 6 traz as tabelas das tags (ticket 40); backup antigo entra sem nenhuma."""
    novas = {
        "tags": ["id", "nome", "arquivada_em", "criado_por", "criado_em"],
        "lancamento_tags": ["lancamento_id", "tag_id"],
    }
    for tabela, colunas in novas.items():
        if tabela not in tabelas:
            tabelas[tabela] = (colunas, [])
            manifesto["tabelas"][tabela] = {"linhas": 0, "somas": {}}
    return manifesto, tabelas


def _da_versao_6_para_a_7(manifesto: dict, tabelas: Tabelas) -> tuple[dict, Tabelas]:
    """A versão 7 (ticket 34) dá ao lançamento a versão e a marca de exclusão, e traz a versão
    de cada campo. Os lançamentos antigos entram sem versão (lida como 1) e sem marca."""
    colunas, linhas = tabelas["lancamentos"]
    if "versao" not in colunas:
        novas = ["versao", "excluido_em", "excluido_por"]
        tabelas["lancamentos"] = (
            colunas + novas,
            [linha + [None] * len(novas) for linha in linhas],
        )
        manifesto["tabelas"]["lancamentos"]["somas"]["versao"] = "0"
    if "lancamento_campos" not in tabelas:
        tabelas["lancamento_campos"] = (
            ["lancamento_id", "campo", "versao", "alterado_por", "alterado_em", "origem"],
            [],
        )
        manifesto["tabelas"]["lancamento_campos"] = {"linhas": 0, "somas": {"versao": "0"}}
    return manifesto, tabelas


def _da_versao_7_para_a_8(manifesto: dict, tabelas: Tabelas) -> tuple[dict, Tabelas]:
    """A versão 8 traz os itens do planejamento (ticket 49); backup antigo entra sem nenhum."""
    if "itens_do_planejamento" not in tabelas:
        tabelas["itens_do_planejamento"] = (
            [
                "id",
                "mes",
                "categoria_id",
                "valor_centavos",
                "criado_por",
                "criado_em",
                "alterado_por",
                "alterado_em",
            ],
            [],
        )
        manifesto["tabelas"]["itens_do_planejamento"] = {
            "linhas": 0,
            "somas": {"valor_centavos": "0"},
        }
    return manifesto, tabelas


def _da_versao_8_para_a_9(manifesto: dict, tabelas: Tabelas) -> tuple[dict, Tabelas]:
    """A versão 9 (ticket 41) dá ao lançamento a pessoa, a fonte e a conferência do "Parece
    repetido". Os antigos entram do conjunto (sem pessoa), sem fonte (lida como "app") e sem
    conferência."""
    colunas, linhas = tabelas["lancamentos"]
    if "pessoa" not in colunas:
        novas = ["pessoa", "fonte", "repetido_mantido_em"]
        tabelas["lancamentos"] = (
            colunas + novas,
            [linha + [None] * len(novas) for linha in linhas],
        )
    return manifesto, tabelas


def _da_versao_9_para_a_10(manifesto: dict, tabelas: Tabelas) -> tuple[dict, Tabelas]:
    """A versão 10 traz o modelo padrão do planejamento (ticket 50); backup antigo entra com o
    modelo vazio."""
    if "modelo_do_planejamento" not in tabelas:
        tabelas["modelo_do_planejamento"] = (
            ["categoria_id", "valor_centavos", "alterado_por", "alterado_em"],
            [],
        )
        manifesto["tabelas"]["modelo_do_planejamento"] = {
            "linhas": 0,
            "somas": {"valor_centavos": "0"},
        }
    return manifesto, tabelas


def _da_versao_10_para_a_11(manifesto: dict, tabelas: Tabelas) -> tuple[dict, Tabelas]:
    """A versão 11 (ticket 44) traz as recorrências e liga o lançamento à regra que o gerou. Os
    lançamentos antigos entram avulsos (sem regra e sem ocorrência) e sem o automático."""
    colunas, linhas = tabelas["lancamentos"]
    if "recorrencia_id" not in colunas:
        novas = ["recorrencia_id", "ocorrencia", "automatico"]
        tabelas["lancamentos"] = (
            colunas + novas,
            [linha + [None] * len(novas) for linha in linhas],
        )
        manifesto["tabelas"]["lancamentos"]["somas"]["ocorrencia"] = "0"
    novas_tabelas = {
        "recorrencias": (
            [
                "id",
                "tipo",
                "valor_centavos",
                "tipo_do_valor",
                "automatico",
                "descricao",
                "conta_id",
                "inicio",
                "a_cada",
                "unidade",
                "ate",
                "vezes",
                "geradas",
                "criado_por",
                "criado_em",
                "alterado_por",
                "alterado_em",
                "pessoa",
            ],
            {"valor_centavos": "0", "a_cada": "0", "vezes": "0", "geradas": "0"},
        ),
        "recorrencia_categorias": (["recorrencia_id", "categoria_id"], {}),
        "recorrencia_tags": (["recorrencia_id", "tag_id"], {}),
    }
    for tabela, (colunas_novas, somas) in novas_tabelas.items():
        if tabela not in tabelas:
            tabelas[tabela] = (colunas_novas, [])
            manifesto["tabelas"][tabela] = {"linhas": 0, "somas": somas}
    return manifesto, tabelas


def _da_versao_11_para_a_12(manifesto: dict, tabelas: Tabelas) -> tuple[dict, Tabelas]:
    """A versão 12 (ticket 37) traz os cartões e as faturas e grava no lançamento o mês em que
    ele conta. Antes dela todo lançamento era de conta, que conta no mês da data."""
    colunas, linhas = tabelas["lancamentos"]
    if "mes" not in colunas:
        data = colunas.index("data")
        tabelas["lancamentos"] = (
            [*colunas, "mes", "fatura_a_mao"],
            [[*linha, linha[data][:8] + "01", None] for linha in linhas],
        )
    novas = {
        "cartoes": (
            [
                "id",
                "nome",
                "dia_fechamento",
                "dia_vencimento",
                "limite_centavos",
                "mes_anterior_ao_fechamento",
                "titular_id",
                "arquivado_em",
                "criado_por",
                "criado_em",
            ],
            {"dia_fechamento": "0", "dia_vencimento": "0", "limite_centavos": "0"},
        ),
        "faturas": (["cartao_id", "mes", "fechamento", "vencimento", "criado_em"], {}),
    }
    for tabela, (colunas_novas, somas) in novas.items():
        if tabela not in tabelas:
            tabelas[tabela] = (colunas_novas, [])
            manifesto["tabelas"][tabela] = {"linhas": 0, "somas": somas}
    return manifesto, tabelas


def _da_versao_12_para_a_13(manifesto: dict, tabelas: Tabelas) -> tuple[dict, Tabelas]:
    """A versão 13 (ticket 46) traz os parcelamentos e liga a parcela ao parcelamento que a
    gerou. Os lançamentos antigos entram avulsos, sem parcelamento e sem número de parcela."""
    colunas, linhas = tabelas["lancamentos"]
    if "parcelamento_id" not in colunas:
        tabelas["lancamentos"] = (
            [*colunas, "parcelamento_id", "parcela"],
            [[*linha, None, None] for linha in linhas],
        )
        manifesto["tabelas"]["lancamentos"]["somas"]["parcela"] = "0"
    novas = {
        "parcelamentos": (
            [
                "id",
                "valor_total_centavos",
                "parcelas",
                "data",
                "automatico",
                "descricao",
                "conta_id",
                "pessoa",
                "geradas",
                "criado_por",
                "criado_em",
                "alterado_por",
                "alterado_em",
            ],
            {"valor_total_centavos": "0", "parcelas": "0", "geradas": "0"},
        ),
        "parcelamento_categorias": (["parcelamento_id", "categoria_id"], {}),
        "parcelamento_tags": (["parcelamento_id", "tag_id"], {}),
    }
    for tabela, (colunas_novas, somas) in novas.items():
        if tabela not in tabelas:
            tabelas[tabela] = (colunas_novas, [])
            manifesto["tabelas"][tabela] = {"linhas": 0, "somas": somas}
    return manifesto, tabelas


# Conversor da versão N para a N+1: recebe e devolve o manifesto e as tabelas. O manifesto
# devolvido traz as contagens e as somas que o banco deve ter depois da restauração.
CONVERSORES: dict[int, Callable[[dict, Tabelas], tuple[dict, Tabelas]]] = {
    1: _da_versao_1_para_a_2,
    2: _da_versao_2_para_a_3,
    3: _da_versao_3_para_a_4,
    4: _da_versao_4_para_a_5,
    5: _da_versao_5_para_a_6,
    6: _da_versao_6_para_a_7,
    7: _da_versao_7_para_a_8,
    8: _da_versao_8_para_a_9,
    9: _da_versao_9_para_a_10,
    10: _da_versao_10_para_a_11,
    11: _da_versao_11_para_a_12,
    12: _da_versao_12_para_a_13,
}
FORA_DO_BACKUP = {"controle_de_migrations"}
# Sem `real` e `double precision`: a soma de ponto flutuante muda com a ordem das linhas.
NUMERICOS = {"smallint", "integer", "bigint", "numeric"}


class BackupDivergente(Exception):
    """O zip não bate com o banco: o backup não vale."""


class RestauracaoRecusada(Exception):
    """A restauração não começou: o banco e o backup continuam como estavam."""


class RestauracaoDesfeita(Exception):
    """A restauração falhou no meio e apagou o que tinha gravado: o banco voltou a ficar vazio."""


def gerar_backup(conn: psycopg.Connection) -> bytes:
    """Lê todas as tabelas e devolve o zip. Rode numa transação REPEATABLE READ, para as
    tabelas, as contagens e as somas saírem do mesmo instante do banco (veja `backup_diario`).
    """
    arquivos: dict[str, bytes] = {}
    tabelas: dict[str, dict] = {}
    for tabela in _tabelas(conn):
        tipos = _colunas(conn, tabela)
        colunas = list(tipos)
        ordem = _chave_primaria(conn, tabela) or colunas
        como_texto = ", ".join(_como_texto(c, tipo) for c, tipo in tipos.items())
        linhas = conn.execute(
            f"SELECT {como_texto} FROM {_identificador(tabela)}"
            f" ORDER BY {', '.join(_identificador(c) for c in ordem)}"
        ).fetchall()
        texto = io.StringIO(newline="")
        escritor = csv.writer(texto, quoting=csv.QUOTE_NOTNULL, lineterminator="\n")
        escritor.writerow(colunas)
        escritor.writerows(linhas)
        arquivos[f"{tabela}.csv"] = texto.getvalue().encode("utf-8")
        tabelas[tabela] = {"linhas": len(linhas), "somas": _somas(conn, tabela, tipos)}
    manifesto = {"versao_formato": VERSAO_FORMATO, "tabelas": tabelas}
    arquivos["manifesto.json"] = json.dumps(manifesto, ensure_ascii=False, indent=2).encode()

    # Sem a hora da geração: o mesmo banco dá o mesmo zip, byte a byte.
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as compactado:
        for nome, conteudo in arquivos.items():
            info = zipfile.ZipInfo(nome, date_time=(1980, 1, 1, 0, 0, 0))
            compactado.writestr(info, conteudo, compress_type=zipfile.ZIP_DEFLATED)
    return saida.getvalue()


def conferir_backup(conn: psycopg.Connection, backup: bytes) -> None:
    """Abre o zip e compara as tabelas e as contagens com o banco; diverge, levanta erro.

    Para não acusar a escrita de alguém no meio, rode na mesma transação da geração.
    Confere só as contagens: as somas do manifesto ficam para a restauração.
    """
    with zipfile.ZipFile(io.BytesIO(backup)) as compactado:
        manifesto = json.loads(compactado.read("manifesto.json"))
        no_zip = {
            nome.removesuffix(".csv") for nome in compactado.namelist() if nome.endswith(".csv")
        }
        no_banco = set(_tabelas(conn))
        if no_zip != no_banco or set(manifesto["tabelas"]) != no_banco:
            raise BackupDivergente(f"tabelas no zip {sorted(no_zip)}, no banco {sorted(no_banco)}")
        for tabela in sorted(no_banco):
            texto = io.StringIO(compactado.read(f"{tabela}.csv").decode("utf-8"), newline="")
            no_csv = sum(1 for _ in csv.reader(texto)) - 1
            (contagem,) = conn.execute(f"SELECT count(*) FROM {_identificador(tabela)}").fetchone()
            if no_csv != contagem or manifesto["tabelas"][tabela]["linhas"] != contagem:
                raise BackupDivergente(
                    f"{tabela}: {no_csv} linhas no CSV,"
                    f" {manifesto['tabelas'][tabela]['linhas']} no manifesto, {contagem} no banco"
                )


def restaurar_backup(conn: psycopg.Connection, backup: bytes) -> dict:
    """Grava o zip num banco vazio com as mesmas tabelas, tudo ou nada, e confere as contagens
    e as somas do banco contra o manifesto. Um backup de versão antiga é convertido antes.

    Recusa (`RestauracaoRecusada`) sem gravar nada se o banco tiver dados, o esquema não for o
    do backup, a versão for desconhecida ou os CSVs não baterem com o manifesto. Grava em lotes,
    um por transação, porque o DSQL limita as linhas por transação: a conexão vem em autocommit.
    Uma falha depois do primeiro lote apaga tudo o que foi gravado (`RestauracaoDesfeita`).
    Devolve o manifesto conferido, já na versão atual.
    """
    if not conn.autocommit:
        raise ValueError("a restauração grava um lote por transação: abra a conexão em autocommit")
    manifesto, tabelas = _abrir_backup(backup)
    versao = manifesto.get("versao_formato")
    if not (
        type(versao) is int  # `true` no JSON é um `int` para o isinstance
        and versao <= VERSAO_FORMATO
        and all(v in CONVERSORES for v in range(versao, VERSAO_FORMATO))
    ):
        raise RestauracaoRecusada(
            f"versão {versao} do formato desconhecida: esta restauração lê da"
            f" {min(CONVERSORES, default=VERSAO_FORMATO)} à {VERSAO_FORMATO}"
        )
    _conferir_manifesto(manifesto, tabelas)
    for anterior in range(versao, VERSAO_FORMATO):
        manifesto, tabelas = CONVERSORES[anterior](manifesto, tabelas)
        manifesto["versao_formato"] = anterior + 1
    no_banco = {tabela: set(_colunas(conn, tabela)) for tabela in _tabelas(conn)}
    no_backup = {tabela: set(colunas) for tabela, (colunas, _) in tabelas.items()}
    if diferentes := sorted(
        tabela
        for tabela in no_banco.keys() | no_backup.keys()
        if no_banco.get(tabela) != no_backup.get(tabela)
    ):
        raise RestauracaoRecusada(
            f"o esquema do banco não é o do backup em {', '.join(diferentes)}"
        )
    # Sem chave, o desfazer e o esvaziar não apagam em lotes.
    if sem_chave := [tabela for tabela in no_banco if not _chave_primaria(conn, tabela)]:
        raise RestauracaoRecusada(
            f"{', '.join(sem_chave)} sem chave primária: a restauração não daria para desfazer"
        )
    com_dados = [
        tabela
        for tabela in no_banco
        if conn.execute(f"SELECT EXISTS (SELECT FROM {_identificador(tabela)})").fetchone()[0]
    ]
    if com_dados:
        raise RestauracaoRecusada(f"o banco já tem dados em {', '.join(com_dados)}")
    ordem = _ordem_de_gravacao(conn)
    try:
        for tabela in ordem:
            colunas, linhas = tabelas[tabela]
            inserir = (
                f"INSERT INTO {_identificador(tabela)}"
                f" ({', '.join(_identificador(c) for c in colunas)})"
                f" VALUES ({', '.join(['%s'] * len(colunas))})"
            )
            for lote in _lotes(linhas):
                # O conflito da concorrência otimista do DSQL chega no COMMIT, no fim do `with`.
                try:
                    with conn.transaction(), conn.cursor() as cursor:
                        cursor.executemany(inserir, lote)
                except psycopg.Error as erro:
                    raise RestauracaoDesfeita(f"{tabela}: {erro}") from erro
        _conferir_gravado(conn, manifesto)
    except BaseException:
        esvaziar_banco(conn)
        raise
    return manifesto


def _lotes(linhas: list[list[str | None]]):
    lote: list[list[str | None]] = []
    tamanho = 0
    for linha in linhas:
        lote.append(linha)
        tamanho += sum(len(valor) for valor in linha if valor is not None)
        if len(lote) == LINHAS_POR_LOTE or tamanho >= BYTES_POR_LOTE:
            yield lote
            lote, tamanho = [], 0
    if lote:
        yield lote


def _conferir_gravado(conn: psycopg.Connection, manifesto: dict) -> None:
    """Contagens e somas do banco contra o manifesto, lidas depois de gravar."""
    for tabela, esperado in sorted(manifesto["tabelas"].items()):
        (contagem,) = conn.execute(f"SELECT count(*) FROM {_identificador(tabela)}").fetchone()
        if contagem != esperado["linhas"]:
            raise RestauracaoDesfeita(
                f"{tabela}: {contagem} linhas no banco, {esperado['linhas']} no manifesto"
            )
        somas = _somas(conn, tabela, _colunas(conn, tabela))
        # Como número: `1.50` e `1.5` são a mesma soma.
        if {c: Decimal(v) for c, v in somas.items()} != {
            c: Decimal(v) for c, v in esperado["somas"].items()
        }:
            raise RestauracaoDesfeita(
                f"{tabela}: somas {somas} no banco, {esperado['somas']} no manifesto"
            )


def esvaziar_banco(conn: psycopg.Connection) -> None:
    """Apaga as linhas de todas as tabelas do backup, em lotes pela chave primária e de trás
    para a frente nas chaves estrangeiras. O DSQL não tem `TRUNCATE`."""
    for tabela in reversed(_ordem_de_gravacao(conn)):
        chave = ", ".join(_identificador(c) for c in _chave_primaria(conn, tabela))
        if not chave:
            raise ValueError(f"{tabela} sem chave primária: não dá para apagar em lotes")
        apagar = (
            f"DELETE FROM {_identificador(tabela)} WHERE ({chave}) IN"
            f" (SELECT {chave} FROM {_identificador(tabela)} LIMIT {LINHAS_POR_LOTE})"
        )
        while True:
            with conn.transaction():
                if not conn.execute(apagar).rowcount:
                    break


def _conferir_manifesto(manifesto: dict, tabelas: Tabelas) -> None:
    """O zip chegou inteiro: as mesmas tabelas e as mesmas contagens nos CSVs e no manifesto."""
    if set(manifesto["tabelas"]) != set(tabelas):
        raise RestauracaoRecusada(
            f"tabelas nos CSVs {sorted(tabelas)}, no manifesto {sorted(manifesto['tabelas'])}"
        )
    for tabela, (_, linhas) in sorted(tabelas.items()):
        if len(linhas) != manifesto["tabelas"][tabela]["linhas"]:
            raise RestauracaoRecusada(
                f"{tabela}: {len(linhas)} linhas no CSV,"
                f" {manifesto['tabelas'][tabela]['linhas']} no manifesto"
            )


def _abrir_backup(backup: bytes) -> tuple[dict, Tabelas]:
    with zipfile.ZipFile(io.BytesIO(backup)) as compactado:
        manifesto = json.loads(compactado.read("manifesto.json"))
        tabelas: Tabelas = {}
        for nome in compactado.namelist():
            if nome.endswith(".csv"):
                texto = io.StringIO(compactado.read(nome).decode("utf-8"), newline="")
                colunas, *linhas = csv.reader(texto, quoting=csv.QUOTE_NOTNULL)
                tabelas[nome.removesuffix(".csv")] = (colunas, linhas)
    return manifesto, tabelas


def _tabelas(conn: psycopg.Connection) -> list[str]:
    nomes = conn.execute(
        "SELECT table_name FROM information_schema.tables"
        " WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name"
    ).fetchall()
    return [nome for (nome,) in nomes if nome not in FORA_DO_BACKUP]


def _colunas(conn: psycopg.Connection, tabela: str) -> dict[str, str]:
    """Nome e tipo de cada coluna, na ordem da tabela."""
    return dict(
        conn.execute(
            "SELECT column_name, data_type FROM information_schema.columns"
            " WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position",
            (tabela,),
        ).fetchall()
    )


def _somas(conn: psycopg.Connection, tabela: str, tipos: dict[str, str]) -> dict[str, str]:
    numericas = [coluna for coluna, tipo in tipos.items() if tipo in NUMERICOS]
    if not numericas:
        return {}
    somas = conn.execute(
        f"SELECT {', '.join(f'coalesce(sum({_identificador(c)}), 0)::text' for c in numericas)}"
        f" FROM {_identificador(tabela)}"
    ).fetchone()
    return dict(zip(numericas, somas))


def _chave_primaria(conn: psycopg.Connection, tabela: str) -> list[str]:
    """Colunas da chave primária, em ordem. Pelo `pg_catalog`: o `information_schema` esconde
    as restrições de quem só tem SELECT, como o papel `backup`."""
    nomes = conn.execute(
        "SELECT a.attname FROM pg_constraint c"
        " JOIN pg_class t ON t.oid = c.conrelid"
        " JOIN pg_namespace n ON n.oid = t.relnamespace"
        " CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS k(numero, ordem)"
        " JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.numero"
        " WHERE n.nspname = 'public' AND t.relname = %s AND c.contype = 'p'"
        " ORDER BY k.ordem",
        (tabela,),
    ).fetchall()
    return [nome for (nome,) in nomes]


def _como_texto(coluna: str, tipo: str) -> str:
    """O valor no texto do Postgres. O de `timestamptz` sai em UTC: o texto padrão segue o
    fuso da sessão, e a ida e volta entre sessões de fusos diferentes não daria o mesmo zip."""
    if tipo == "timestamp with time zone":
        return f"({_identificador(coluna)} AT TIME ZONE 'UTC')::text || '+00'"
    return f"{_identificador(coluna)}::text"


def _ordem_de_gravacao(conn: psycopg.Connection) -> list[str]:
    """As tabelas numa ordem em que cada uma vem depois das que ela referencia."""
    referencias = conn.execute(
        "SELECT t.relname, r.relname FROM pg_constraint c"
        " JOIN pg_class t ON t.oid = c.conrelid"
        " JOIN pg_class r ON r.oid = c.confrelid"
        " JOIN pg_namespace n ON n.oid = t.relnamespace"
        " WHERE n.nspname = 'public' AND c.contype = 'f' AND t.oid <> r.oid"
    ).fetchall()
    dependencias: dict[str, set[str]] = {tabela: set() for tabela in _tabelas(conn)}
    for tabela, referenciada in referencias:
        if tabela in dependencias and referenciada in dependencias:
            dependencias[tabela].add(referenciada)
    # Um ciclo de chaves entre tabelas levanta `graphlib.CycleError` antes de gravar.
    return list(graphlib.TopologicalSorter(dependencias).static_order())


def _identificador(identificador: str) -> str:
    return '"' + identificador.replace('"', '""') + '"'
