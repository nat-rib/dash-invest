"""Rotas do simulador de amortização (Fase 6 do roadmap)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas.mortgage import BalancePoint, CompareIn, CompareOut, ScheduleRow, SimulationIn, SimulationOut
from api.services import mortgage_service

router = APIRouter(prefix="/api/mortgage", tags=["mortgage"])


def _bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)


@router.post("/simulate", response_model=SimulationOut)
def simulate(body: SimulationIn) -> SimulationOut:
    try:
        data = mortgage_service.simulate(body, rows_limit=body.rows_limit)
    except ValueError as error:
        raise _bad_request(str(error)) from error
    return SimulationOut(
        months=data["months"],
        total_interest=data["total_interest"],
        total_paid=data["total_paid"],
        schedule_rows=[ScheduleRow(**row) for row in data["schedule_rows"]],
        final_balance_series=[BalancePoint(**row) for row in data["final_balance_series"]],
    )


@router.post("/compare", response_model=CompareOut)
def compare(body: CompareIn) -> CompareOut:
    if body.extra >= body.balance:
        raise _bad_request("A amortização extra deve ser maior que zero e menor que o saldo devedor.")
    try:
        data = mortgage_service.compare(body)
    except ValueError as error:
        raise _bad_request(str(error)) from error
    return CompareOut(
        months_saved=data["months_saved"],
        interest_saved=data["interest_saved"],
        payment_saved=data["payment_saved"],
        invest_value=data["invest_value"],
        amortization_value=data["amortization_value"],
        difference=data["difference"],
        winner=data["winner"],
        break_even_net_return=data["break_even_net_return"],
        horizon_months=data["horizon_months"],
        invest_at_end=data["invest_value"],
        amortize_at_end=data["amortization_value"],
        alternative_months=data["alternative_months"],
        balance_series=[BalancePoint(**row) for row in data["balance_series"]],
    )
