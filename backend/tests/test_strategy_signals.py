from pathlib import Path

import pandas as pd
import pytest

from app.strategy.config import StrategyConfig
from app.strategy.signals import market_regime_ok, near_52w_high, trend_ok


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


def test_trend_ok_synthetic():
    # Synthetic DataFrame testing strict stacking of 4 EMAs
    df = pd.DataFrame(
        {
            "date": [
                "2023-01-01",
                "2023-01-02",
                "2023-01-03",
                "2023-01-04",
                "2023-01-05",
                "2023-01-06",
            ],
            "ema_20": [200.0, 190.0, 200.0, 200.0, 200.0, 200.0],
            "ema_50": [150.0, 150.0, 150.0, 150.0, 150.0, 150.0],
            "ema_150": [100.0, 100.0, 120.0, 100.0, 100.0, 100.0],
            "ema_200": [50.0, 50.0, 120.0, 110.0, None, 50.0],
        }
    )
    # Day 1: 200 > 150 > 100 > 50 -> True (perfect stack)
    # Day 2: 190 > 150 > 100 > 50 -> True
    # Day 3: ema_150 == ema_200 (120 == 120) -> False (strict inequality)
    # Day 4: ema_150 (100) < ema_200 (110) -> False (inverted)
    # Day 5: ema_200 is NaN -> False
    # Day 6: 200 > 150 > 100 > 50 -> True
    df_copy = df.copy()

    trend = trend_ok(df)

    assert trend.iloc[0] is True or trend.iloc[0] == True  # noqa: E712
    assert trend.iloc[1] is True or trend.iloc[1] == True  # noqa: E712
    assert trend.iloc[2] is False or trend.iloc[2] == False  # noqa: E712
    assert trend.iloc[3] is False or trend.iloc[3] == False  # noqa: E712
    assert trend.iloc[4] is False or trend.iloc[4] == False  # noqa: E712
    assert trend.iloc[5] is True or trend.iloc[5] == True  # noqa: E712

    assert list(trend.index) == [
        "2023-01-01",
        "2023-01-02",
        "2023-01-03",
        "2023-01-04",
        "2023-01-05",
        "2023-01-06",
    ]
    assert trend.name == "trend_ok"

    # Verify input DataFrame is NOT mutated
    pd.testing.assert_frame_equal(df, df_copy)


def test_trend_ok_empty():
    df_empty = pd.DataFrame()
    trend = trend_ok(df_empty)
    assert trend.empty
    assert trend.dtype == bool


def test_trend_ok_on_fixture():
    fixture_path = Path("data/fixtures/MIDCAP_STOCK_101.parquet")
    if not fixture_path.exists():
        pytest.skip("MIDCAP_STOCK_101 fixture not found")

    df_stock = pd.read_parquet(fixture_path)
    trend = trend_ok(df_stock)

    assert len(trend) == len(df_stock)
    assert trend.dtype == bool
    # Initially before warm-up (200 bars), trend must be False
    assert trend.iloc[:199].sum() == 0
    # Later there should be sessions with confirmed uptrends
    assert trend.sum() > 0


def test_near_52w_high_synthetic():
    df = pd.DataFrame(
        {
            "date": [
                "2023-01-01",
                "2023-01-02",
                "2023-01-03",
                "2023-01-04",
                "2023-01-05",
            ],
            "adj_close": [90.0, 85.0, 84.9, 100.0, 95.0],
            "high_52w": [100.0, 100.0, 100.0, None, 100.0],
        }
    )
    # Day 1: 90.0 > 0.85 * 100.0 (85.0) -> True
    # Day 2: 85.0 > 85.0 -> False (strictly greater than)
    # Day 3: 84.9 > 85.0 -> False
    # Day 4: high_52w is NaN -> False
    # Day 5: 95.0 > 85.0 -> True
    df_copy = df.copy()

    near = near_52w_high(df, factor=0.85)

    assert near.iloc[0] is True or near.iloc[0] == True  # noqa: E712
    assert near.iloc[1] is False or near.iloc[1] == False  # noqa: E712
    assert near.iloc[2] is False or near.iloc[2] == False  # noqa: E712
    assert near.iloc[3] is False or near.iloc[3] == False  # noqa: E712
    assert near.iloc[4] is True or near.iloc[4] == True  # noqa: E712

    assert list(near.index) == [
        "2023-01-01",
        "2023-01-02",
        "2023-01-03",
        "2023-01-04",
        "2023-01-05",
    ]
    assert near.name == "near_52w_high"

    # Test with custom factor
    near_90 = near_52w_high(df, factor=0.90)
    # Day 1: 90.0 > 0.90 * 100.0 (90.0) -> False
    assert near_90.iloc[0] is False or near_90.iloc[0] == False  # noqa: E712
    # Day 5: 95.0 > 90.0 -> True
    assert near_90.iloc[4] is True or near_90.iloc[4] == True  # noqa: E712

    # Verify input DataFrame is NOT mutated
    pd.testing.assert_frame_equal(df, df_copy)


def test_near_52w_high_empty():
    df_empty = pd.DataFrame()
    near = near_52w_high(df_empty)
    assert near.empty
    assert near.dtype == bool


def test_near_52w_high_on_fixture():
    fixture_path = Path("data/fixtures/MIDCAP_STOCK_101.parquet")
    if not fixture_path.exists():
        pytest.skip("MIDCAP_STOCK_101 fixture not found")

    df_stock = pd.read_parquet(fixture_path)
    near = near_52w_high(df_stock)

    assert len(near) == len(df_stock)
    assert near.dtype == bool
    # Initially before warm-up (252 bars), near_52w_high must be False
    assert near.iloc[:251].sum() == 0
    # Later there should be sessions where stock is within 15% of 52W high
    assert near.sum() > 0
