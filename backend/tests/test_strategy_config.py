"""Tests for StrategyConfig Pydantic model, Rankers, and Universe bounds (REQ-6.1)."""

import json

import pandas as pd

from app.data.universe import get_default_fallback_constituents, get_universe
from app.engine.backtest import (
    AlphabeticalRanker,
    DefaultRanker,
    Proximity52WRanker,
    get_ranker,
)
from app.strategy.config import StrategyConfig


def test_strategy_config_defaults():
    """Validates StrategyConfig initializes with locked PRD defaults."""
    cfg = StrategyConfig()
    assert cfg.universe_start_rank == 101
    assert cfg.universe_end_rank == 750
    assert cfg.ema_spans == [20, 50, 150, 200]
    assert cfg.regime_ema_spans == [50, 200]
    assert cfg.high_52w_factor == 0.85
    assert cfg.high_52w_lookback == 252
    assert cfg.sl_pct == 0.07
    assert cfg.risk_pct == 0.02
    assert cfg.capital == 500000.0
    assert cfg.ranking_rule == "momentum"
    assert cfg.lot_size == 1
    assert cfg.cost_bps == 10.0
    assert cfg.allow_crossover_equal is False


def test_strategy_config_backward_compatibility_aliases():
    """Validates legacy constructor arguments and property accessors."""
    cfg = StrategyConfig(
        corpus=1000000.0,
        stop_loss_pct=0.05,
        ema_trend_spans=[10, 30, 100, 200],
        regime_spans=[20, 100],
    )
    # Check underlying fields
    assert cfg.capital == 1000000.0
    assert cfg.sl_pct == 0.05
    assert cfg.ema_spans == [10, 30, 100, 200]
    assert cfg.regime_ema_spans == [20, 100]

    # Check property accessors
    assert cfg.corpus == 1000000.0
    assert cfg.stop_loss_pct == 0.05
    assert cfg.ema_trend_spans == [10, 30, 100, 200]
    assert cfg.regime_spans == [20, 100]

    # Check setters
    cfg.corpus = 750000.0
    assert cfg.capital == 750000.0
    cfg.stop_loss_pct = 0.08
    assert cfg.sl_pct == 0.08
    cfg.ema_trend_spans = [20, 50]
    assert cfg.ema_spans == [20, 50]
    cfg.regime_spans = [50]
    assert cfg.regime_ema_spans == [50]


def test_strategy_config_serialization():
    """Validates serialization to dict and JSON."""
    cfg = StrategyConfig(capital=250000.0, sl_pct=0.06, ranking_rule="alphabetical")
    d = cfg.to_dict()
    assert d["capital"] == 250000.0
    assert d["corpus"] == 250000.0
    assert d["sl_pct"] == 0.06
    assert d["stop_loss_pct"] == 0.06
    assert d["ranking_rule"] == "alphabetical"

    # Pydantic v2 model_dump and JSON roundtrip
    dumped = cfg.model_dump()
    assert dumped["capital"] == 250000.0
    json_str = cfg.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["capital"] == 250000.0
    assert parsed["sl_pct"] == 0.06

    reconstituted = StrategyConfig.model_validate_json(json_str)
    assert reconstituted.capital == 250000.0
    assert reconstituted.sl_pct == 0.06
    assert reconstituted.ranking_rule == "alphabetical"


def test_ranker_factory_resolution():
    """Validates get_ranker returns correct ranker instance based on rule."""
    assert isinstance(get_ranker("momentum"), DefaultRanker)
    assert isinstance(get_ranker("MOMENTUM"), DefaultRanker)
    assert isinstance(get_ranker(None), DefaultRanker)
    assert isinstance(get_ranker("alphabetical"), AlphabeticalRanker)
    assert isinstance(get_ranker("alpha"), AlphabeticalRanker)
    assert isinstance(get_ranker("52w_proximity"), Proximity52WRanker)
    assert isinstance(get_ranker("high_52w"), Proximity52WRanker)
    assert isinstance(get_ranker("unknown_rule"), DefaultRanker)


def test_alphabetical_ranker():
    """Validates AlphabeticalRanker sorts symbols alphabetically."""
    ranker = AlphabeticalRanker()
    ranked = ranker.rank(["GAMMA", "ALPHA", "BETA"], "2021-05-25", {})
    assert ranked == ["ALPHA", "BETA", "GAMMA"]


def test_proximity_52w_ranker():
    """Validates Proximity52WRanker sorts by Close/52W High ratio descending."""
    ranker = Proximity52WRanker()
    date = "2021-05-25"
    # Stock A: Close 95, 52W High 100 -> ratio 0.95
    # Stock B: Close 90, 52W High 100 -> ratio 0.90
    # Stock C: Close 99, 52W High 100 -> ratio 0.99
    signals = {
        "STOCK_A": pd.DataFrame([{"date": date, "close": 95.0, "high_52w": 100.0}]),
        "STOCK_B": pd.DataFrame([{"date": date, "close": 90.0, "high_52w": 100.0}]),
        "STOCK_C": pd.DataFrame([{"date": date, "close": 99.0, "high_52w": 100.0}]),
    }
    ranked = ranker.rank(["STOCK_A", "STOCK_B", "STOCK_C"], date, signals)
    assert ranked == ["STOCK_C", "STOCK_A", "STOCK_B"]


def test_universe_rank_bounds():
    """Validates universe rank filtering with custom start_rank and end_rank."""
    fallback = get_default_fallback_constituents(start_rank=101, end_rank=150)
    assert len(fallback) == 50
    assert fallback[0]["rank"] == 101
    assert fallback[-1]["rank"] == 150

    tickers, biased, details = get_universe("2022-01-01", start_rank=101, end_rank=110)
    assert len(tickers) == 10
    assert details[0]["rank"] == 101
    assert details[-1]["rank"] == 110
