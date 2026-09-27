from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    scope: str | None = Field(
        default=None,
        description="Optional ingestion scope ('smoke', 'midcap', 'full', 'custom').",
        examples=["smoke", "midcap", "full", "custom"],
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


class ConstituentDetail(BaseModel):
    symbol: str = Field(..., description="Equity ticker symbol")
    name: str = Field(..., description="Human-readable company name")
    rank: int = Field(..., description="Market capitalization rank (101 to 750)")
    sector: str = Field(
        default="Diversified",
        description="Industry or sector classification",
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
    details: list[ConstituentDetail] = Field(
        default_factory=list,
        description=(
            "Constituent stock metadata including company name, rank, and sector"
        ),
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
    model_config = ConfigDict(extra="ignore")

    corpus: float = Field(
        default=500000.0,
        gt=0,
        description="Starting portfolio corpus/capital in INR",
        examples=[500000.0],
    )
    capital: float | None = Field(
        default=None,
        gt=0,
        description="Starting portfolio capital in INR (alias for corpus)",
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
    sl_pct: float | None = Field(
        default=None,
        gt=0,
        lt=1,
        description="Stop loss percentage distance (alias for stop_loss_pct)",
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
    ranking_rule: str = Field(
        default="momentum",
        description=(
            "Candidate prioritization rule under capital constraints "
            "(momentum, alphabetical, 52w_proximity)"
        ),
        examples=["momentum"],
    )
    universe_start_rank: int = Field(
        default=101,
        ge=1,
        description="Starting universe rank (inclusive)",
        examples=[101],
    )
    universe_end_rank: int = Field(
        default=750,
        ge=1,
        description="Ending universe rank (inclusive)",
        examples=[750],
    )

    @model_validator(mode="before")
    @classmethod
    def handle_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # capital & corpus
            if data.get("capital") is not None and data.get("corpus") is None:
                data["corpus"] = data["capital"]
            elif data.get("corpus") is not None and data.get("capital") is None:
                data["capital"] = data["corpus"]
            elif data.get("capital") is not None and data.get("corpus") is not None:
                data["corpus"] = data["capital"]

            # sl_pct & stop_loss_pct
            if data.get("sl_pct") is not None and data.get("stop_loss_pct") is None:
                data["stop_loss_pct"] = data["sl_pct"]
            elif data.get("stop_loss_pct") is not None and data.get("sl_pct") is None:
                data["sl_pct"] = data["stop_loss_pct"]
            elif (
                data.get("sl_pct") is not None and data.get("stop_loss_pct") is not None
            ):
                data["stop_loss_pct"] = data["sl_pct"]

            # Convert whole numbers (e.g. 5, 7 -> 0.05, 0.07; 1, 2 -> 0.01, 0.02)
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
        return data


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

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "start_date" in data and "start" not in data:
                data["start"] = data["start_date"]
            if "end_date" in data and "end" not in data:
                data["end"] = data["end_date"]
            if "initial_capital" in data or "max_positions" in data:
                cfg = dict(data.get("config") or {})
                if "initial_capital" in data and "initial_capital" not in cfg:
                    cfg["initial_capital"] = data["initial_capital"]
                if "max_positions" in data and "max_positions" not in cfg:
                    cfg["max_positions"] = data["max_positions"]
                data["config"] = cfg
        return data


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
    config_version: str = Field(
        default="1.0", description="Configuration schema version"
    )
    sweep_id: str | None = Field(
        default=None, description="Parent parameter sweep ID if applicable"
    )
    initial_capital: float = Field(..., description="Starting capital in INR")
    final_capital: float | None = Field(
        default=None, description="Ending capital in INR"
    )
    total_return_pct: float | None = Field(
        default=None, description="Total portfolio return percentage"
    )
    cagr: float | None = Field(default=None, description="Compound Annual Growth Rate")
    total_trades: int | None = Field(
        default=None, description="Total closed round-trip trades"
    )
    win_rate: float | None = Field(
        default=None, description="Fraction of winning trades"
    )
    max_drawdown_pct: float | None = Field(
        default=None, description="Maximum percentage drawdown"
    )
    error_message: str | None = Field(
        default=None, description="Error explanation if failed"
    )


class SweepRunRequest(BaseModel):
    base_config: BacktestConfigSchema | None = Field(
        default=None,
        description="Optional base strategy configuration template",
    )
    param_grid: dict[str, list[Any]] = Field(
        ...,
        description="Map of parameter names to lists of candidate values to sweep",
        examples=[{"sl_pct": [0.05, 0.06, 0.07], "risk_pct": [0.01, 0.02, 0.03]}],
    )
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
    symbols: list[str] | None = Field(
        default=None,
        description="Optional subset of symbols (defaults to universe)",
        examples=[["ALPHA", "BETA", "GAMMA"]],
    )


class SweepRunCreateResponse(BaseModel):
    sweep_id: str = Field(..., description="Unique parameter sweep identifier")
    total_runs: int = Field(..., description="Total permutation child runs generated")
    run_ids: list[str] = Field(..., description="List of generated child run IDs")
    status: str = Field(default="pending", description="Initial lifecycle status")
    message: str = Field(
        default="Parameter sweep execution queued successfully",
        description="Informational status message",
    )


class SweepRunItem(BaseModel):
    run_id: str = Field(..., description="Child run ID")
    status: str = Field(..., description="Child run lifecycle status")
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameter values for this specific run",
    )
    initial_capital: float = Field(..., description="Starting capital")
    final_capital: float | None = Field(default=None, description="Ending capital")
    total_return_pct: float | None = Field(
        default=None, description="Total return percentage"
    )
    total_trades: int | None = Field(default=None, description="Total trades count")
    win_rate: float | None = Field(default=None, description="Win rate")
    max_drawdown_pct: float | None = Field(
        default=None, description="Maximum drawdown percentage"
    )
    cagr: float | None = Field(default=None, description="Compound Annual Growth Rate")
    error_message: str | None = Field(
        default=None, description="Error message if failed"
    )


class SweepStatusResponse(BaseModel):
    sweep_id: str = Field(..., description="Unique sweep identifier")
    status: str = Field(
        ...,
        description=(
            "Overall sweep status (pending, running, completed, partial, failed)"
        ),
    )
    created_at: str = Field(..., description="Creation ISO timestamp")
    param_grid: dict[str, list[Any]] = Field(
        default_factory=dict, description="Parameters swept"
    )
    total_runs: int = Field(..., description="Total permutation runs")
    completed_runs: int = Field(..., description="Number of completed runs so far")
    runs: list[SweepRunItem] = Field(
        ..., description="Summary metrics for each child run"
    )


class EquityPoint(BaseModel):
    date: str = Field(..., description="Session date (YYYY-MM-DD)")
    equity: float = Field(..., description="Total mark-to-market equity")
    cash: float = Field(..., description="Available cash balance")
    positions_value: float = Field(..., description="Open positions market value")
    open_positions: int = Field(..., description="Number of currently held positions")
    daily_return: float = Field(..., description="Day-over-day return fraction")
    drawdown: float = Field(..., description="Drawdown from equity peak in INR")
    drawdown_pct: float = Field(..., description="Drawdown percentage from peak")
    benchmark_equity: float | None = Field(
        default=None, description="Benchmark normalized equity value in INR"
    )


class CompareMetricItem(BaseModel):
    run_id: str = Field(..., description="Run identifier")
    status: str = Field(..., description="Run status")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Configuration parameters"
    )
    initial_capital: float = Field(..., description="Starting capital")
    final_capital: float | None = Field(default=None, description="Ending capital")
    total_return_pct: float | None = Field(
        default=None, description="Total return percentage"
    )
    cagr: float | None = Field(default=None, description="Compound Annual Growth Rate")
    total_trades: int | None = Field(default=None, description="Total trades count")
    win_rate: float | None = Field(default=None, description="Win rate")
    max_drawdown_pct: float | None = Field(
        default=None, description="Max percentage drawdown"
    )
    avg_profit: float | None = Field(
        default=None, description="Average profit on winning trades"
    )
    avg_loss: float | None = Field(
        default=None, description="Average loss on losing trades"
    )


class BacktestCompareResponse(BaseModel):
    run_ids: list[str] = Field(..., description="List of compared run IDs")
    runs: dict[str, CompareMetricItem] = Field(
        ..., description="Summary metrics dictionary keyed by run_id"
    )
    equity_curves: dict[str, list[EquityPoint]] = Field(
        default_factory=dict,
        description="Overlaid equity curves keyed by run_id",
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


class BacktestEquityResponse(BaseModel):
    run_id: str = Field(..., description="Unique backtest run identifier")
    count: int = Field(..., description="Number of equity curve data points")
    equity_curve: list[EquityPoint] = Field(
        ..., description="Chronological daily mark-to-market equity curve"
    )


class MonthlyReturnRow(BaseModel):
    year: int = Field(..., description="Calendar year")
    jan: float | None = Field(default=None, description="January compounded return")
    feb: float | None = Field(default=None, description="February compounded return")
    mar: float | None = Field(default=None, description="March compounded return")
    apr: float | None = Field(default=None, description="April compounded return")
    may: float | None = Field(default=None, description="May compounded return")
    jun: float | None = Field(default=None, description="June compounded return")
    jul: float | None = Field(default=None, description="July compounded return")
    aug: float | None = Field(default=None, description="August compounded return")
    sep: float | None = Field(default=None, description="September compounded return")
    oct: float | None = Field(default=None, description="October compounded return")
    nov: float | None = Field(default=None, description="November compounded return")
    dec: float | None = Field(default=None, description="December compounded return")
    total: float = Field(..., description="Full year compounded return")


class ReportMonthlyResponse(BaseModel):
    run_id: str = Field(..., description="Unique backtest run identifier")
    years: list[MonthlyReturnRow] = Field(
        ..., description="Month x year returns matrix"
    )


from app.reports.metrics import PerformanceMetrics  # noqa: E402


class ReportSummaryResponse(BaseModel):
    run_id: str = Field(..., description="Unique backtest run identifier")
    status: str = Field(..., description="Execution status")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Strategy parameters"
    )
    metrics: PerformanceMetrics = Field(
        ..., description="Calculated core and advanced KPIs"
    )


class CrossCheckPoint(BaseModel):
    date: str = Field(..., description="Session date (YYYY-MM-DD)")
    close: float = Field(..., description="Price used for indicators and evaluation")
    ema_20: float | None = Field(
        default=None, description="20-day Exponential Moving Average"
    )
    ema_50: float | None = Field(
        default=None, description="50-day Exponential Moving Average"
    )
    ema_150: float | None = Field(
        default=None, description="150-day Exponential Moving Average"
    )
    ema_200: float | None = Field(
        default=None, description="200-day Exponential Moving Average"
    )
    high_52w: float | None = Field(
        default=None, description="252-day rolling 52-week high"
    )
    entry: bool = Field(
        ..., description="Whether entry signal triggered on this session"
    )
    exit: bool = Field(..., description="Whether exit signal triggered on this session")


class CrossCheckResponse(BaseModel):
    run_id: str = Field(..., description="Backtest run identifier")
    symbol: str = Field(..., description="NSE equity ticker symbol")
    count: int = Field(..., description="Total trading sessions returned")
    rows: list[CrossCheckPoint] = Field(
        ..., description="Aligned indicator and signal data rows"
    )
    csv: str = Field(
        ..., description="Raw CSV string formatted for TradingView visual diff"
    )


class BacktestAuditResponse(BaseModel):
    run_id: str = Field(..., description="Unique backtest run identifier")
    git_sha: str = Field(
        ..., description="Git commit hash of codebase during execution"
    )
    config: dict[str, Any] = Field(..., description="Strategy configuration parameters")
    data_hash: str = Field(
        ..., description="SHA-256 snapshot hash of input parquet market data"
    )
    versions: dict[str, str] = Field(
        ..., description="Runtime and library dependencies versions"
    )
    created_at: str | None = Field(default=None, description="Execution ISO timestamp")


class PdfJobResponse(BaseModel):
    """Status record of an asynchronous PDF generation background job (REQ-9.4)."""

    job_id: str = Field(..., description="Unique background PDF generation job ID")
    status: str = Field(..., description="Job status: 'pending', 'ready', or 'failed'")
    file_path: str | None = Field(
        default=None, description="Absolute file path to ready PDF on server"
    )
    error: str | None = Field(
        default=None, description="Error message if generation failed"
    )
    created_at: str = Field(..., description="Job creation ISO timestamp")


class PdfJobCreateResponse(BaseModel):
    """Response returned when initiating an asynchronous PDF generation job.

    Covers REQ-9.4.
    """

    job_id: str = Field(..., description="Unique background PDF generation job ID")
    status: str = Field(default="pending", description="Initial job status")
    message: str = Field(
        default="PDF generation job accepted and processing in background.",
        description="Informational status message",
    )


class RetentionCleanupRequest(BaseModel):
    """Optional payload to override retention thresholds during cleanup."""

    max_runs: int | None = Field(
        default=None,
        description="Override maximum number of standalone backtest runs retained",
        ge=0,
    )
    max_sweeps: int | None = Field(
        default=None,
        description="Override maximum number of parameter sweep batches retained",
        ge=0,
    )


class RetentionCleanupResponse(BaseModel):
    """Execution report returned by the admin retention cleanup endpoint."""

    status: str = Field(..., description="Execution status ('success' or 'disabled')")
    max_runs_threshold: int | None = Field(
        default=None, description="Applied threshold for standalone backtest runs"
    )
    max_sweeps_threshold: int | None = Field(
        default=None, description="Applied threshold for parameter sweeps"
    )
    evicted_run_count: int = Field(
        default=0, description="Number of standalone and sweep child runs evicted"
    )
    evicted_sweep_count: int = Field(
        default=0, description="Number of parameter sweeps evicted"
    )
    evicted_runs: list[str] = Field(
        default_factory=list, description="List of evicted BacktestRun IDs"
    )
    evicted_sweeps: list[str] = Field(
        default_factory=list, description="List of evicted BacktestSweep IDs"
    )
