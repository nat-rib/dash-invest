"""Adaptador CVM DFP (Demonstrações Financeiras Padronizadas).

Fluxo: baixar o ZIP anual de dados abertos da CVM → ler o índice de documentos
(`DT_RECEB`/link) → converter cada linha das demonstrações em `Observation`.

Convenções:
- `instrument_id` usa `cnpj:<14 dígitos>` porque a DFP é uma visão por emissor;
  o vínculo com um `Instrument` interno pode ser feito depois via CNPJ/CD_CVM.
- valores em `ESCALA_MOEDA=MIL` são normalizados para unidades (×1000).
- `ORDEM_EXERC=PENÚLTIMO` é descartado: representa o exercício comparativo.
- linhas sem `VL_CONTA` são ignoradas; ausência nunca vira zero.
"""
from __future__ import annotations

import csv
import io
import json
import unicodedata
import urllib.request
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation

from src.domain.observations import Observation, QualityStatus

DFP_BASE_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS"
PARSER_VERSION = "cvm-dfp-v1"
DFP_STATEMENTS = ("DRE", "BPA", "BPP")

# Mapeamento best-effort de contas padronizadas para métricas canônicas.
# O código original sempre permanece em `raw_payload`.
CANONICAL_METRICS: dict[tuple[str, str], str] = {
    ("DRE", "3.01"): "revenue",
    ("DRE", "3.03"): "gross_profit",
    ("DRE", "3.05"): "operating_income",
    ("DRE", "3.11"): "net_income",
    ("BPA", "1"): "total_assets",
    ("BPA", "1.01"): "current_assets",
    ("BPP", "2.01"): "current_liabilities",
    ("BPP", "2.03"): "equity",
}

CVM_CURRENCIES = {"REAL": "BRL", "DOLAR": "USD", "EURO": "EUR"}


class CvmParseError(ValueError):
    """Linha da DFP inválida; o lote inteiro deve ser rejeitado."""


@dataclass(frozen=True)
class CvmDocument:
    cnpj: str
    reference_date: date
    version: int
    company_name: str
    cvm_code: str
    document_type: str
    document_id: str
    received_at: date | None
    url: str | None


@dataclass(frozen=True)
class CvmDfpArchive:
    payload: bytes

    def names(self) -> list[str]:
        with zipfile.ZipFile(io.BytesIO(self.payload)) as archive:
            return archive.namelist()

    def read_text(self, name: str, encoding: str = "iso-8859-1") -> str:
        with zipfile.ZipFile(io.BytesIO(self.payload)) as archive:
            return archive.read(name).decode(encoding)


def dfp_url(year: int) -> str:
    if not 1999 <= year <= 2100:
        raise ValueError("ano da DFP fora do intervalo suportado")
    return f"{DFP_BASE_URL}/dfp_cia_aberta_{year}.zip"


