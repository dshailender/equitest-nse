from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, col, func, select

from app.api.v1.schemas import (
    ConstituentDetail,
    CoverageItem,
    CoverageResponse,
    IngestRequest,
    IngestResponse,
    PriceItem,
    PricesResponse,
    UniverseResponse,
)
from app.data.ingest import ingest_market_data
from app.data.universe import get_universe
from app.db.models import Price
from app.db.session import get_session

router = APIRouter(tags=["data"])


@router.post(
    "/data/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest Market Data",
    description="Ingests historical OHLCV data for equities and universe.",
)
def api_ingest_data(
    req: IngestRequest,
    session: Annotated[Session, Depends(get_session)],
) -> IngestResponse:
    result = ingest_market_data(
        session=session,
        start=req.start,
        end=req.end,
        symbols=req.symbols,
    )
    return IngestResponse(**result)


@router.get(
    "/data/coverage",
    response_model=CoverageResponse,
    summary="Get Data Coverage",
    description="Returns stored date ranges and session counts for symbols.",
)
def api_get_coverage(
    session: Annotated[Session, Depends(get_session)],
) -> CoverageResponse:
    # Query min date, max date, and count grouped by symbol
    stmt = (
        select(
            Price.symbol,
            func.min(Price.date).label("first_date"),
            func.max(Price.date).label("last_date"),
            func.count(Price.date).label("rows"),
        )
        .group_by(Price.symbol)
        .order_by(Price.symbol)
    )
    results = session.exec(stmt).all()

    priority = {"RELIANCE": 0, "HDFCBANK": 1, "INFY": 2, "TATAMOTORS": 3}
    sorted_results = sorted(results, key=lambda r: (priority.get(r[0], 99), r[0]))

    items = [
        CoverageItem(
            symbol=row[0],
            first_date=row[1],
            last_date=row[2],
            rows=row[3],
        )
        for row in sorted_results
    ]
    return CoverageResponse(items=items)


@router.get(
    "/universe",
    response_model=UniverseResponse,
    summary="Get Universe Constituents",
    description="Returns tickers ranked 101 to 750 with survivorship bias flag.",
)
def api_get_universe(
    date: Annotated[
        str | None,
        Query(
            description="Target date in YYYY-MM-DD format. Defaults to UTC today.",
            examples=["2023-01-01"],
        ),
    ] = None,
    session: Annotated[Session, Depends(get_session)] = None,
) -> UniverseResponse:
    target_date = date or datetime.now(UTC).strftime("%Y-%m-%d")
    tickers, survivorship_bias, details = get_universe(target_date, session=session)
    return UniverseResponse(
        date=target_date,
        count=len(tickers),
        tickers=tickers,
        details=[ConstituentDetail(**d) for d in details],
        survivorship_bias=survivorship_bias,
    )


@router.get(
    "/prices/{symbol}",
    response_model=PricesResponse,
    summary="Get Symbol Prices",
    description="Returns historical OHLCV prices for symbol, filtered chronologically.",
)
def api_get_prices(
    symbol: str,
    start: Annotated[
        str | None, Query(description="Optional start date (YYYY-MM-DD)")
    ] = None,
    end: Annotated[
        str | None, Query(description="Optional end date (YYYY-MM-DD)")
    ] = None,
    session: Annotated[Session, Depends(get_session)] = None,
) -> PricesResponse:
    clean_symbol = symbol.strip().upper()

    stmt = select(Price).where(Price.symbol == clean_symbol)

    if start:
        stmt = stmt.where(Price.date >= start)
    if end:
        # Enforce no look-ahead: only sessions on or before end date
        stmt = stmt.where(Price.date <= end)

    stmt = stmt.order_by(col(Price.date).asc())
    rows = session.exec(stmt).all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price data found for symbol '{clean_symbol}'",
        )

    price_items = [
        PriceItem(
            date=r.date,
            open=r.open,
            high=r.high,
            low=r.low,
            close=r.close,
            adj_close=r.adj_close,
            volume=r.volume,
        )
        for r in rows
    ]

    return PricesResponse(
        symbol=clean_symbol,
        count=len(price_items),
        prices=price_items,
    )
