import pytest

from src.mortgage import amortize_extra, break_even_net_return, build_sac_schedule, compare_with_investment, savings


def test_sac_schedule_pays_balance_to_zero():
    schedule = build_sac_schedule(100_000, 120, .10, 0)
    assert len(schedule) == 120
    assert schedule.iloc[-1]["Saldo final"] == pytest.approx(0)


def test_extra_amortization_reduces_term_and_interest():
    base = build_sac_schedule(100_000, 120, .10)
    alternative = amortize_extra(100_000, 120, .10, 0, 20_000, "prazo")
    result = savings(base, alternative)
    assert result["months_saved"] > 0
    assert result["interest_saved"] > 0


def test_extra_amortization_reduces_installment_with_same_term():
    base = build_sac_schedule(100_000, 120, .10)
    alternative = amortize_extra(100_000, 120, .10, 0, 20_000, "parcela")
    assert len(alternative) == len(base)
    assert alternative.iloc[0]["Parcela"] < base.iloc[0]["Parcela"]


def test_comparison_returns_a_valid_winner():
    base = build_sac_schedule(100_000, 120, .10)
    alternative = amortize_extra(100_000, 120, .10, 0, 20_000, "prazo")
    assert compare_with_investment(base, alternative, 20_000, .10)["winner"] in {"Investir", "Amortizar"}


def test_break_even_rate_makes_scenarios_equal():
    base = build_sac_schedule(100_000, 120, .10)
    alternative = amortize_extra(100_000, 120, .10, 0, 20_000, "prazo")
    rate = break_even_net_return(base, alternative, 20_000)
    assert abs(compare_with_investment(base, alternative, 20_000, rate)["difference"]) < .01
