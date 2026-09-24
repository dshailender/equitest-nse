from sqlmodel import Field, SQLModel


class PriceBase(SQLModel):
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: float = 0.0


class Price(PriceBase, table=True):
    __tablename__ = "prices"

    symbol: str = Field(primary_key=True, index=True)
    date: str = Field(primary_key=True, index=True)  # Format: YYYY-MM-DD


class IndexPrice(PriceBase, table=True):
    __tablename__ = "index_prices"

    symbol: str = Field(primary_key=True, index=True)
    date: str = Field(primary_key=True, index=True)  # Format: YYYY-MM-DD


class UniverseMembership(SQLModel, table=True):
    __tablename__ = "universe_membership"

    date: str = Field(primary_key=True, index=True)  # Format: YYYY-MM-DD
    symbol: str = Field(primary_key=True, index=True)
    rank: int = Field(index=True)


class BacktestRun(SQLModel, table=True):
    __tablename__ = "backtest_runs"

    id: str = Field(primary_key=True, index=True)
    created_at: str = Field(index=True)
    status: str = Field(default="pending", index=True)
    sweep_id: str | None = Field(default=None, index=True)
    config_version: str = Field(default="1.0")
    start_date: str | None = Field(default=None)
    end_date: str | None = Field(default=None)
    config_json: str = Field(default="{}")
    result_blob_path: str | None = Field(default=None)
    initial_capital: float = Field(default=500000.0)
    final_capital: float | None = Field(default=None)
    total_return_pct: float | None = Field(default=None)
    cagr: float | None = Field(default=None)
    total_trades: int | None = Field(default=None)
    win_rate: float | None = Field(default=None)
    max_drawdown_pct: float | None = Field(default=None)
    error_message: str | None = Field(default=None)


class BacktestSweep(SQLModel, table=True):
    __tablename__ = "backtest_sweeps"

    id: str = Field(primary_key=True, index=True)
    created_at: str = Field(index=True)
    status: str = Field(
        default="pending", index=True
    )  # pending, running, completed, partial, failed
    base_config_json: str = Field(default="{}")
    param_grid_json: str = Field(default="{}")
    total_runs: int = Field(default=0)
    completed_runs: int = Field(default=0)
    error_message: str | None = Field(default=None)
