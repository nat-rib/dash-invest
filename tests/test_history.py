from src.history import portfolio_history, position_history, record_snapshot
from src.importer import validate_json


def test_records_portfolio_and_positions_locally(tmp_path):
    snapshot = validate_json('''{"schema_version":1,"snapshot_date":"2026-10-28","currency":"BRL","positions":[{"institution":"Teste","asset_class":"acao","ticker":"TEST3","name":"Teste","quantity":2,"current_price":10,"currency":"BRL"}]}''')
    database = tmp_path / "history.db"
    record_snapshot(snapshot, "test", database)
    assert portfolio_history(database).iloc[0]["Patrimônio BRL"] == 20
    assert position_history(database).iloc[0]["Ativo"] == "Teste"
