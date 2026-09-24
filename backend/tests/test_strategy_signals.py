from pathlib import Path

import pandas as pd
import pytest

from app.strategy.config import StrategyConfig
from app.strategy.signals import (
    entry_signal,
    exit_signal,
    generate_signals,
    market_regime_ok,
    near_52w_high,
    trend_ok,
)


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


def test_handcrafted_10_bar_signals():
    """Fixture-driven test: 10 bars where ground truth signals are known.

    Days:
    - Day 0: Close < EMA20 (90 < 100). No crossover. Exit = True. Entry = False.
    - Day 1: Close crosses above EMA20 (102 > 100.5, prev 90 < 100). All filters OK.
             Entry = True. Exit = False.
    - Day 2: Close stays above EMA20 (105 > 101, prev 102 > 100.5). No crossover.
             Entry = False. Exit = False.
    - Day 3: NIFTY regime turns False (Close < EMA50).
             Entry = False even if crossover occurs.
    - Day 4: Stock drops below EMA20 (95 < 101). Exit = True. Entry = False.
    - Day 5: Trend broken (EMA20 < EMA50). Entry = False.
    - Day 6: Far from 52W high (Close 70 < 0.85 * 100 = 85). Entry = False.
    - Day 7: Close stays below EMA20 (65 < 75). Exit = True.
    - Day 8: Close stays below EMA20. Exit = True.
    - Day 9: All filters OK, crossover above EMA20 (was 65, now 105 > 100).
             Entry = True. Exit = False.
    """

    dates = [f"2023-01-{i:02d}" for i in range(1, 11)]

    # Stock dataframe (10 bars)
    stock_df = pd.DataFrame(
        {
            "date": dates,
            "open": [90.0, 92.0, 102.0, 103.0, 98.0, 94.0, 72.0, 68.0, 64.0, 85.0],
            "high": [95.0, 103.0, 106.0, 104.0, 99.0, 95.0, 74.0, 70.0, 66.0, 106.0],
            "low": [88.0, 91.0, 101.0, 97.0, 93.0, 70.0, 69.0, 63.0, 62.0, 84.0],
            "close": [90.0, 102.0, 105.0, 103.0, 95.0, 92.0, 70.0, 65.0, 64.0, 105.0],
            "adj_close": [
                90.0,
                102.0,
                105.0,
                103.0,
                95.0,
                92.0,
                70.0,
                65.0,
                64.0,
                105.0,
            ],
            "volume": [1000.0] * 10,
            "ema_20": [
                100.0,
                100.5,
                101.0,
                101.0,
                101.0,
                95.0,
                80.0,
                75.0,
                70.0,
                100.0,
            ],
            "ema_50": [80.0, 80.0, 80.0, 80.0, 80.0, 96.0, 75.0, 70.0, 65.0, 90.0],
            "ema_150": [70.0, 70.0, 70.0, 70.0, 70.0, 70.0, 70.0, 65.0, 60.0, 80.0],
            "ema_200": [60.0, 60.0, 60.0, 60.0, 60.0, 60.0, 60.0, 60.0, 55.0, 70.0],
            "high_52w": [100.0] * 10,
        }
    )

    # NIFTY benchmark dataframe (10 bars)
    # Day 3 (2023-01-04) has close 16500 < ema_50 17000 (Regime=False)
    nifty_df = pd.DataFrame(
        {
            "date": dates,
            "close": [
                18000.0,
                18100.0,
                18200.0,
                16500.0,
                18000.0,
                18000.0,
                18000.0,
                18000.0,
                18000.0,
                18500.0,
            ],
            "ema_50": [17000.0] * 10,
            "ema_200": [16000.0] * 10,
        }
    )

    stock_copy = stock_df.copy()
    nifty_copy = nifty_df.copy()

    entries = entry_signal(stock_df, nifty_df)
    exits = exit_signal(stock_df)

    # Assert exact entry days: Day 1 and Day 9
    expected_entries = [
        False,
        True,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        True,
    ]
    assert list(entries.values) == expected_entries

    # Assert exact exit days: Day 0, Day 4, Day 5, Day 6, Day 7, Day 8
    expected_exits = [True, False, False, False, True, True, True, True, True, False]
    assert list(exits.values) == expected_exits

    # Verify generate_signals produces identical results and adds columns
    gen_df = generate_signals(stock_df, nifty_df)
    assert list(gen_df["entry"].values) == expected_entries
    assert list(gen_df["exit"].values) == expected_exits
    assert "regime_ok" in gen_df.columns
    assert "trend_ok" in gen_df.columns
    assert "near_52w_high" in gen_df.columns
    assert "crossover" in gen_df.columns

    # Verify input DataFrames are NOT mutated
    pd.testing.assert_frame_equal(stock_df, stock_copy)
    pd.testing.assert_frame_equal(nifty_df, nifty_copy)


def test_regime_filter_override_blocks_all_entries():
    """Assert when NIFTY is below EMAs, entry_signal is always False."""

    df_stock = pd.read_parquet("data/fixtures/MIDCAP_STOCK_101.parquet")
    df_nifty = pd.read_parquet("data/fixtures/NIFTY50.parquet").copy()

    # Artificially force NIFTY into persistent bear regime (Close < EMA 50 & 200)
    df_nifty["close"] = 1000.0  # Far below EMA 50 and 200

    entries = entry_signal(df_stock, df_nifty)
    assert len(entries) == len(df_stock)
    # Must be strictly 0 entries under bear regime
    assert entries.sum() == 0


def test_no_lookahead_truncation_guard():
    """No-look-ahead guard: Signal on day T must be computable using only rows <= T.

    Test: Truncate dataframe at T, recompute, assert signal at T is 100% identical.
    """
    df_stock = pd.read_parquet("data/fixtures/MIDCAP_STOCK_101.parquet")
    df_nifty = pd.read_parquet("data/fixtures/NIFTY50.parquet")

    # Run full calculation
    full_signals = generate_signals(df_stock, df_nifty)

    # Test multiple evaluation points across time
    eval_indices = [350, 500, 750, 1000]
    for idx in eval_indices:
        target_date = full_signals["date"].iloc[idx]

        # Truncate stock and nifty dataframes strictly up to bar idx
        stock_trunc = df_stock.iloc[: idx + 1].copy()
        nifty_trunc = df_nifty.iloc[: idx + 1].copy()

        # Recompute signals on truncated slice
        trunc_signals = generate_signals(stock_trunc, nifty_trunc)

        # Assert values on date T are strictly identical
        full_row = full_signals.iloc[idx]
        trunc_row = trunc_signals.iloc[-1]

        assert full_row["date"] == trunc_row["date"] == target_date
        assert full_row["regime_ok"] == trunc_row["regime_ok"]
        assert full_row["trend_ok"] == trunc_row["trend_ok"]
        assert full_row["near_52w_high"] == trunc_row["near_52w_high"]
        assert full_row["crossover"] == trunc_row["crossover"]
        assert full_row["entry"] == trunc_row["entry"]
        assert full_row["exit"] == trunc_row["exit"]
