import os
from datetime import datetime

import boto3
import psycopg
from botocore.config import Config
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.banco import conectar
from app.cartoes import router as cartoes
from app.classificacao import router as classificacao
from app.exportacao import Formato, exportar
from app.lancamentos import router as lancamentos
from app.login import UsuarioLogado, VerificadorDeJwt, verificador_da_configuracao
from app.migrations import total_aplicadas
from app.transferencias import router as transferencias


class Saude(BaseModel):
    status: str
    migrations: int


class Eu(BaseModel):
    usuario: str


class PedidoDeExportacao(BaseModel):
    formato: Formato


class ExportacaoPronta(BaseModel):
    url: str
    arquivo: str
    expira_em: datetime


def create_app(
    url: str | None = None,
    verificador: VerificadorDeJwt | None = None,
    s3=None,
    bucket_de_exportacoes: str | None = None,
) -> FastAPI:
    app = FastAPI(title="Financial App", version="0.1.0")
    app.state.url = url
    app.state.verificador = verificador or verificador_da_configuracao()

    @app.get("/api/saude", response_model=Saude, operation_id="saude")
    def saude() -> Saude:
        try:
            with conectar(url) as conn:
                return Saude(status="ok", migrations=total_aplicadas(conn))
        except psycopg.Error:
            raise HTTPException(status_code=503, detail="banco indisponível")

    @app.get("/api/eu", response_model=Eu, operation_id="eu")
    def eu(usuario: UsuarioLogado) -> Eu:
        return Eu(usuario=usuario)

    @app.exception_handler(psycopg.errors.SerializationFailure)
    def disputa_perdida(_: Request, __: psycopg.errors.SerializationFailure) -> JSONResponse:
        # Esgotou as tentativas de em_transacao: o cliente pode repetir (a fila do app repete).
        return JSONResponse(
            {"detail": "banco ocupado, tente de novo"},
            status_code=503,
            headers={"Retry-After": "1"},
        )

    @app.post("/api/exportacoes", response_model=ExportacaoPronta, operation_id="exportar")
    def exportacoes(pedido: PedidoDeExportacao, usuario: UsuarioLogado) -> ExportacaoPronta:
        bucket = bucket_de_exportacoes or os.environ.get("EXPORTACOES_BUCKET")
        if not bucket:
            raise HTTPException(status_code=503, detail="exportação não configurada")
        # A URL assinada precisa da assinatura v3 (SigV4) do endereço regional do bucket.
        cliente_s3 = s3 or boto3.client("s3", config=Config(signature_version="s3v4"))
        pronta = exportar(cliente_s3, bucket, usuario, pedido.formato, url)
        return ExportacaoPronta(url=pronta.url, arquivo=pronta.arquivo, expira_em=pronta.expira_em)

    app.include_router(lancamentos)
    app.include_router(classificacao)
    app.include_router(transferencias)
    app.include_router(cartoes)
    return app
