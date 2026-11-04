from datetime import datetime, timezone
from decimal import Decimal
import pytest

from src.domain.models import Portfolio
from src.persistence.database import SQLiteDatabase
from src.persistence.repositories import PortfolioRepository, TransactionRepository
from src.importers.transactions_csv import CanonicalTransactionCsvImporter, TransactionCsvImportError


HEADER = "external_id,occurred_at,transaction_type,institution,currency,amount,instrument_id,quantity,unit_price,fees,taxes,transfer_id,notes,metadata_json\n"


@pytest.fixture
def importer(tmp_path):
    db = SQLiteDatabase(tmp_path / "ledger.db")
    db.initialize()
    PortfolioRepository(db).save(Portfolio(id="main", name="Principal"))
    return CanonicalTransactionCsvImporter(TransactionRepository(db))


def test_imports_canonical_csv_and_is_idempotent(importer):
    csv_text = HEADER + "row-1,2026-11-04T10:00:00-03:00,DEPOSIT,Banco A,BRL,1000,,,,,,,aporte,{}\n"
    first = importer.import_text(csv_text, portfolio_id="main")
    second = importer.import_text(csv_text, portfolio_id="main")
    assert (first.parsed, first.inserted, first.skipped_duplicates) == (1, 1, 0)
    assert (second.parsed, second.inserted, second.skipped_duplicates) == (1, 0, 1)


def test_import_rejects_naive_timestamp_without_persisting(importer):
    csv_text = HEADER + "row-1,2026-11-04T10:00:00,DEPOSIT,Banco A,BRL,1000,,,,,,,aporte,{}\n"
    with pytest.raises(TransactionCsvImportError, match="timezone"):
        importer.import_text(csv_text, portfolio_id="main")


def test_import_validates_whole_file_before_writing(importer):
    csv_text = HEADER + (
        "row-1,2026-11-04T10:00:00Z,DEPOSIT,Banco A,BRL,1000,,,,,,,aporte,{}\n"
        "row-2,invalid,DEPOSIT,Banco A,BRL,200,,,,,,,aporte,{}\n"
    )
    with pytest.raises(TransactionCsvImportError):
        importer.import_text(csv_text, portfolio_id="main")
    assert importer.repository.list_for_portfolio("main") == []


def test_reusing_external_id_with_different_payload_fails(importer):
    first = HEADER + "row-1,2026-11-04T10:00:00Z,DEPOSIT,Banco A,BRL,1000,,,,,,,aporte,{}\n"
    changed = HEADER + "row-1,2026-11-04T10:00:00Z,DEPOSIT,Banco A,BRL,1200,,,,,,,aporte,{}\n"
    importer.import_text(first, portfolio_id="main")
    with pytest.raises(ValueError, match="conteúdo diferente"):
        importer.import_text(changed, portfolio_id="main")
    assert len(importer.repository.list_for_portfolio("main")) == 1
