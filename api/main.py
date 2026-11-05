from __future__ import annotations
import math, os
from pathlib import Path
from typing import Any
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from src.importer import load_snapshot
from src.portfolio import positions_frame
from src.history import portfolio_history, position_history

PORTFOLIO_PATH = Path(os.getenv("PORTFOLIO_PATH", "portfolio.json"))
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", "frontend/dist"))
app = FastAPI(title="Dash Invest API", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

def clean(value: Any) -> Any:
    if value is None: return None
    if hasattr(value, "item"): value = value.item()
    if isinstance(value, float) and not math.isfinite(value): return None
    if hasattr(value, "isoformat"): return value.isoformat()
    return value

@app.get("/api/health")
def health(): return {"status": "ok"}

@app.get("/api/overview")
def overview() -> dict[str, Any]:
    if not PORTFOLIO_PATH.exists():
        return {"has_snapshot": False, "message": "Nenhum snapshot de carteira foi encontrado."}
    snapshot = load_snapshot(PORTFOLIO_PATH)
    frame = positions_frame(snapshot)
    positions = [{key: clean(value) for key, value in row.items()} for row in frame.to_dict(orient="records")]
    known = [row for row in positions if row["Valor consolidado BRL"] is not None]
    total = sum(float(row["Valor consolidado BRL"]) for row in known)
    classes, institutions = {}, {}
    for row in known:
        cls, inst, value = str(row["Classe"]), str(row["Instituição"]), float(row["Valor consolidado BRL"])
        classes[cls] = classes.get(cls, 0.0) + value
        institutions[inst] = institutions.get(inst, 0.0) + value
    top = sorted(known, key=lambda row: float(row["Valor consolidado BRL"]), reverse=True)[:5]
    for row in top: row["weight"] = float(row["Valor consolidado BRL"]) / total if total else None
    return {
        "has_snapshot": True, "snapshot_date": snapshot.snapshot_date.isoformat(), "currency": snapshot.currency,
        "metrics": {"total_brl": total if known else None, "assets": len(positions),
          "institutions": len({row["Instituição"] for row in positions}), "known_value": len(known),
          "known_cost": sum(row["Custo total"] is not None for row in positions),
          "converted": sum(row["Valor convertido BRL"] is not None for row in positions)},
        "allocation": [{"name": k, "value": v, "weight": v / total if total else 0} for k,v in sorted(classes.items(), key=lambda x:x[1], reverse=True)],
        "institutions_data": [{"name": k, "value": v, "weight": v / total if total else 0} for k,v in sorted(institutions.items(), key=lambda x:x[1], reverse=True)],
        "top_positions": top, "positions": positions, "data_source": "portfolio_snapshot_json",
        "performance": {"twr": None, "xirr": None, "benchmark": None,
          "note": "Rentabilidade não é inferida de um snapshot isolado."}
    }

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")
    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend(full_path: str):
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file() and FRONTEND_DIST in candidate.resolve().parents:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")


@app.get("/api/history")
def history() -> dict[str, Any]:
    """Read-only historical snapshots; not a return calculation."""
    wealth = portfolio_history()
    positions = position_history()
    def records(frame):
        return [{key: clean(value) for key, value in row.items()} for row in frame.to_dict(orient="records")]
    return {"wealth": records(wealth), "positions": records(positions),
            "note": "Variação patrimonial não equivale a rentabilidade: fluxos externos afetam os saldos."}
