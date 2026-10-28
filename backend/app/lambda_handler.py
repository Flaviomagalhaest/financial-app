"""Entrada da Lambda: a HTTP API chama a mesma FastAPI que roda local com uvicorn."""

from mangum import Mangum

from app.main import create_app

handler = Mangum(create_app(), lifespan="off")
