"""Serviço do simulador de amortização (Fase 6).

Reutiliza integralmente src.mortgage (SAC+TR, comparação e equilíbrio).
A simulação não executa nenhuma operação bancária real.
"""
from __future__ import annotations

from src.mortgage import (
    amortize_extra, break_even_net_return, build_sac_schedule,
    compare_with_investment, savings,
)


def _base_schedule(params) -> object:
    return build_sac_schedule(
        params.balance, params.months, params.annual_interest,
        params.annual_tr, params.monthly_fees,
    )


def _alternative_schedule(params) -> object:
    return amortize_extra(
        params.balance, params.months, params.annual_interest,
        params.annual_tr, params.extra, params.mode, params.monthly_fees,
    )


def _rows(frame) -> list[dict]:
    return [
        {
            "month": int(row["Mês"]),
            "saldo_inicial": float(row["Saldo inicial"]),
            "saldo_corrigido": float(row["Saldo corrigido"]),
            "amortizacao": float(row["Amortização"]),
            "juros": float(row["Juros"]),
            "encargos": float(row["Encargos"]),
            "parcela": float(row["Parcela"]),
            "saldo_final": float(row["Saldo final"]),
        }
        for _, row in frame.iterrows()
    ]


def _balance_series(frame, scenario: str) -> list[dict]:
    return [
        {"month": int(row["Mês"]), "saldo_final": float(row["Saldo final"]), "scenario": scenario}
        for _, row in frame.iterrows()
    ]


def simulate(params, *, rows_limit: int) -> dict:
    frame = _base_schedule(params)
    return {
        "months": len(frame),
        "total_interest": float(frame["Juros"].sum()),
        "total_paid": float(frame["Parcela"].sum()),
        "schedule_rows": _rows(frame.head(rows_limit)),
        "final_balance_series": _balance_series(frame, "Sem amortização"),
    }


def compare(params) -> dict:
    base = _base_schedule(params)
    alternative = _alternative_schedule(params)
    metrics = savings(base, alternative)
    comparison = compare_with_investment(base, alternative, params.extra, params.net_annual_return)
    breakeven = break_even_net_return(base, alternative, params.extra)
    return {
        "months_saved": int(metrics["months_saved"]),
        "interest_saved": metrics["interest_saved"],
        "payment_saved": metrics["payment_saved"],
        "invest_value": float(comparison["invest_value"]),
        "amortization_value": float(comparison["amortization_value"]),
        "difference": float(comparison["difference"]),
        "winner": str(comparison["winner"]),
        "break_even_net_return": breakeven,
        "horizon_months": len(base),
        "alternative_months": len(alternative),
        "balance_series": _balance_series(base, "Sem amortização") + _balance_series(
            alternative, f"Amortizar — {params.mode}",
        ),
    }
