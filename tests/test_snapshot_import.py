from datetime import date
from decimal import Decimal

from src.domain.models import Transaction
from src.persistence.database import SQLiteDatabase
from src.persistence.repositories import (
    InstrumentRepository, PortfolioPositionRepository, PortfolioRepository,
    TransactionRepository,
)
from src.persistence.snapshot_import import PortfolioSnapshotImporter
from src.schemas import PortfolioSnapshot, Position


def _snapshot():
    return PortfolioSnapshot(
        schema_version=1,
        snapshot_date=date(2026, 11, 4),
        currency="BRL",
        positions=[
            Position(
                institution="Corretora A", asset_class="acao", ticker="PETR4",
                name="Petrobras PN", quantity=Decimal("10"), average_cost=Decimal("30"),
                current_price=Decimal("35"), currency="BRL",
            ),
            Position(
                institution="Corretora B", asset_class="acao", ticker="PETR4",
                name="Petrobras PN", quantity=Decimal("5"), average_cost=Decimal("32"),
                current_price=Decimal("35"), currency="BRL",
            ),
            Position(
                institution="Banco C", asset_class="renda_fixa", name="CDB Banco C",
                current_value=Decimal("1200"), currency="BRL", issuer="Banco C",
            ),
        ],
    )


def test_snapshot_import_is_repeatable_and_does_not_fabricate_transactions(tmp_path):
    database = SQLiteDatabase(tmp_path / "snapshot.db")
    database.initialize()
    importer = PortfolioSnapshotImporter(database)
    first = importer.import_snapshot(_snapshot())
    second = importer.import_snapshot(_snapshot())

    assert first.instruments_saved == 2
    assert first.positions_saved == 3
    assert second == first
    assert len(PortfolioRepository(database).list_all()) == 1
    assert len(InstrumentRepository(database).list_all()) == 2
    positions = PortfolioPositionRepository(database).list_snapshots("legacy-import", date(2026, 11, 4))
    assert len(positions) == 3
    assert any(position.quantity is None for position in positions)
    assert all(position.metadata["source"] == "portfolio_snapshot_json" for position in positions)
    assert TransactionRepository(database).list_for_portfolio("legacy-import") == []
    assert first.transactions_created == 0


def test_same_instrument_across_institutions_has_one_catalog_entry(tmp_path):
    database = SQLiteDatabase(tmp_path / "snapshot.db")
    database.initialize()
    PortfolioSnapshotImporter(database).import_snapshot(_snapshot())
    instruments = InstrumentRepository(database).list_all()
    petr = next(instrument for instrument in instruments if instrument.name == "Petrobras PN")
    positions = PortfolioPositionRepository(database).list_snapshots("legacy-import", date(2026, 11, 4))
    petr_positions = [position for position in positions if position.instrument_id == petr.id]
    assert len(petr_positions) == 2
    assert {position.institution for position in petr_positions} == {"Corretora A", "Corretora B"}


def test_snapshot_import_rejects_duplicate_instrument_rows(tmp_path):
    import pytest

    database = SQLiteDatabase(tmp_path / "atomic.db")
    database.initialize()
    snapshot = _snapshot()
    duplicate = snapshot.positions[0].model_copy()
    snapshot = snapshot.model_copy(update={"positions": [snapshot.positions[0], duplicate]})

    with pytest.raises(ValueError, match="mesmo instrumento"):
        PortfolioSnapshotImporter(database).import_snapshot(snapshot)

    assert PortfolioRepository(database).list_all() == []
    assert InstrumentRepository(database).list_all() == []
    assert PortfolioPositionRepository(database).list_snapshots("legacy-import") == []


def test_snapshot_import_rolls_back_if_a_position_write_fails(tmp_path, monkeypatch):
    import pytest

    database = SQLiteDatabase(tmp_path / "rollback.db")
    database.initialize()
    original = PortfolioPositionRepository.save_snapshot

    def fail_on_bank_position(self, position, connection=None):
        if position.institution == "Banco C":
            raise RuntimeError("simulated persistence failure")
        return original(self, position, connection=connection)

    monkeypatch.setattr(PortfolioPositionRepository, "save_snapshot", fail_on_bank_position)
    with pytest.raises(RuntimeError, match="simulated persistence failure"):
        PortfolioSnapshotImporter(database).import_snapshot(_snapshot())

    assert PortfolioRepository(database).list_all() == []
    assert InstrumentRepository(database).list_all() == []
    assert PortfolioPositionRepository(database).list_snapshots("legacy-import") == []
