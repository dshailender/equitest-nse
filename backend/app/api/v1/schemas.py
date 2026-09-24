from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    start: str = Field(
        ...,
        description="Start date for data ingestion in YYYY-MM-DD format",
        examples=["2020-01-01"],
    )
    end: str = Field(
        ...,
        description="End date for data ingestion in YYYY-MM-DD format",
        examples=["2024-01-01"],
    )
    symbols: list[str] | None = Field(
        default=None,
        description="Optional list of ticker symbols. Defaults to active universe.",
        examples=[["RELIANCE", "HDFCBANK", "INFY"]],
    )


class IngestResponse(BaseModel):
    job_id: str = Field(..., description="Unique ingestion job execution ID")
    status: str = Field(
        ..., description="Job execution status (completed, partial, failed)"
    )
    symbols_ingested: int = Field(
        ..., description="Number of symbols successfully processed"
    )
    rows_ingested: int = Field(
        ..., description="Total new price rows inserted into database"
    )
    errors: list[str] = Field(
        default=[], description="List of non-fatal ingestion warnings or errors"
    )


class CoverageItem(BaseModel):
    symbol: str = Field(..., description="Equity or index ticker symbol")
    first_date: str | None = Field(
        default=None, description="Earliest available trading session"
    )
    last_date: str | None = Field(
        default=None, description="Latest available trading session"
    )
    rows: int = Field(..., description="Total number of stored trading sessions")


class CoverageResponse(BaseModel):
    items: list[CoverageItem] = Field(
        ..., description="List of symbol coverage summaries"
    )


class UniverseResponse(BaseModel):
    date: str = Field(
        ..., description="Target date for universe constituent evaluation"
    )
    count: int = Field(
        ..., description="Total number of constituent tickers (ranks 101 to 750)"
    )
    tickers: list[str] = Field(
        ..., description="List of ticker symbols belonging to the universe"
    )
    survivorship_bias: bool = Field(
        ...,
        description=(
            "True if fallback current list was used due to missing "
            "point-in-time constituent records"
        ),
    )


class PriceItem(BaseModel):
    date: str = Field(..., description="Session date (YYYY-MM-DD)")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price during session")
    low: float = Field(..., description="Lowest price during session")
    close: float = Field(..., description="Unadjusted closing price")
    adj_close: float = Field(..., description="Corporate-action adjusted closing price")
    volume: float = Field(..., description="Total trading volume")


class PricesResponse(BaseModel):
    symbol: str = Field(..., description="Equity ticker symbol")
    count: int = Field(..., description="Number of sessions returned")
    prices: list[PriceItem] = Field(
        ..., description="Chronological series of OHLCV bars"
    )


class IndicatorConfigSchema(BaseModel):
    spans: list[int] = Field(
        default=[20, 50, 150, 200],
        description="EMA spans to compute (e.g. [20, 50, 150, 200])",
        examples=[[20, 50, 150, 200]],
    )
    include_high_52w: bool = Field(
        default=True,
        description="Whether to compute rolling 52-week high",
    )
    high_52w_lookback: int = Field(
        default=252,
        description="Lookback window sessions for 52W high calculation",
        examples=[252],
    )


class IndicatorItem(BaseModel):
    date: str = Field(..., description="Session date (YYYY-MM-DD)")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price during session")
    low: float = Field(..., description="Lowest price during session")
    close: float = Field(..., description="Unadjusted closing price")
    adj_close: float = Field(..., description="Corporate-action adjusted closing price")
    volume: float = Field(..., description="Total trading volume")
    ema_20: float | None = Field(default=None, description="20-day EMA")
    ema_50: float | None = Field(default=None, description="50-day EMA")
    ema_150: float | None = Field(default=None, description="150-day EMA")
    ema_200: float | None = Field(default=None, description="200-day EMA")
    high_52w: float | None = Field(default=None, description="52-week rolling high")
    indicators: dict[str, float | None] = Field(
        default_factory=dict,
        description="Dictionary of dynamic or custom computed indicator values",
    )


class IndicatorResponse(BaseModel):
    symbol: str = Field(..., description="Equity or benchmark ticker symbol")
    count: int = Field(..., description="Number of indicator bars returned")
    indicators: list[IndicatorItem] = Field(
        ..., description="Chronological series of indicator-augmented OHLCV bars"
    )


class IndicatorPreviewRequest(BaseModel):
    symbol: str = Field(
        default="RELIANCE",
        description="Symbol to compute preview indicators for",
        examples=["RELIANCE"],
    )
    start: str | None = Field(
        default=None,
        description="Optional start date (YYYY-MM-DD)",
        examples=["2020-01-01"],
    )
    end: str | None = Field(
        default=None,
        description="Optional end date (YYYY-MM-DD)",
        examples=["2023-12-31"],
    )
    config: IndicatorConfigSchema = Field(
        default_factory=IndicatorConfigSchema,
        description="Indicator calculation configuration",
    )


