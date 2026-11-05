"""Rotas de análise e detalhes dos ativos (Fase 4 do roadmap)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException

from api.schemas.analysis import (
    AllocationOut, AllocationSlice, ComparablePosition, ConcentrationItem,
    ConcentrationOut, PositionDetailOut, PositionListOut, PositionSummaryOut,
)
from api.services import analysis_service

router = APIRouter(prefix="/api", tags=["analysis"])


def _bad_request(message: str, status_code: int = 400) -> HTTPException:
    return HTTPException(status_code=status_code, detail=message)


def _slice_out(slice: dict) -> AllocationSlice:
    return AllocationSlice(
        name=slice["name"],
        value=slice["value"],
        share=slice["share"],
        positions=slice["positions"],
    )


def _concentration_item(item: dict) -> ConcentrationItem:
    return ConcentrationItem(**item)


@router.get("/analysis/allocation", response_model=AllocationOut)
def allocation() -> AllocationOut:
    try:
        data = analysis_service.allocation()
    except FileNotFoundError as error:
        raise _bad_request(str(error)) from error
    except ValueError as error:
        raise _bad_request(f"Snapshot inválido: {error}") from error
    return AllocationOut(
        total_brl=str(data["total_brl"]),
        known_positions=data["known_positions"],
        unknown_positions=data["unknown_positions"],
        by_class=[_slice_out(item) for item in data["by_class"]],
        by_institution=[_slice_out(item) for item in data["by_institution"]],
    )


@router.get("/analysis/concentration", response_model=ConcentrationOut)
def concentration() -> ConcentrationOut:
    try:
        data = analysis_service.concentration()
    except (FileNotFoundError, ValueError) as error:
        raise _bad_request(str(error)) from error
    return ConcentrationOut(
        total_brl=data["total_brl"],
        items=[_concentration_item(item) for item in data["items"]],
        top=[_concentration_item(item) for item in data["top"]],
        comparable=[
            ComparablePosition(**item) for item in data["comparable"]
        ],
    )


@router.get("/portfolio/positions", response_model=PositionListOut)
def positions() -> PositionListOut:
    try:
        data = analysis_service.position_list()
    except (FileNotFoundError, ValueError) as error:
        raise _bad_request(str(error)) from error
    return PositionListOut(
        snapshot_date=data["snapshot_date"].isoformat(),
        positions=[PositionSummaryOut(**item) for item in data["positions"]],
    )


@router.get("/portfolio/positions/{position_id}", response_model=PositionDetailOut)
def position_detail(position_id: int) -> PositionDetailOut:
    try:
        detail = analysis_service.position_detail(position_id)
    except (FileNotFoundError, ValueError) as error:
        raise _bad_request(str(error)) from error
    except IndexError as error:
        raise _bad_request(str(error), status_code=404) from error

    def _string_date(value: object) -> str | None:
        return value.isoformat() if isinstance(value, date) else None

    payload = dict(detail)
    payload.pop("snapshot_date")
    for key in ("conversion_date", "maturity_date", "application_date"):
        payload[key] = _string_date(payload[key])
    for key, value in list(payload.items()):
        if isinstance(value, Decimal):
            payload[key] = str(value)
    return PositionDetailOut(**payload)
