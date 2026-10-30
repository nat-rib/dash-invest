from decimal import Decimal
import math


def number(value: object, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "Não disponível"
    text = f"{float(value):,.{digits}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def money(value: object, currency: str = "BRL") -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "Não disponível"
    symbol = "R$" if currency == "BRL" else currency
    return f"{symbol} {number(value)}"


def percent(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "Não disponível"
    return f"{number(float(value) * 100)}%"
