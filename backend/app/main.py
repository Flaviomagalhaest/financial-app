import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.banco import conectar
from app.lancamentos import router as lancamentos
from app.login import UsuarioLogado, VerificadorDeJwt, verificador_da_configuracao
from app.migrations import total_aplicadas


class Saude(BaseModel):
    status: str
    migrations: int


class Eu(BaseModel):
    usuario: str


def create_app(url: str | None = None, verificador: VerificadorDeJwt | None = None) -> FastAPI:
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

    app.include_router(lancamentos)
    return app
