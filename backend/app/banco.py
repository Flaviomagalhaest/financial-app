"""Conexão com o banco: Postgres por DATABASE_URL (local e CI) ou Aurora DSQL por IAM (na AWS)."""

import os
from pathlib import Path

import boto3
import botocore
import psycopg

PAPEL_DA_API = "api"


def conectar(
    url: str | None = None, *, autocommit: bool = False, admin: bool = False
) -> psycopg.Connection:
    """Abre uma conexão. Sem `url`, usa DSQL_ENDPOINT (token IAM, sem senha) ou DATABASE_URL.

    No DSQL a API entra com o papel `api`; só o job de deploy (migrations) pede `admin`.
    """
    if url is None and os.environ.get("DSQL_ENDPOINT"):
        return _conectar_ao_dsql(os.environ["DSQL_ENDPOINT"], autocommit, admin)
    return psycopg.connect(
        url or os.environ["DATABASE_URL"], connect_timeout=3, autocommit=autocommit
    )


def _conectar_ao_dsql(endpoint: str, autocommit: bool, admin: bool) -> psycopg.Connection:
    regiao = os.environ["AWS_REGION"]
    cliente = boto3.client("dsql", region_name=regiao)
    gerar = (
        cliente.generate_db_connect_admin_auth_token
        if admin
        else cliente.generate_db_connect_auth_token
    )
    token = gerar(endpoint, regiao)
    return psycopg.connect(
        host=endpoint,
        port=5432,
        dbname="postgres",
        user="admin" if admin else PAPEL_DA_API,
        password=token,
        sslmode="verify-full",
        # A cadeia do DSQL termina numa raiz pública; o pacote do botocore traz as raízes.
        sslrootcert=str(Path(botocore.__file__).parent / "cacert.pem"),
        connect_timeout=5,
        autocommit=autocommit,
    )