class SignalItem(BaseModel):
    date: str = Field(..., description="Session date (YYYY-MM-DD)")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price during session")
    low: float = Field(..., description="Lowest price during session")
    close: float = Field(..., description="Unadjusted closing price")
    adj_close: float = Field(..., description="Corporate-action adjusted closing price")
    volume: float = Field(..., description="Total trading volume")
    ema_20: float | None = Field(default=None, description="20-day EMA")
    ema_50: float | None = Field(default=None, description="50-day EMA")
    ema_150: float | None = Field(default=None, description="150-day EMA")
    ema_200: float | None = Field(default=None, description="200-day EMA")
    high_52w: float | None = Field(default=None, description="52-week rolling high")
    regime_ok: bool = Field(
        ..., description="Market regime filter (NIFTY Close > EMA 50 & EMA 200)"
    )
    trend_ok: bool = Field(
        ..., description="Stock trend filter (EMA 20 > EMA 50 > EMA 150 > EMA 200)"
    )
    near_52w_high: bool = Field(
        ..., description="52W high proximity filter (Close > 0.85 * 52W High)"
    )
    crossover: bool = Field(
        ...,
        description=(
            "EMA20 crossover trigger (Close_T > EMA20_T and Close_T-1 < EMA20_T-1)"
        ),
    )

    entry: bool = Field(
        ..., description="Entry signal triggered on bar T for execution on T+1 open"
    )
    exit: bool = Field(
        ..., description="Exit signal triggered on bar T (Close_T < EMA20_T)"
    )


class SignalsResponse(BaseModel):
    symbol: str = Field(..., description="Equity ticker symbol")
    count: int = Field(..., description="Number of signal rows returned")
    signals: list[SignalItem] = Field(
        ..., description="Chronological series of signal-augmented OHLCV bars"
    )


class ScreenResponse(BaseModel):
    date: str = Field(
        ..., description="Target date for universe screening (YYYY-MM-DD)"
    )
    count: int = Field(
        ..., description="Total number of constituent tickers with entry signal"
    )
    symbols: list[str] = Field(
        ..., description="List of ticker symbols with active entry signals"
    )
    survivorship_bias: bool = Field(
        ...,
        description=(
            "True if fallback current list was used due to missing "
            "point-in-time constituent records"
        ),
    )


class RiskSizeRequest(BaseModel):
    corpus: float = Field(
        ...,
        gt=0,
        description="Total account capital / portfolio corpus",
        examples=[500000.0],
    )
    entry: float = Field(
        ...,
        gt=0,
        description="Proposed trade entry price per share",
        examples=[100.0],
    )
    sl_pct: float = Field(
        default=0.07,
        gt=0,
        lt=1,
        description="Stop loss percentage distance from entry (default 0.07)",
        examples=[0.07],
    )
    risk_pct: float = Field(
        default=0.02,
        gt=0,
        lt=1,
        description="Maximum account risk percentage per trade (default 0.02)",
        examples=[0.02],
    )
    lot_size: int = Field(
        default=1,
        ge=1,
        description="Minimum lot size multiple (default 1)",
        examples=[1],
    )


class RiskSizeResponse(BaseModel):
    qty: int = Field(
        ...,
        description="Derived integer position size / share quantity",
    )
    capital_required: float = Field(
        ...,
        description="Total capital required for this position (qty * entry)",
    )
    sl_price: float = Field(
        ...,
        description="Stop loss price level (entry * (1 - sl_pct))",
    )
    risk_amount: float = Field(
        ...,
        description="Maximum monetary account risk for this trade (corpus * risk_pct)",
    )


class RiskConfigResponse(BaseModel):
    corpus: float = Field(
        default=500000.0,
        description="Default portfolio starting corpus in INR",
    )
    risk_pct: float = Field(
        default=0.02,
        description="Default risk percentage per trade (2%)",
    )
    stop_loss_pct: float = Field(
        default=0.07,
        description="Default stop loss percentage (7%)",
    )
    lot_size: int = Field(
        default=1,
        description="Default share lot size multiple (1)",
    )
    cost_bps: float = Field(
        default=10.0,
        description=(
            "Default transaction friction and slippage costs in basis points "
            "(10 bps = 0.10%)"
        ),
    )


