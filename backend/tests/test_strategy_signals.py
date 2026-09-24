from pathlib import Path

import pandas as pd
import pytest

from app.strategy.config import StrategyConfig
from app.strategy.signals import market_regime_ok


def test_strategy_config_defaults():
    cfg = StrategyConfig()
    assert cfg.ema_short == 20
    assert cfg.ema_long == 200
    assert cfg.ema_trend_spans == [20, 50, 150, 200]
    assert cfg.regime_ema_spans == [50, 200]
    assert cfg.high_52w_factor == 0.85
    assert cfg.high_52w_lookback == 252
    assert cfg.stop_loss_pct == 0.07
    assert cfg.risk_pct == 0.02
    assert cfg.allow_crossover_equal is False
    assert cfg.regime_spans == [50, 200]
    assert cfg.ema_spans == [20, 50, 150, 200]


def test_market_regime_ok_synthetic():
    # Synthetic test DataFrame with precomputed EMAs
    df = pd.DataFrame(
        {
            "date": [
                "2023-01-01",
                "2023-01-02",
                "2023-01-03",
                "2023-01-04",
                "2023-01-05",
            ],
            "close": [100.0, 105.0, 95.0, 100.0, 110.0],
            "ema_50": [95.0, 98.0, 98.0, 102.0, None],  # day 5 has NaN
            "ema_200": [90.0, 106.0, 92.0, 99.0, 90.0],  # day 2 has close < ema_200
        }
    )
    df_copy = df.copy()

    regime = market_regime_ok(df)

    # Day 1: close 100 > 95 and 100 > 90 -> True
    assert regime.iloc[0] is True or regime.iloc[0] == True  # noqa: E712
    # Day 2: close 105 > 98 but 105 <= 106 -> False
    assert regime.iloc[1] is False or regime.iloc[1] == False  # noqa: E712
    # Day 3: close 95 <= 98 -> False
    assert regime.iloc[2] is False or regime.iloc[2] == False  # noqa: E712
    # Day 4: close 100 <= 102 -> False
    assert regime.iloc[3] is False or regime.iloc[3] == False  # noqa: E712
    # Day 5: ema_50 is NaN -> False
    assert regime.iloc[4] is False or regime.iloc[4] == False  # noqa: E712

    # Check index is date strings
    assert list(regime.index) == [
        "2023-01-01",
        "2023-01-02",
        "2023-01-03",
        "2023-01-04",
        "2023-01-05",
    ]
    assert regime.name == "regime_ok"

    # Verify input DataFrame is NOT mutated
    pd.testing.assert_frame_equal(df, df_copy)


def test_market_regime_ok_empty():
    df_empty = pd.DataFrame()
    regime = market_regime_ok(df_empty)
    assert regime.empty
    assert regime.dtype == bool


def test_market_regime_ok_on_fixture():
    fixture_path = Path("data/fixtures/NIFTY50.parquet")
    if not fixture_path.exists():
        pytest.skip("NIFTY50 fixture not found")

    df_nifty = pd.read_parquet(fixture_path)
    regime = market_regime_ok(df_nifty)

    assert len(regime) == len(df_nifty)
    assert regime.dtype == bool
    # Initially before warm-up (200 bars), regime must be False
    assert regime.iloc[:199].sum() == 0
    # Later in trending bull markets, regime must have True periods
    assert regime.sum() > 0
