import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.config import database_url
from app.migrations import total_aplicadas


class Saude(BaseModel):
    status: str
    migrations: int


def create_app(url: str | None = None) -> FastAPI:
    app = FastAPI(title="Financial App", version="0.1.0")

    @app.get("/api/saude", response_model=Saude, operation_id="saude")
    def saude() -> Saude:
        try:
            with psycopg.connect(url or database_url(), connect_timeout=3) as conn:
                return Saude(status="ok", migrations=total_aplicadas(conn))
        except psycopg.Error:
            raise HTTPException(status_code=503, detail="banco indisponível")

    return app
