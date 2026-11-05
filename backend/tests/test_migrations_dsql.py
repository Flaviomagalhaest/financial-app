import re

from app.migrations import PASTA

# O DSQL recusa `ADD COLUMN` com restrição (NOT NULL, DEFAULT, CHECK, UNIQUE, REFERENCES): a coluna
# entra nula e o código trata o NULL. O Postgres local aceitaria, e o erro só apareceria no deploy
# de prod, no passo das migrations.
COLUNA_COM_RESTRICAO = re.compile(
    r"ADD\s+COLUMN\b[^;]*\b(NOT\s+NULL|DEFAULT|CHECK|UNIQUE|REFERENCES|PRIMARY\s+KEY|GENERATED)\b",
    re.IGNORECASE,
)


def test_nenhuma_migration_adiciona_coluna_com_restricao():
    erradas = [
        arquivo.name
        for arquivo in sorted(PASTA.glob("[0-9][0-9][0-9][0-9]_*.sql"))
        if COLUNA_COM_RESTRICAO.search(arquivo.read_text())
    ]
    assert erradas == [], f"o DSQL não aceita ADD COLUMN com restrição: {erradas}"
