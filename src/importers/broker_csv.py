"""Adaptador configurável para extratos CSV de bancos e corretoras.

Não presume um layout universal: a UI fornece o mapeamento de colunas e o
catálogo de instrumentos. A saída passa pelo importador canônico já validado.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
from zoneinfo import ZoneInfo

from src.importers.transactions_csv import (
    CanonicalTransactionCsvImporter, TransactionCsvImportError, TransactionCsvImportResult,
)


CANONICAL_FIELDS = (
    "external_id", "occurred_at", "transaction_type", "institution", "currency",
    "instrument_id", "quantity", "unit_price", "amount", "fees", "taxes",
    "sequence", "transfer_id", "notes", "metadata_json",
)
DEFAULT_TYPE_ALIASES = {
    "COMPRA": "BUY", "BUY": "BUY",
    "VENDA": "SELL", "SELL": "SELL",
    "APORTE": "DEPOSIT", "DEPOSITO": "DEPOSIT", "DEPOSIT": "DEPOSIT",
    "RETIRADA": "WITHDRAWAL", "SAQUE": "WITHDRAWAL", "WITHDRAWAL": "WITHDRAWAL",
    "DIVIDENDO": "DIVIDEND", "DIVIDENDOS": "DIVIDEND", "DIVIDEND": "DIVIDEND",
    "JCP": "JCP", "JUROS": "INTEREST", "INTEREST": "INTEREST",
    "CUPOM": "COUPON", "COUPON": "COUPON",
    "AMORTIZACAO": "AMORTIZATION", "AMORTIZATION": "AMORTIZATION",
    "TAXA": "FEE", "TARIFA": "FEE", "FEE": "FEE",
    "IMPOSTO": "TAX", "TAX": "TAX",
    "BONIFICACAO": "BONUS", "BONUS": "BONUS",
    "DESDOBRAMENTO": "SPLIT", "SPLIT": "SPLIT",
    "TRANSFERENCIA ENTRADA": "TRANSFER_IN", "TRANSFER IN": "TRANSFER_IN",
    "TRANSFERENCIA SAIDA": "TRANSFER_OUT", "TRANSFER OUT": "TRANSFER_OUT",
}


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.strip().upper())
    return " ".join("".join(c for c in value if not unicodedata.combining(c)).split())


@dataclass(frozen=True)
class BrokerCsvMapping:
    institution: str
    currency: str
    columns: dict[str, str]
    instrument_map: dict[str, str] = field(default_factory=dict)
    type_aliases: dict[str, str] = field(default_factory=dict)
    delimiter: str = ","
    decimal_locale: str = "pt_BR"
    date_format: str = "%d/%m/%Y"
    timezone_name: str = "America/Sao_Paulo"


def _decimal(value: str, *, locale: str, line: int, field_name: str) -> str:
    raw = value.strip().replace("R$", "").replace("$", "").replace(" ", "")
    if locale == "pt_BR":
        raw = raw.replace(".", "").replace(",", ".")
    elif locale == "en_US":
        raw = raw.replace(",", "")
    else:
        raise TransactionCsvImportError(f"Locale decimal não suportado: {locale}.")
    try:
        number = Decimal(raw)
    except InvalidOperation:
        raise TransactionCsvImportError(f"Linha {line}: {field_name} não é um decimal válido.") from None
    if not number.is_finite():
        raise TransactionCsvImportError(f"Linha {line}: {field_name} precisa ser finito.")
    return format(number, "f")


def _date(value: str, mapping: BrokerCsvMapping, line: int) -> str:
    raw = value.strip()
    parsed = None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(raw, mapping.date_format)
        except ValueError:
            raise TransactionCsvImportError(
                f"Linha {line}: data não corresponde ao formato {mapping.date_format!r}."
            ) from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(mapping.timezone_name))
    return parsed.isoformat()


def _type(value: str, aliases: dict[str, str], line: int) -> str:
    key = _normalized(value)
    target = aliases.get(key, key)
    if target not in {
        "BUY", "SELL", "DEPOSIT", "WITHDRAWAL", "DIVIDEND", "JCP", "INTEREST",
        "COUPON", "AMORTIZATION", "TAX", "FEE", "SPLIT", "BONUS",
        "TRANSFER_IN", "TRANSFER_OUT",
    }:
        raise TransactionCsvImportError(f"Linha {line}: tipo de operação não mapeado: {value!r}.")
    return target


def to_canonical_csv(content: str, *, mapping: BrokerCsvMapping) -> str:
    """Normaliza o extrato para o CSV canônico, validando layout e mapeamento.

    Não persiste nada; a persistência é responsabilidade do importador canônico,
    garantindo prévia e confirmação com as mesmas regras.
    """
    if not mapping.institution.strip():
        raise TransactionCsvImportError("Informe a instituição.")
    reader = csv.DictReader(StringIO(content.lstrip("\ufeff")), delimiter=mapping.delimiter)
    headers = set(reader.fieldnames or [])
    required = {"occurred_at", "transaction_type"}
    missing_mapping = required - set(mapping.columns)
    if missing_mapping:
        raise TransactionCsvImportError("Mapeie as colunas: " + ", ".join(sorted(missing_mapping)))
    missing_headers = {
        source for source in mapping.columns.values()
        if source and source not in headers
    }
    if missing_headers:
        raise TransactionCsvImportError("Colunas não encontradas: " + ", ".join(sorted(missing_headers)))

    aliases = dict(DEFAULT_TYPE_ALIASES)
    aliases.update({_normalized(key): value for key, value in mapping.type_aliases.items()})
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=CANONICAL_FIELDS, lineterminator="\n")
    writer.writeheader()
    synthetic_counts: dict[str, int] = {}

    for line, source_row in enumerate(reader, start=2):
        def get(field_name: str) -> str:
            source = mapping.columns.get(field_name)
            return (source_row.get(source) or "").strip() if source else ""

        transaction_type = _type(get("transaction_type"), aliases, line)
        occurred_at = _date(get("occurred_at"), mapping, line)
        raw_instrument = get("instrument_id")
        instrument_id = mapping.instrument_map.get(raw_instrument) if raw_instrument else None
        if raw_instrument and not instrument_id:
            raise TransactionCsvImportError(
                f"Linha {line}: associe o ativo {raw_instrument!r} a um instrumento do catálogo."
            )
        if transaction_type in {"BUY", "SELL", "BONUS", "SPLIT"} and not instrument_id:
            raise TransactionCsvImportError(
                f"Linha {line}: associe o ativo {raw_instrument!r} a um instrumento do catálogo."
            )

        external_id = get("external_id")
        metadata = {}
        if not external_id:
            # Fingerprint determinístico para reimportar o mesmo arquivo sem duplicar.
            fingerprint = json.dumps(source_row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            base = hashlib.sha256(f"{mapping.institution}|{fingerprint}".encode()).hexdigest()
            occurrence = synthetic_counts.get(base, 0) + 1
            synthetic_counts[base] = occurrence
            external_id = f"sha256:{base}:{occurrence}"
            metadata["external_id_strategy"] = "content_fingerprint_with_row_occurrence"

        record = {
            "external_id": external_id,
            "occurred_at": occurred_at,
            "transaction_type": transaction_type,
            "institution": mapping.institution.strip(),
            "currency": (get("currency") or mapping.currency).upper(),
            "instrument_id": instrument_id or "",
            "transfer_id": get("transfer_id"),
            "notes": get("notes"),
            "metadata_json": json.dumps(metadata, ensure_ascii=False),
        }
        for field_name in ("quantity", "unit_price", "amount", "fees", "taxes"):
            raw = get(field_name)
            record[field_name] = _decimal(raw, locale=mapping.decimal_locale, line=line, field_name=field_name) if raw else ""
        sequence = get("sequence")
        record["sequence"] = sequence or "0"
        writer.writerow(record)

    if not synthetic_counts and output.getvalue().count("\n") <= 1:
        raise TransactionCsvImportError("O CSV não contém operações.")
    return output.getvalue()


def adapt_broker_csv(
    content: str,
    *,
    portfolio_id: str,
    mapping: BrokerCsvMapping,
    importer: CanonicalTransactionCsvImporter,
) -> TransactionCsvImportResult:
    """Conveniência compatível: adapta, valida e persiste em uma chamada."""
    return importer.import_text(
        to_canonical_csv(content, mapping=mapping), portfolio_id=portfolio_id
    )
