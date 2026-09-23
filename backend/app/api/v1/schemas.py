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
