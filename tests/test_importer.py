import pytest
from pydantic import ValidationError
from src.importer import replace_snapshot, validate_json


VALID = '''{"schema_version":1,"snapshot_date":"2026-10-28","currency":"BRL","positions":[{"institution":"Teste","asset_class":"acao","name":"Ativo","quantity":2,"average_cost":10,"current_price":12,"currency":"BRL"}]}'''


def test_valid_json():
    assert validate_json(VALID).positions[0].name == "Ativo"


@pytest.mark.parametrize("raw", ["", "{bad json}"])
def test_empty_or_invalid_json(raw):
    with pytest.raises(ValueError): validate_json(raw)


def test_missing_required_field():
    with pytest.raises(ValidationError): validate_json('{"schema_version":1,"snapshot_date":"2026-10-28","currency":"BRL","positions":[]}')


def test_negative_quantity_rejected():
    with pytest.raises(ValidationError):
        validate_json(VALID.replace('"quantity":2', '"quantity":-2'))


def test_unknown_value_rejected():
    with pytest.raises(ValidationError):
        validate_json('''{"schema_version":1,"snapshot_date":"2026-10-28","currency":"BRL","positions":[{"institution":"Teste","asset_class":"acao","name":"Ativo","quantity":2,"currency":"BRL"}]}''')


def test_invalid_import_does_not_replace_current_snapshot(tmp_path):
    path = tmp_path / "portfolio.json"
    path.write_text(VALID)
    with pytest.raises(ValueError):
        replace_snapshot(path, b"invalid")
    assert path.read_text() == VALID


def test_valid_import_replaces_snapshot(tmp_path):
    path = tmp_path / "portfolio.json"
    replace_snapshot(path, VALID.encode())
    assert validate_json(path.read_text()).positions[0].quantity == 2
