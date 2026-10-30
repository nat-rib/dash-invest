from src.importer import validate_json
from src.portfolio import consolidated_total, duplicate_positions, positions_frame


def snapshot(raw): return validate_json(raw)


def test_market_value_and_gain():
    data = snapshot('''{"schema_version":1,"snapshot_date":"2026-10-28","currency":"BRL","positions":[{"institution":"A","asset_class":"acao","name":"X","quantity":10,"average_cost":5,"current_price":7,"currency":"BRL"}]}''')
    row = positions_frame(data).iloc[0]
    assert row["Valor atual"] == 70
    assert row["Ganho/perda"] == 20
    assert row["Rentabilidade"] == .4


def test_foreign_currency_is_not_consolidated():
    data = snapshot('''{"schema_version":1,"snapshot_date":"2026-10-28","currency":"BRL","positions":[{"institution":"A","asset_class":"exterior","name":"US","current_value":100,"currency":"USD"}]}''')
    assert consolidated_total(positions_frame(data)) == 0


def test_direct_value_and_unknown_cost():
    data = snapshot('''{"schema_version":1,"snapshot_date":"2026-10-28","currency":"BRL","positions":[{"institution":"A","asset_class":"renda_fixa","name":"CDB","current_value":100,"currency":"BRL"}]}''')
    row = positions_frame(data).iloc[0]
    assert row["Valor atual"] == 100
    assert row["Ganho/perda"] is None  # não calculável


def test_duplicate_positions_are_reported():
    data = snapshot('''{"schema_version":1,"snapshot_date":"2026-10-28","currency":"BRL","positions":[{"institution":"A","asset_class":"acao","name":"X","current_value":10,"currency":"BRL"},{"institution":"A","asset_class":"acao","name":"X","current_value":20,"currency":"BRL"}]}''')
    assert duplicate_positions(data) == [("A", "X", "BRL")]
