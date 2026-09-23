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
