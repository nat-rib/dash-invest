"""Rotas da importação de carteira (Fase 3 do roadmap).

Prévia e confirmação são etapas separadas: o arquivo é validado como dados,
exibido ao usuário e só substitui o snapshot após confirmação explícita.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.config import portfolio_path
from api.schemas.import_snapshot import (
    ImportConfirmOut, ImportPositionOut, ImportPreviewOut,
)
from api.services import import_service
from src.importer import replace_snapshot

router = APIRouter(prefix="/api/import", tags=["import"])


def _bad_request(message: str, status_code: int = 400) -> HTTPException:
    return HTTPException(status_code=status_code, detail=message)


def _read_json(file: UploadFile) -> bytes:
    raw = file.file.read()
    if not raw:
        raise _bad_request("O arquivo JSON está vazio.")
    if len(raw) > 10 * 1024 * 1024:
        raise _bad_request("Arquivo muito grande (limite de 10 MB).")
    return raw


def _position_out(position) -> ImportPositionOut:
    return ImportPositionOut(
        institution=position.institution,
        asset_class=str(position.asset_class),
        ticker=position.ticker,
        name=position.name,
        quantity=str(position.quantity) if position.quantity is not None else None,
        currency=position.currency,
    )


@router.post("/snapshot/preview", response_model=ImportPreviewOut)
def preview_import(file: Annotated[UploadFile, File()]) -> ImportPreviewOut:
    raw = _read_json(file)
    snapshot, errors = import_service.preview_import(raw)
    if snapshot is None:
        return ImportPreviewOut(
            snapshot_date="",
            currency="",
            positions=[],
            duplicates=[],
            valid=False,
            validation_errors=errors,
            message="O arquivo não passou na validação; nenhum dado foi alterado.",
        )
    return ImportPreviewOut(
        snapshot_date=snapshot.snapshot_date.isoformat(),
        currency=snapshot.currency,
        positions=[_position_out(position) for position in snapshot.positions],
        duplicates=import_service.duplicate_list(snapshot),
        valid=True,
        validation_errors=[],
        message=(f"Arquivo válido: {len(snapshot.positions)} posições."),
    )


@router.post("/snapshot/confirm", response_model=ImportConfirmOut)
def confirm_import(
    file: Annotated[UploadFile, File()],
    confirm_replacement: Annotated[str, Form()] = "",
) -> ImportConfirmOut:
    if confirm_replacement.strip().lower() not in {"true", "1", "yes", "on"}:
        raise _bad_request("Confirmação explícita obrigatória para substituir a carteira.")
    raw = _read_json(file)
    snapshot, errors = import_service.preview_import(raw)
    if snapshot is None:
        raise _bad_request(
            "O arquivo não passou na validação; o snapshot atual foi preservado.",
            status_code=422,
        )
    # REutiliza a substituição atômica validada: grava em arquivo temporário e
    # só então substitui o snapshot corrente.
    replace_snapshot(portfolio_path(), raw)
    return ImportConfirmOut(
        snapshot_date=snapshot.snapshot_date.isoformat(),
        positions=len(snapshot.positions),
        message="Carteira substituída com sucesso.",
    )