class BacktestConfigSchema(BaseModel):
    corpus: float = Field(
        default=500000.0,
        gt=0,
        description="Starting portfolio corpus in INR",
        examples=[500000.0],
    )
    risk_pct: float = Field(
        default=0.02,
        gt=0,
        lt=1,
        description="Risk percentage per trade (default 0.02 = 2%)",
        examples=[0.02],
    )
    stop_loss_pct: float = Field(
        default=0.07,
        gt=0,
        lt=1,
        description="Stop loss percentage distance (default 0.07 = 7%)",
        examples=[0.07],
    )
    lot_size: int = Field(
        default=1,
        ge=1,
        description="Minimum share lot multiple",
        examples=[1],
    )
    cost_bps: float = Field(
        default=10.0,
        ge=0,
        description="Transaction friction and slippage costs in basis points",
        examples=[10.0],
    )
    ema_spans: list[int] = Field(
        default=[20, 50, 150, 200],
        description="Trend EMA spans",
        examples=[[20, 50, 150, 200]],
    )
    regime_spans: list[int] = Field(
        default=[50, 200],
        description="NIFTY regime EMA spans",
        examples=[[50, 200]],
    )
    high_52w_factor: float = Field(
        default=0.85,
        gt=0,
        description="Proximity threshold to 52-week high",
        examples=[0.85],
    )
    high_52w_lookback: int = Field(
        default=252,
        gt=0,
        description="Lookback window sessions for 52W high",
        examples=[252],
    )
    allow_crossover_equal: bool = Field(
        default=False,
        description="Whether equality on bar T-1 satisfies crossover condition",
    )


class BacktestRunRequest(BaseModel):
    start: str | None = Field(
        default=None,
        description="Optional backtest start date (YYYY-MM-DD)",
        examples=["2020-06-01"],
    )
    end: str | None = Field(
        default=None,
        description="Optional backtest end date (YYYY-MM-DD)",
        examples=["2022-04-29"],
    )
    config: BacktestConfigSchema | None = Field(
        default=None,
        description="Optional strategy parameter overrides",
    )
    symbols: list[str] | None = Field(
        default=None,
        description="Optional subset of symbols (defaults to universe)",
        examples=[["ALPHA", "BETA", "GAMMA"]],
    )


class BacktestRunCreateResponse(BaseModel):
    run_id: str = Field(..., description="Unique backtest run identifier")
    status: str = Field(
        default="pending",
        description="Initial lifecycle status (pending, running)",
    )
    message: str = Field(
        default="Backtest execution queued",
        description="Informational status message",
    )


class BacktestStatusResponse(BaseModel):
    run_id: str = Field(..., description="Unique backtest run identifier")
    status: str = Field(
        ...,
        description="Current lifecycle status (pending, running, completed, failed)",
    )
    created_at: str = Field(..., description="Creation ISO timestamp")
    start_date: str | None = Field(default=None, description="Start date")
    end_date: str | None = Field(default=None, description="End date")
    initial_capital: float = Field(..., description="Starting capital in INR")
    final_capital: float | None = Field(
        default=None, description="Ending capital in INR"
    )
    total_return_pct: float | None = Field(
        default=None, description="Total portfolio return percentage"
    )
    total_trades: int | None = Field(
        default=None, description="Total closed round-trip trades"
    )
    win_rate: float | None = Field(
        default=None, description="Fraction of winning trades"
    )
    error_message: str | None = Field(
        default=None, description="Error explanation if failed"
    )


class TradeItem(BaseModel):
    symbol: str = Field(..., description="Equity ticker symbol")
    entry_date: str = Field(..., description="Entry date (YYYY-MM-DD)")
    entry_price: float = Field(..., description="Execution buy price with slippage")
    qty: int = Field(..., description="Executed share quantity")
    exit_date: str = Field(..., description="Exit date (YYYY-MM-DD)")
    exit_price: float = Field(..., description="Execution sell price with slippage")
    pnl: float = Field(..., description="Net realized profit/loss in INR")
    pnl_pct: float = Field(..., description="Net realized return percentage")
    exit_reason: str = Field(
        ..., description="Exit reason: stop_loss, gap, exit_signal"
    )
    days_held: int = Field(..., description="Trading sessions held")
    costs: float = Field(..., description="Total friction costs in INR")


class BacktestTradesResponse(BaseModel):
    run_id: str = Field(..., description="Unique backtest run identifier")
    count: int = Field(..., description="Total number of closed trades")
    trades: list[TradeItem] = Field(..., description="Chronological trade ledger")


class EquityPoint(BaseModel):
    date: str = Field(..., description="Session date (YYYY-MM-DD)")
    equity: float = Field(..., description="Total mark-to-market equity")
    cash: float = Field(..., description="Available cash balance")
    positions_value: float = Field(..., description="Open positions market value")
    open_positions: int = Field(..., description="Number of currently held positions")
    daily_return: float = Field(..., description="Day-over-day return fraction")
    drawdown: float = Field(..., description="Drawdown from equity peak in INR")
    drawdown_pct: float = Field(..., description="Drawdown percentage from peak")


class BacktestEquityResponse(BaseModel):
    run_id: str = Field(..., description="Unique backtest run identifier")
    count: int = Field(..., description="Number of equity curve data points")
    equity_curve: list[EquityPoint] = Field(
        ..., description="Chronological daily mark-to-market equity curve"
    )
