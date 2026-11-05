"""Configuração da API por variáveis de ambiente."""
from __future__ import annotations

import os
from pathlib import Path


def database_path() -> Path:
    return Path(os.environ.get("DASH_INVEST_DB_PATH", "data/dash_invest.db"))


def portfolio_path() -> Path:
    return Path(os.environ.get("PORTFOLIO_PATH", "portfolio.json"))


def default_portfolio_id() -> str:
    return os.environ.get("DASH_INVEST_PORTFOLIO_ID", "legacy-import")


def frontend_dist() -> Path:
    return Path(os.environ.get("FRONTEND_DIST", "frontend/dist"))
