from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrategyConfig(BaseModel):
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
    - Universe Ranks: 101 to 750
    - Ranking Rule: "momentum"
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    universe_start_rank: int = Field(
        default=101, ge=1, description="Starting universe rank (inclusive)"
    )
    universe_end_rank: int = Field(
        default=750, ge=1, description="Ending universe rank (inclusive)"
    )
    ema_spans: list[int] = Field(
        default_factory=lambda: [20, 50, 150, 200],
        description="Stock trend EMA spans",
    )
    regime_ema_spans: list[int] = Field(
        default_factory=lambda: [50, 200],
        description="NIFTY regime EMA spans",
    )
    high_52w_factor: float = Field(
        default=0.85, gt=0, description="52-Week High proximity threshold"
    )
    high_52w_lookback: int = Field(
        default=252, gt=0, description="52-Week High lookback sessions"
    )
    sl_pct: float = Field(
        default=0.07, gt=0, lt=1, description="Stop loss percentage distance"
    )
    risk_pct: float = Field(
        default=0.02, gt=0, lt=1, description="Maximum risk per trade fraction"
    )
    cost_bps: float = Field(
        default=10.0,
        ge=0,
        description="Transaction friction and slippage costs in basis points",
    )
    capital: float = Field(
        default=500000.0, gt=0, description="Starting portfolio capital in INR"
    )
    ranking_rule: str = Field(
        default="momentum",
        description="Candidate ranking rule under capital constraints",
    )
    lot_size: int = Field(default=1, ge=1, description="Minimum share lot multiple")
    allow_crossover_equal: bool = Field(
        default=False,
        description="Whether equality on bar T-1 satisfies crossover",
    )
    ema_short: int = Field(default=20)
    ema_long: int = Field(default=200)

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize corpus -> capital
            if data.get("capital") is None and data.get("corpus") is not None:
                data["capital"] = data["corpus"]
            elif data.get("corpus") is None and data.get("capital") is not None:
                data["corpus"] = data["capital"]
            # Normalize stop_loss_pct -> sl_pct
            if data.get("sl_pct") is None and data.get("stop_loss_pct") is not None:
                data["sl_pct"] = data["stop_loss_pct"]
            elif data.get("stop_loss_pct") is None and data.get("sl_pct") is not None:
                data["stop_loss_pct"] = data["sl_pct"]
            # Convert whole percentages (e.g. 5, 7 -> 0.05, 0.07; 1, 2 -> 0.01, 0.02)
            sl_val = data.get("sl_pct")
            if isinstance(sl_val, (int, float)) and sl_val >= 1.0:
                data["sl_pct"] = sl_val / 100.0
                data["stop_loss_pct"] = data["sl_pct"]

            stop_val = data.get("stop_loss_pct")
            if isinstance(stop_val, (int, float)) and stop_val >= 1.0:
                data["stop_loss_pct"] = stop_val / 100.0
                data["sl_pct"] = data["stop_loss_pct"]

            risk_val = data.get("risk_pct")
            if isinstance(risk_val, (int, float)) and risk_val >= 1.0:
                data["risk_pct"] = risk_val / 100.0

            # Normalize ema_trend_spans -> ema_spans
            if (
                data.get("ema_spans") is None
                and data.get("ema_trend_spans") is not None
            ):
                data["ema_spans"] = data["ema_trend_spans"]
            # Normalize regime_spans -> regime_ema_spans
            if (
                data.get("regime_ema_spans") is None
                and data.get("regime_spans") is not None
            ):
                data["regime_ema_spans"] = data["regime_spans"]
        return data

    @property
    def corpus(self) -> float:
        """Backward-compatible alias for capital."""
        return self.capital

    @corpus.setter
    def corpus(self, val: float) -> None:
        self.capital = val

    @property
    def stop_loss_pct(self) -> float:
        """Backward-compatible alias for sl_pct."""
        return self.sl_pct

    @stop_loss_pct.setter
    def stop_loss_pct(self, val: float) -> None:
        self.sl_pct = val

    @property
    def ema_trend_spans(self) -> list[int]:
        """Backward-compatible alias for ema_spans."""
        return self.ema_spans

    @ema_trend_spans.setter
    def ema_trend_spans(self, val: list[int]) -> None:
        self.ema_spans = val

    @property
    def regime_spans(self) -> list[int]:
        """Backward-compatible alias for regime_ema_spans."""
        return self.regime_ema_spans

    @regime_spans.setter
    def regime_spans(self, val: list[int]) -> None:
        self.regime_ema_spans = val

    def to_dict(self) -> dict[str, Any]:
        """Serializes configuration to dictionary with all fields and aliases."""
        d = self.model_dump()
        d["corpus"] = self.capital
        d["stop_loss_pct"] = self.sl_pct
        d["ema_trend_spans"] = list(self.ema_spans)
        d["regime_spans"] = list(self.regime_ema_spans)
        return d
