"""Leitura e validação segura de snapshots JSON."""
import json
from pathlib import Path
import tempfile

from pydantic import ValidationError

from src.schemas import PortfolioSnapshot


def validate_json(raw: str | bytes) -> PortfolioSnapshot:
    """Valida JSON apenas como dados e retorna o snapshot tipado."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if not raw.strip():
        raise ValueError("O arquivo está vazio.")
    try:
        return PortfolioSnapshot.model_validate(json.loads(raw))
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON inválido: {error.msg}.") from error


def load_snapshot(path: Path) -> PortfolioSnapshot:
    return validate_json(path.read_text(encoding="utf-8"))


def replace_snapshot(path: Path, raw: bytes) -> PortfolioSnapshot:
    """Valida antes de substituir; um JSON inválido nunca altera o arquivo atual."""
    snapshot = validate_json(raw)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as temporary:
        temporary.write(raw)
        temp_path = Path(temporary.name)
    temp_path.replace(path)
    return snapshot


def validation_messages(error: Exception) -> list[str]:
    if isinstance(error, ValidationError):
        return [f"{' → '.join(map(str, item['loc']))}: {item['msg']}" for item in error.errors()]
    return [str(error)]
