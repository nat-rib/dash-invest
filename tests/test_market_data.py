from src.importer import validate_json
from src.market_data import MarketDataError, Quote, alpha_symbol, replace_prices, updatable_positions


def test_resolves_brazilian_symbol_and_updates_price():
    snapshot = validate_json('''{"schema_version":1,"snapshot_date":"2026-10-28","currency":"BRL","positions":[{"institution":"A","asset_class":"acao","ticker":"PETR4","name":"Petrobras","quantity":2,"current_price":10,"currency":"BRL"}]}''')
    assert alpha_symbol(snapshot.positions[0]) == "PETR4.SAO"
    updated = replace_prices(snapshot, {0: Quote("PETR4.SAO", 20.0)})
    assert updated.positions[0].current_price == 20
    assert updated.positions[0].current_value == 40


def test_market_symbol_overrides_default_and_non_quoted_assets_are_skipped():
    snapshot = validate_json('''{"schema_version":1,"snapshot_date":"2026-10-28","currency":"BRL","positions":[{"institution":"A","asset_class":"acao","ticker":"TEST","market_symbol":"CUSTOM","name":"Teste","current_value":10,"currency":"BRL"},{"institution":"B","asset_class":"renda_fixa","name":"CDB","current_value":10,"currency":"BRL"}]}''')
    assert alpha_symbol(snapshot.positions[0]) == "CUSTOM"
    assert updatable_positions(snapshot) == [(0, "CUSTOM")]


def test_resolves_crypto_symbol():
    snapshot = validate_json('''{"schema_version":1,"snapshot_date":"2026-10-28","currency":"BRL","positions":[{"institution":"Binance","asset_class":"cripto","ticker":"BTC","name":"Bitcoin","quantity":1,"current_price":1,"currency":"USD"}]}''')
    assert alpha_symbol(snapshot.positions[0]) == "BTC"


def test_daily_limit_message_is_translated():
    # A mensagem exibida pelo Alpha Vantage deve virar uma orientação acionável.
    error = MarketDataError("Limite diário da chave gratuita (25 consultas) atingido. Aguarde a renovação da cota ou use um plano compatível.")
    assert "25 consultas" in str(error)
