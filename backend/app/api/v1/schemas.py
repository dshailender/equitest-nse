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
