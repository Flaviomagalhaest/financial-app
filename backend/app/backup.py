"""Backup: zip com um CSV por tabela, ids originais e um manifesto (ADR 0012).

O gerador só lê o banco. Ele descobre as tabelas sozinho, então uma tabela nova entra no
backup sem mudar este módulo; o controle de migrations fica de fora.
"""

import csv
import io
import json
import zipfile

import psycopg

VERSAO_FORMATO = 1
FORA_DO_BACKUP = {"controle_de_migrations"}
# Sem `real` e `double precision`: a soma de ponto flutuante muda com a ordem das linhas.
NUMERICOS = {"smallint", "integer", "bigint", "numeric"}


class BackupDivergente(Exception):
    """O zip não bate com o banco: o backup não vale."""


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
        como_texto = ", ".join(f"{_identificador(c)}::text" for c in colunas)
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


def _identificador(identificador: str) -> str:
    return '"' + identificador.replace('"', '""') + '"'
