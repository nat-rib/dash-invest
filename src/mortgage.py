"""Projeções SAC + TR e comparação de amortização com investimento.

Lógica adaptada do motor SAC do repositório local finCalc. As projeções partem
do saldo devedor atual informado e não substituem a planilha contratual da CAIXA.
"""
from __future__ import annotations

import math
import pandas as pd


def monthly_rate(annual_rate: float) -> float:
    """Convenção de taxa nominal brasileira: taxa anual dividida por 12."""
    return annual_rate / 12


def build_sac_schedule(
    balance: float,
    months: int,
    annual_interest: float,
    annual_tr: float = 0.0,
    monthly_fees: float = 0.0,
) -> pd.DataFrame:
    """Projeta as parcelas restantes de um contrato SAC corrigido por TR."""
    interest_monthly = monthly_rate(annual_interest)
    tr_monthly = monthly_rate(annual_tr)
    rows, outstanding = [], balance
    for month in range(1, months + 1):
        corrected = outstanding * (1 + tr_monthly)
        amortization = corrected / (months - month + 1)
        interest = corrected * interest_monthly
        installment = amortization + interest + monthly_fees
        final_balance = max(corrected - amortization, 0.0)
        rows.append({
            "Mês": month, "Saldo inicial": outstanding, "Saldo corrigido": corrected,
            "Amortização": amortization, "Juros": interest, "Encargos": monthly_fees,
            "Parcela": installment, "Saldo final": final_balance,
        })
        outstanding = final_balance
    return pd.DataFrame(rows)


def amortize_extra(
    balance: float,
    months: int,
    annual_interest: float,
    annual_tr: float,
    extra: float,
    mode: str,
    monthly_fees: float = 0.0,
) -> pd.DataFrame:
    """Aplica amortização extra reduzindo prazo ou valor de parcela."""
    if not 0 < extra < balance:
        raise ValueError("A amortização extra deve ser maior que zero e menor que o saldo devedor.")
    remaining_balance = balance - extra
    if mode == "parcela":
        return build_sac_schedule(remaining_balance, months, annual_interest, annual_tr, monthly_fees)
    if mode != "prazo":
        raise ValueError("Modo deve ser 'prazo' ou 'parcela'.")

    interest_monthly, tr_monthly = monthly_rate(annual_interest), monthly_rate(annual_tr)
    corrected_base = balance * (1 + tr_monthly)
    target_installment = corrected_base / months + corrected_base * interest_monthly + monthly_fees
    corrected_new = remaining_balance * (1 + tr_monthly)
    denominator = target_installment - corrected_new * interest_monthly - monthly_fees
    if denominator <= 0:
        raise ValueError("Não foi possível calcular o novo prazo para estes parâmetros.")
    new_months = math.ceil(corrected_new / denominator)
    return build_sac_schedule(remaining_balance, new_months, annual_interest, annual_tr, monthly_fees)


def savings(base: pd.DataFrame, alternative: pd.DataFrame) -> dict[str, float]:
    return {
        "months_saved": float(len(base) - len(alternative)),
        "interest_saved": float(base["Juros"].sum() - alternative["Juros"].sum()),
        "payment_saved": float(base["Parcela"].sum() - alternative["Parcela"].sum()),
    }


def compare_with_investment(
    base: pd.DataFrame,
    alternative: pd.DataFrame,
    extra: float,
    net_annual_return: float,
) -> dict[str, float | str]:
    """Compara patrimônios no fim do prazo original.

    Estratégia investimento: o valor extra é aplicado hoje. Estratégia amortização:
    cada redução de parcela é aplicada ao mesmo retorno líquido mensal. Não inclui
    impostos futuros, TR realizada, custos de transação ou risco de crédito.
    """
    months = len(base)
    investment_monthly = (1 + net_annual_return) ** (1 / 12) - 1
    invest_value = extra * (1 + investment_monthly) ** months
    savings_cashflows = []
    for month in range(months):
        alternative_payment = float(alternative.iloc[month]["Parcela"]) if month < len(alternative) else 0.0
        savings_cashflows.append(float(base.iloc[month]["Parcela"]) - alternative_payment)
    amort_value = sum(
        cashflow * (1 + investment_monthly) ** (months - index - 1)
        for index, cashflow in enumerate(savings_cashflows)
    )
    difference = invest_value - amort_value
    return {
        "invest_value": invest_value,
        "amortization_value": amort_value,
        "difference": difference,
        "winner": "Investir" if difference > 0 else "Amortizar",
    }


def break_even_net_return(base: pd.DataFrame, alternative: pd.DataFrame, extra: float) -> float:
    """Taxa anual efetiva líquida que deixa os dois cenários empatados."""
    low, high = 0.0, 1.0
    # Expand the upper bound if an unusually expensive loan requires it.
    while float(compare_with_investment(base, alternative, extra, high)["difference"]) < 0:
        high *= 2
        if high > 10:
            raise ValueError("Não foi possível encontrar uma taxa de equilíbrio realista.")
    for _ in range(80):
        middle = (low + high) / 2
        if float(compare_with_investment(base, alternative, extra, middle)["difference"]) < 0:
            low = middle
        else:
            high = middle
    return (low + high) / 2
