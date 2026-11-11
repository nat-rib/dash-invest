"""Importação de séries de preço (CSV ou provedor) para o banco de observações."""
from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Iterator
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from src.domain.observations import Observation, QualityStatus
from src.persistence.observations import ObservationRepository

CSV_PARSER_VERSION = "csv-prices-v1"
_DATE_ALIASES = ("date", "data", "dia")
_CLOSE_ALIASES = ("close", "fechamento", "preco", "preço", "price")


def _normalized(value: str) -> str:
    return value.strip().lower()


def _parse_date(value: str) -> date:
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    raise ValueError(f"data inválida: {value!r}")


def _parse_decimal(value: str) -> Decimal:
    text = value.strip().replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        number = Decimal(text)
    except InvalidOperation as error:
        raise ValueError(f"valor inválido: {value!r}") from error
    if not number.is_finite():
        raise ValueError(f"valor não finito: {value!r}")
    return number


def csv_price_observations(
    text: str,
    *,
    symbol: str,
    currency: str | None = None,
    provider: str = "csv",
    source_document: str | None = None,
) -> Iterator[Observation]:
    """Converte um CSV com colunas de data e fechamento em observações.

    Aceita cabeçalhos em português ou inglês (`date`/`Data`, `close`/`Fechamento`)
    e separadores `,` ou `;`.
    """
    sample = text.lstrip("\ufeff").splitlines()[:1]
    delimiter = ";" if sample and sample[0].count(";") > sample[0].count(",") else ","
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), delimiter=delimiter)
    if reader.fieldnames is None:
        raise ValueError("CSV sem cabeçalho.")

    fields = {_normalized(name): name for name in reader.fieldnames}
    date_field = next((fields[alias] for alias in _DATE_ALIASES if alias in fields), None)
    close_field = next((fields[alias] for alias in _CLOSE_ALIASES if alias in fields), None)
    if date_field is None or close_field is None:
        raise ValueError("CSV precisa de colunas de data e fechamento.")

    rows: list[tuple[date, Decimal]] = []
    for line, row in enumerate(reader, start=2):
        raw_date = (row.get(date_field) or "").strip()
        raw_close = (row.get(close_field) or "").strip()
        if not raw_date and not raw_close:
            continue
        if not raw_date or not raw_close:
            raise ValueError(f"linha {line}: data ou fechamento ausente.")
        rows.append((_parse_date(raw_date), _parse_decimal(raw_close)))

    for day, close in sorted(rows, key=lambda item: item[0]):
        yield Observation(
            provider=provider,
            metric="close",
            instrument_id=symbol,
            value=close,
            currency=currency,
            period_end=day,
            reference_date=day,
            parser_version=CSV_PARSER_VERSION,
            quality_status=QualityStatus.VERIFIED,
            source_document=source_document,
        )


def ingest_price_series(
    observations: Iterable[Observation],
    repository: ObservationRepository,
) -> int:
    return repository.record_many(observations)
