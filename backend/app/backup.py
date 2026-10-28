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
NUMERICOS = {"smallint", "integer", "bigint", "numeric", "real", "double precision"}


class BackupDivergente(Exception):
    """O zip não bate com o banco: o backup não vale."""


def gerar_backup(conn: psycopg.Connection) -> bytes:
    arquivos: dict[str, bytes] = {}
    tabelas: dict[str, dict] = {}
    for tabela in _tabelas(conn):
        tipos = _colunas(conn, tabela)
        colunas = list(tipos)
        ordem = _chave(conn, tabela) or colunas
        linhas = conn.execute(
            f"SELECT {', '.join(f'{_nome(c)}::text' for c in colunas)} FROM {_nome(tabela)}"
            f" ORDER BY {', '.join(_nome(c) for c in ordem)}"
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
    with zipfile.ZipFile(saida, "w") as zip:
        for nome, conteudo in arquivos.items():
            info = zipfile.ZipInfo(nome, date_time=(1980, 1, 1, 0, 0, 0))
            zip.writestr(info, conteudo, compress_type=zipfile.ZIP_DEFLATED)
    return saida.getvalue()


def conferir_backup(conn: psycopg.Connection, backup: bytes) -> None:
    """Abre o zip e compara as tabelas e as contagens com o banco; diverge, levanta erro.

    Para não acusar a escrita de alguém no meio, rode na mesma transação da geração.
    """
    with zipfile.ZipFile(io.BytesIO(backup)) as zip:
        manifesto = json.loads(zip.read("manifesto.json"))
        no_zip = {nome.removesuffix(".csv") for nome in zip.namelist() if nome.endswith(".csv")}
        no_banco = set(_tabelas(conn))
        if no_zip != no_banco or set(manifesto["tabelas"]) != no_banco:
            raise BackupDivergente(f"tabelas no zip {sorted(no_zip)}, no banco {sorted(no_banco)}")
        for tabela in sorted(no_banco):
            texto = io.StringIO(zip.read(f"{tabela}.csv").decode("utf-8"), newline="")
            no_csv = sum(1 for _ in csv.reader(texto)) - 1
            (contagem,) = conn.execute(f"SELECT count(*) FROM {_nome(tabela)}").fetchone()
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
        f"SELECT {', '.join(f'coalesce(sum({_nome(c)}), 0)::text' for c in numericas)}"
        f" FROM {_nome(tabela)}"
    ).fetchone()
    return dict(zip(numericas, somas))


def _chave(conn: psycopg.Connection, tabela: str) -> list[str]:
    nomes = conn.execute(
        "SELECT k.column_name FROM information_schema.table_constraints t"
        " JOIN information_schema.key_column_usage k"
        "   ON k.constraint_schema = t.constraint_schema AND k.constraint_name = t.constraint_name"
        " WHERE t.table_schema = 'public' AND t.table_name = %s"
        "   AND t.constraint_type = 'PRIMARY KEY'"
        " ORDER BY k.ordinal_position",
        (tabela,),
    ).fetchall()
    return [nome for (nome,) in nomes]


def _nome(identificador: str) -> str:
    return '"' + identificador.replace('"', '""') + '"'
