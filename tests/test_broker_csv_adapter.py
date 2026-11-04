from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.domain.models import AssetClass, Instrument, Portfolio
from src.importers.broker_csv import BrokerCsvMapping, adapt_broker_csv
from src.importers.transactions_csv import CanonicalTransactionCsvImporter, TransactionCsvImportError
from src.persistence.database import SQLiteDatabase
from src.persistence.repositories import InstrumentRepository, PortfolioRepository, TransactionRepository


@pytest.fixture
def setup_importer(tmp_path):
    db = SQLiteDatabase(tmp_path / "broker.db")
    db.initialize()
    PortfolioRepository(db).save(Portfolio(id="main", name="Principal"))
    InstrumentRepository(db).save(Instrument(
        id="instrument-petr4", name="Petrobras PN", asset_class=AssetClass.EQUITY, currency="BRL",
    ))
    repository = TransactionRepository(db)
    return CanonicalTransactionCsvImporter(repository), repository


def test_adapts_portuguese_broker_csv_and_is_idempotent(setup_importer):
    importer, repository = setup_importer
    content = (
        "ID;Data;Operação;Ativo;Qtd;Preço;Valor;Moeda\n"
        "op-1;04/11/2026;Compra;PETR4;10;32,50;325,00;BRL\n"
    )
    mapping = BrokerCsvMapping(
        institution="Corretora A", currency="BRL", delimiter=";",
        columns={
            "external_id": "ID", "occurred_at": "Data", "transaction_type": "Operação",
            "instrument_id": "Ativo", "quantity": "Qtd", "unit_price": "Preço",
            "amount": "Valor", "currency": "Moeda",
        },
        instrument_map={"PETR4": "instrument-petr4"},
    )
    first = adapt_broker_csv(content, portfolio_id="main", mapping=mapping, importer=importer)
    second = adapt_broker_csv(content, portfolio_id="main", mapping=mapping, importer=importer)
    tx = repository.list_for_portfolio("main")[0]
    assert (first.inserted, second.skipped_duplicates) == (1, 1)
    assert tx.instrument_id == "instrument-petr4"
    assert tx.quantity == Decimal("10")
    assert tx.unit_price == Decimal("32.50")
    assert tx.occurred_at == datetime(2026, 11, 4, 3, tzinfo=timezone.utc)


def test_rejects_unmapped_asset_for_trade(setup_importer):
    importer, repository = setup_importer
    content = "ID,Data,Operação,Ativo,Qtd,Preço\nop-1,2026-11-04,Compra,PETR4,1,10\n"
    mapping = BrokerCsvMapping(
        institution="Broker", currency="BRL",
        columns={"external_id": "ID", "occurred_at": "Data", "transaction_type": "Operação",
                 "instrument_id": "Ativo", "quantity": "Qtd", "unit_price": "Preço"},
    )
    with pytest.raises(TransactionCsvImportError, match="associe o ativo"):
        adapt_broker_csv(content, portfolio_id="main", mapping=mapping, importer=importer)
    assert repository.list_for_portfolio("main") == []


def test_generates_stable_fingerprint_when_external_id_is_missing(setup_importer):
    importer, repository = setup_importer
    content = "Data,Operação,Valor\n04/11/2026,Aporte,1000,00\n"
    # Correctly quoted decimal comma is required in a comma-delimited CSV.
    content = 'Data,Operação,Valor\n04/11/2026,Aporte,"1.000,00"\n'
    mapping = BrokerCsvMapping(
        institution="Broker", currency="BRL",
        columns={"occurred_at": "Data", "transaction_type": "Operação", "amount": "Valor"},
    )
    first = adapt_broker_csv(content, portfolio_id="main", mapping=mapping, importer=importer)
    second = adapt_broker_csv(content, portfolio_id="main", mapping=mapping, importer=importer)
    assert first.inserted == 1 and second.skipped_duplicates == 1
    assert repository.list_for_portfolio("main")[0].amount == Decimal("1000.00")
