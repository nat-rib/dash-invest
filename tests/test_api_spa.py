from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app

DIST = Path("frontend/dist")


@pytest.mark.skipif(not DIST.exists(), reason="frontend não compilado")
def test_fallback_do_spa_serve_index_em_rota_profunda():
    with TestClient(create_app()) as client:
        response = client.get("/radar")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "root" in response.text or "vite" in response.text.lower()


@pytest.mark.skipif(not DIST.exists(), reason="frontend não compilado")
def test_fallback_nao_esconde_api_inexistente():
    with TestClient(create_app()) as client:
        response = client.get("/api/nao-existe")

    assert response.status_code == 404


@pytest.mark.skipif(not DIST.exists(), reason="frontend não compilado")
def test_fallback_serve_asset_real():
    asset = next((DIST / "assets").glob("*.js"), None)
    if asset is None:
        pytest.skip("nenhum asset compilado")

    with TestClient(create_app()) as client:
        response = client.get(f"/assets/{asset.name}")

    assert response.status_code == 200