def download_dfp(year: int, *, timeout: int = 180) -> bytes:
    request = urllib.request.Request(
        dfp_url(year), headers={"User-Agent": "dash-invest/1.0 (+dados abertos CVM)"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def normalize_cnpj(value: str) -> str:
    digits = "".join(char for char in value if char.isdigit())
    if len(digits) != 14:
        raise CvmParseError(f"CNPJ inválido: {value!r}")
    return digits


def _normalize_token(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    return decomposed.encode("ascii", "ignore").decode("ascii").strip().upper()


def _reader(text: str) -> csv.DictReader:
    stream = io.StringIO(text.lstrip("\ufeff"))
    return csv.DictReader(stream, delimiter=";")


def _document_key(cnpj: str, reference_date: date, version: int) -> str:
    return f"{cnpj}|{reference_date.isoformat()}|{version}"


def parse_document_index(text: str | bytes) -> dict[str, CvmDocument]:
    if isinstance(text, bytes):
        text = text.decode("iso-8859-1")
    documents: dict[str, CvmDocument] = {}
    for row in _reader(text):
        if not (row.get("CNPJ_CIA") or "").strip():
            continue
        cnpj = normalize_cnpj(row["CNPJ_CIA"])
        reference_date = date.fromisoformat(row["DT_REFER"].strip())
        version = int(row["VERSAO"])
        received_at = date.fromisoformat(row["DT_RECEB"].strip()) if row.get("DT_RECEB") else None
        documents[_document_key(cnpj, reference_date, version)] = CvmDocument(
            cnpj=cnpj,
            reference_date=reference_date,
            version=version,
            company_name=(row.get("DENOM_CIA") or "").strip(),
            cvm_code=(row.get("CD_CVM") or "").strip(),
            document_type=(row.get("CATEG_DOC") or "").strip(),
            document_id=(row.get("ID_DOC") or "").strip(),
            received_at=received_at,
            url=(row.get("LINK_DOC") or "").strip() or None,
        )
    return documents


def _currency(value: str) -> str | None:
    normalized = _normalize_token(value)
    return CVM_CURRENCIES.get(normalized)


def _scale(value: str) -> Decimal:
    normalized = _normalize_token(value)
    if normalized == "MIL":
        return Decimal(1000)
    if normalized in {"", "UNIDADE"}:
        return Decimal(1)
    raise CvmParseError(f"ESCALA_MOEDA desconhecida: {value!r}")


def _decimal(value: str) -> Decimal:
    try:
        return Decimal(value.strip())
    except (InvalidOperation, AttributeError) as error:
        raise CvmParseError(f"VL_CONTA inválido: {value!r}") from error


def _scope_matches(group: str, consolidated: bool | None) -> bool:
    if consolidated is None:
        return True
    normalized = _normalize_token(group)
    if consolidated:
        return "CONSOLIDADO" in normalized
    return "INDIVIDUAL" in normalized


def parse_statement(
    text: str | bytes,
    *,
    statement: str,
    documents: Mapping[str, CvmDocument] | None = None,
    consolidated: bool | None = True,
    parser_version: str = PARSER_VERSION,
) -> list[Observation]:
    statement = statement.strip().upper()
    if statement not in DFP_STATEMENTS:
        raise ValueError(f"demonstração não suportada: {statement}")

    if isinstance(text, bytes):
        text = text.decode("iso-8859-1")

    observations: list[Observation] = []
    for row in _reader(text):
        if not (row.get("CNPJ_CIA") or "").strip():
            continue
        if _normalize_token(row.get("ORDEM_EXERC", "")) != "ULTIMO":
            continue
        if not _scope_matches(row.get("GRUPO_DFP", ""), consolidated):
            continue
        raw_value = (row.get("VL_CONTA") or "").strip()
        if not raw_value:
            continue

        cnpj = normalize_cnpj(row["CNPJ_CIA"])
        reference_date = date.fromisoformat(row["DT_REFER"].strip())
        version = int(row["VERSAO"])
        period_end = date.fromisoformat(
            (row.get("DT_FIM_EXERC") or row["DT_REFER"]).strip()
        )
        period_start = (
            date.fromisoformat(row["DT_INI_EXERC"].strip())
            if (row.get("DT_INI_EXERC") or "").strip()
            else None
        )
        account = (row.get("CD_CONTA") or "").strip()
        metric = CANONICAL_METRICS.get((statement, account), f"cvm_dfp.{statement.lower()}.{account}")

        document = (documents or {}).get(_document_key(cnpj, reference_date, version))
        published_at = (
            datetime.combine(document.received_at, time.min, tzinfo=timezone.utc)
            if document is not None and document.received_at is not None
            else None
        )

        observations.append(
            Observation(
                provider="cvm",
                metric=metric,
                instrument_id=f"cnpj:{cnpj}",
                value=_decimal(raw_value) * _scale(row.get("ESCALA_MOEDA", "")),
                currency=_currency(row.get("MOEDA", "")),
                unit=None,
                period_start=period_start,
                period_end=period_end,
                reference_date=reference_date,
                published_at=published_at,
                parser_version=parser_version,
                quality_status=QualityStatus.VERIFIED,
                source_document=document.url if document is not None else None,
                raw_payload=json.dumps(row, ensure_ascii=False, sort_keys=True),
            )
        )
    return observations


@dataclass(frozen=True)
class CvmDfpProvider:
    """Provedor de fundamentos da CVM; implementa `FundamentalsProvider`."""

    name: str = "cvm"
    parser_version: str = PARSER_VERSION
    timeout: int = 180
    consolidated: bool = True

    def statements(self, fiscal_year: int) -> list[Observation]:
        archive = CvmDfpArchive(download_dfp(fiscal_year, timeout=self.timeout))
        names = set(archive.names())

        index_name = f"dfp_cia_aberta_{fiscal_year}.csv"
        documents = (
            parse_document_index(archive.read_text(index_name)) if index_name in names else {}
        )

        suffix = "con" if self.consolidated else "ind"
        observations: list[Observation] = []
        for statement in DFP_STATEMENTS:
            member = f"dfp_cia_aberta_{statement}_{suffix}_{fiscal_year}.csv"
            if member not in names:
                continue
            observations.extend(
                parse_statement(
                    archive.read_text(member),
                    statement=statement,
                    documents=documents,
                    consolidated=self.consolidated,
                    parser_version=self.parser_version,
                )
            )
        return observations
