"""Conexão com o banco: Postgres por DATABASE_URL (local e CI) ou Aurora DSQL por IAM (na AWS)."""

import os
from pathlib import Path

import psycopg


def conectar(url: str | None = None, *, autocommit: bool = False) -> psycopg.Connection:
    """Abre uma conexão. Sem `url`, usa DSQL_ENDPOINT (token IAM, sem senha) ou DATABASE_URL."""
    if url is None and os.environ.get("DSQL_ENDPOINT"):
        return _conectar_ao_dsql(os.environ["DSQL_ENDPOINT"], autocommit)
    return psycopg.connect(
        url or os.environ["DATABASE_URL"], connect_timeout=3, autocommit=autocommit
    )


def _conectar_ao_dsql(endpoint: str, autocommit: bool) -> psycopg.Connection:
    import boto3
    import botocore

    regiao = os.environ["AWS_REGION"]
    token = boto3.client("dsql", region_name=regiao).generate_db_connect_admin_auth_token(
        endpoint, regiao
    )
    return psycopg.connect(
        host=endpoint,
        port=5432,
        dbname="postgres",
        user="admin",
        password=token,
        sslmode="verify-full",
        # A cadeia do DSQL termina numa raiz pública; o pacote do botocore traz as raízes.
        sslrootcert=str(Path(botocore.__file__).parent / "cacert.pem"),
        connect_timeout=5,
        autocommit=autocommit,
    )
