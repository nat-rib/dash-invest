from src.ui.dashboard import _quality_summary


def test_quality_summary_counts_available_financial_values():
    class FakeFrame:
        def __len__(self):
            return 3

        def __getitem__(self, key):
            import pandas as pd
            return {
                "Valor consolidado BRL": pd.Series([100.0, None, 50.0]),
                "Custo total": pd.Series([80.0, 40.0, None]),
                "Valor convertido BRL": pd.Series([None, 20.0, None]),
            }[key]

    assert _quality_summary(FakeFrame()) == {
        "total": 3,
        "value_known": 2,
        "cost_known": 2,
        "converted": 1,
    }


def test_quality_summary_handles_empty_positions():
    class EmptyFrame:
        def __len__(self):
            return 0

    assert _quality_summary(EmptyFrame()) == {
        "total": 0,
        "value_known": 0,
        "cost_known": 0,
        "converted": 0,
    }
