import csv
import io
import json
import zipfile

import pytest

from app.backup import BackupDivergente, conferir_backup, gerar_backup
from tests.exemplo_ficticio import CONTA_CORRENTE, CONTA_POUPANCA, trocar_arquivo


def ler_csv(backup: bytes, nome: str) -> list[list[str | None]]:
    with zipfile.ZipFile(io.BytesIO(backup)) as zip:
        texto = zip.read(nome).decode("utf-8")
    return list(csv.reader(io.StringIO(texto, newline=""), quoting=csv.QUOTE_NOTNULL))


def test_backup_tem_um_csv_por_tabela_com_os_ids_na_ordem_da_chave(banco_ficticio):
    backup = gerar_backup(banco_ficticio)

    with zipfile.ZipFile(io.BytesIO(backup)) as zip:
        # As tabelas do domínio (vazias aqui) vão junto com as do exemplo.
        nomes = set(zip.namelist())
    assert {
        "exemplo_contas.csv",
        "exemplo_lancamentos.csv",
        "lancamentos.csv",
        "manifesto.json",
    } <= nomes
    assert ler_csv(backup, "exemplo_contas.csv") == [
        ["id", "nome", "saldo_de_abertura"],
        [CONTA_CORRENTE, "Corrente", "250.50"],
        [CONTA_POUPANCA, "Poupança", "1000.00"],
    ]


def test_backup_distingue_nulo_de_texto_vazio_e_guarda_o_texto_como_esta(banco_ficticio):
    backup = gerar_backup(banco_ficticio)

    assert ler_csv(backup, "exemplo_lancamentos.csv") == [
        ["id", "conta_id", "descricao", "valor", "data", "observacao"],
        [
            "00000000-0000-0000-0000-000000000001",
            CONTA_CORRENTE,
            "Salário",
            "5000.00",
            "2026-10-01",
            None,
        ],
        [
            "00000000-0000-0000-0000-000000000002",
            CONTA_CORRENTE,
            'Pão; "fresco"',
            "-8.90",
            "2026-10-01",
            "linha 1\nlinha 2",
        ],
        [
            "00000000-0000-0000-0000-000000000003",
            CONTA_CORRENTE,
            "Mercado",
            "-120.35",
            "2026-10-02",
            "",
        ],
    ]


def test_manifesto_traz_a_versao_do_formato_as_contagens_e_as_somas(banco_ficticio):
    backup = gerar_backup(banco_ficticio)

    with zipfile.ZipFile(io.BytesIO(backup)) as zip:
        manifesto = json.loads(zip.read("manifesto.json"))
    do_exemplo = {n: t for n, t in manifesto["tabelas"].items() if n.startswith("exemplo_")}
    assert manifesto["versao_formato"] == 15
    assert manifesto["tabelas"]["lancamentos"] == {
        "linhas": 0,
        "somas": {"valor_centavos": "0", "versao": "0", "ocorrencia": "0"},
    }
    assert do_exemplo == {
        "exemplo_contas": {"linhas": 2, "somas": {"saldo_de_abertura": "1250.50"}},
        "exemplo_lancamentos": {"linhas": 3, "somas": {"valor": "4870.75"}},
    }


def test_o_mesmo_banco_gera_o_mesmo_zip_sem_a_hora_da_geracao(banco_ficticio):
    backup = gerar_backup(banco_ficticio)

    assert gerar_backup(banco_ficticio) == backup
    with zipfile.ZipFile(io.BytesIO(backup)) as zip:
        assert {info.date_time for info in zip.infolist()} == {(1980, 1, 1, 0, 0, 0)}


def test_conferencia_aceita_o_backup_do_proprio_banco(banco_ficticio):
    conferir_backup(banco_ficticio, gerar_backup(banco_ficticio))


def test_conferencia_recusa_zip_com_linha_faltando(banco_ficticio):
    backup = gerar_backup(banco_ficticio)
    with zipfile.ZipFile(io.BytesIO(backup)) as zip:
        sem_a_ultima = zip.read("exemplo_lancamentos.csv").decode().splitlines(keepends=True)[:-1]

    with pytest.raises(BackupDivergente, match="exemplo_lancamentos"):
        conferir_backup(
            banco_ficticio,
            trocar_arquivo(backup, "exemplo_lancamentos.csv", "".join(sem_a_ultima).encode()),
        )


def test_papel_so_de_leitura_gera_o_mesmo_backup_que_o_dono(banco_ficticio):
    # A chave primária não é a primeira coluna: a ordem pela chave difere da ordem pelas colunas.
    banco_ficticio.execute(
        "CREATE TABLE parcelas (descricao text NOT NULL, numero int PRIMARY KEY)"
    )
    banco_ficticio.execute("INSERT INTO parcelas VALUES ('b primeira', 1), ('a segunda', 2)")
    do_dono = gerar_backup(banco_ficticio)
    # Como o papel `backup` do DSQL: só SELECT (o DSQL já libera o schema public).
    banco_ficticio.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'so_leitura')"
        " THEN CREATE ROLE so_leitura; END IF; END $$"
    )
    banco_ficticio.execute("GRANT USAGE ON SCHEMA public TO so_leitura")
    banco_ficticio.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO so_leitura")
    banco_ficticio.execute("SET ROLE so_leitura")

    assert gerar_backup(banco_ficticio) == do_dono
