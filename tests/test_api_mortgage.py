"""Testes de integração do simulador de amortização (Fase 6)."""
import pytest
from fastapi.testclient import TestClient

from api.main import create_app

PARAMS = {
    "balance": 245135.45,
    "months": 226,
    "annual_interest": 0.107447,
    "annual_tr": 0.0,
    "monthly_fees": 0.0,
    "extra": 8464.0,
    "mode": "prazo",
    "net_annual_return": 0.10,
}


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def test_simulate_matches_domain_reference(client):
    from src.mortgage import build_sac_schedule

    reference = build_sac_schedule(
        PARAMS["balance"], PARAMS["months"], PARAMS["annual_interest"],
        PARAMS["annual_tr"], PARAMS["monthly_fees"],
    )
    response = client.post("/api/mortgage/simulate", json=PARAMS)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["months"] == PARAMS["months"]
    assert body["schedule_rows"][0]["parcela"] == float(reference.iloc[0]["Parcela"])
    assert body["total_interest"] == pytest.approx(float(reference["Juros"].sum()))
    assert len(body["schedule_rows"]) == 12


def test_compare_matches_domain_reference(client):
    from src.mortgage import (
        amortize_extra, break_even_net_return, build_sac_schedule,
        compare_with_investment, savings,
    )

    base = build_sac_schedule(
        PARAMS["balance"], PARAMS["months"], PARAMS["annual_interest"],
        PARAMS["annual_tr"], PARAMS["monthly_fees"],
    )
    alternative = amortize_extra(
        PARAMS["balance"], PARAMS["months"], PARAMS["annual_interest"],
        PARAMS["annual_tr"], PARAMS["extra"], PARAMS["mode"], PARAMS["monthly_fees"],
    )
    reference_metrics = savings(base, alternative)
    reference_comparison = compare_with_investment(base, alternative, PARAMS["extra"], PARAMS["net_annual_return"])
    reference_breakeven = break_even_net_return(base, alternative, PARAMS["extra"])

    response = client.post("/api/mortgage/compare", json=PARAMS)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["months_saved"] == int(reference_metrics["months_saved"])
    assert body["interest_saved"] == pytest.approx(reference_metrics["interest_saved"])
    assert body["winner"] == reference_comparison["winner"]
    assert body["difference"] == pytest.approx(float(reference_comparison["difference"]))
    assert body["break_even_net_return"] == pytest.approx(reference_breakeven, rel=1e-6)
    assert body["alternative_months"] < body["horizon_months"]
    si = [point for point in body["balance_series"] if point["scenario"] == "Sem amortização"]
    sa = [point for point in body["balance_series"] if point["scenario"] != "Sem amortização"]
    assert len(si) == body["horizon_months"]
    assert len(sa) == body["alternative_months"]


def test_compare_rejects_extra_above_balance(client):
    response = client.post("/api/mortgage/compare", json={**PARAMS, "extra": PARAMS["balance"] + 1})
    assert response.status_code == 400
    assert "saldo" in response.json()["detail"].lower()


def test_compare_rejects_invalid_mode(client):
    response = client.post("/api/mortgage/compare", json={**PARAMS, "mode": "juros"})
    assert response.status_code == 422


def test_compare_pagamento_vs_prazo(client):
    reduce_installment = client.post("/api/mortgage/compare", json={**PARAMS, "mode": "parcela"})
    assert reduce_installment.status_code == 200
    assert reduce_installment.json()["months_saved"] == 0  # mantém prazo, reduz parcela
