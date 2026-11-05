"""Serviço da importação de carteira (Fase 3).

Reutiliza src.importer (validação e substituição atômica) e src.portfolio
(detecção de duplicidades). Um arquivo inválido nunca substitui o snapshot.
"""
from __future__ import annotations

from src.importer import validate_json, validation_messages
from src.portfolio import duplicate_positions


def preview_import(raw: bytes) -> tuple[object | None, list[str]]:
    """Valida o JSON e devolve (snapshot, erros); snapshot é None quando inválido."""
    try:
        snapshot = validate_json(raw)
        return snapshot, []
    except Exception as error:
        return None, validation_messages(error)


def duplicate_list(snapshot) -> list[list[str]]:
    return [list(item) for item in duplicate_positions(snapshot)]
