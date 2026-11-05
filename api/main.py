"""Aplicação FastAPI do Dash-Invest.

Em produção serve o frontend compilado (frontend/dist), preservando a
implantação em um único container. O Streamlit permanece disponível para
uso local até a paridade funcional ser confirmada.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api import config
from api.routes import (
    analysis, import_snapshot, ledger, market, mortgage, overview, performance,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Conexões SQLite são curtas e abertas por operação; nada a fechar.


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dash Invest API",
        version="0.1.0",
        description=(
            "Contratos HTTP do Dash-Invest. Regras financeiras permanecem nos "
            "módulos Python de domínio; esta API só valida e orquestra."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )
    app.include_router(ledger.router)
    app.include_router(performance.router)
    app.include_router(import_snapshot.router)
    app.include_router(analysis.router)
    app.include_router(overview.router)
    app.include_router(market.router)
    app.include_router(mortgage.router)

    @app.get("/api/health", tags=["health"])
    def health() -> JSONResponse:
        try:
            from api.dependencies import get_database

            with get_database().connection() as connection:
                connection.execute("SELECT 1")
            return JSONResponse({"status": "ok"})
        except Exception as error:  # pragma: no cover - falha de infraestrutura
            logging.exception("Healthcheck falhou")
            return JSONResponse({"status": "unhealthy", "detail": str(error)}, status_code=503)

    dist = config.frontend_dist()
    if dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")

    return app


app = create_app()
