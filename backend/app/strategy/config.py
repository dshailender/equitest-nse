from dataclasses import dataclass, field


@dataclass
class StrategyConfig:
    """Strategy configuration parameters and threshold rules.

    Default values strictly follow the PRD specifications:
    - Short EMA: 20
    - Long EMA: 200
    - Stock Trend EMAs: [20, 50, 150, 200]
    - NIFTY Regime EMAs: [50, 200]
    - 52-Week High Proximity Factor: 0.85 (Close > 0.85 * 52W High)
    - 52-Week High Lookback: 252 trading sessions
    - Hard Stop Loss: 7% from entry price
    - Maximum Risk per Trade: 2% of current portfolio corpus
    """

    ema_short: int = 20
    ema_long: int = 200
    ema_trend_spans: list[int] = field(default_factory=lambda: [20, 50, 150, 200])
    regime_ema_spans: list[int] = field(default_factory=lambda: [50, 200])
    high_52w_factor: float = 0.85
    high_52w_lookback: int = 252
    stop_loss_pct: float = 0.07
    risk_pct: float = 0.02
    corpus: float = 500000.0
    lot_size: int = 1
    cost_bps: float = 10.0
    allow_crossover_equal: bool = False

    def to_dict(self) -> dict:
        """Serializes configuration to dictionary."""
        return {
            "ema_short": self.ema_short,
            "ema_long": self.ema_long,
            "ema_trend_spans": list(self.ema_trend_spans),
            "regime_ema_spans": list(self.regime_ema_spans),
            "high_52w_factor": self.high_52w_factor,
            "high_52w_lookback": self.high_52w_lookback,
            "stop_loss_pct": self.stop_loss_pct,
            "risk_pct": self.risk_pct,
            "corpus": self.corpus,
            "lot_size": self.lot_size,
            "cost_bps": self.cost_bps,
            "allow_crossover_equal": self.allow_crossover_equal,
        }

    @property
    def regime_spans(self) -> list[int]:
        """Alias for regime_ema_spans."""
        return self.regime_ema_spans

    @property
    def ema_spans(self) -> list[int]:
        """Alias for ema_trend_spans."""
        return self.ema_trend_spans
