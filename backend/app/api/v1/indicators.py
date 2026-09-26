from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, col, select

from app.api.v1.schemas import (
    IndicatorItem,
    IndicatorPreviewRequest,
    IndicatorResponse,
)
from app.data.source import get_price_source
from app.db.models import IndexPrice, Price
from app.db.session import get_session
from app.indicators.pipeline import (
    IndicatorConfig,
    compute_indicators,
    compute_nifty_indicators,
)

router = APIRouter(prefix="/indicators", tags=["indicators"])


def _parse_spans(spans_str: str) -> list[int]:
    """Parse comma-separated spans string into list of positive integers."""
    try:
        spans = [int(s.strip()) for s in spans_str.split(",") if s.strip()]
        if not spans or any(s < 1 for s in spans):
            raise ValueError()
        return spans
    except Exception as err:
        msg = (
            f"Invalid spans parameter '{spans_str}'. "
            "Must be comma-separated positive integers."
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=msg,
        ) from err


def _fetch_equity_df(
    symbol: str,
    session: Session,
    end: str | None = None,
    start: str | None = None,
) -> pd.DataFrame:
    """Fetch equity price history from DB, falling back to PriceSource."""
    clean_sym = symbol.strip().upper()
    stmt = select(Price).where(Price.symbol == clean_sym)
    if start:
        stmt = stmt.where(Price.date >= start)
    if end:
        stmt = stmt.where(Price.date <= end)
    stmt = stmt.order_by(col(Price.date).asc())
    rows = session.exec(stmt).all()

    if rows:
        data = [r.model_dump() for r in rows]
        return pd.DataFrame(data)

    # Fallback to PriceSource fixture
    price_source = get_price_source()
    df = price_source.get_equity_prices(
        clean_sym, start=start or "2000-01-01", end=end or "2099-12-31"
    )
    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price data found for symbol '{clean_sym}'",
        )
    return df


def _fetch_nifty_df(session: Session, end: str | None = None) -> pd.DataFrame:
    """Fetch NIFTY benchmark price history from DB, falling back to PriceSource."""
    index_symbols = ["^NSEI", "NIFTY50", "NIFTY"]
    for sym in index_symbols:
        stmt = select(IndexPrice).where(IndexPrice.symbol == sym)
        if end:
            stmt = stmt.where(IndexPrice.date <= end)
        stmt = stmt.order_by(col(IndexPrice.date).asc())
        rows = session.exec(stmt).all()
        if rows:
            data = [r.model_dump() for r in rows]
            return pd.DataFrame(data)

    # Fallback to PriceSource fixture
    price_source = get_price_source()
    for sym in index_symbols:
        df = price_source.get_index_prices(
            sym, start="2000-01-01", end=end or "2099-12-31"
        )
        if not df.empty:
            return df

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No benchmark data found for NIFTY",
    )


def _safe_float(val: object) -> float | None:
    """Safely converts value to float or None if missing/NaN."""
    return None if (val is None or pd.isna(val)) else float(val)


def _build_indicator_items(
    augmented_df: pd.DataFrame, spans: list[int], start: str | None = None
) -> list[IndicatorItem]:
    """Convert indicator-augmented DataFrame to list of IndicatorItem models."""
    if start:
        df_filtered = augmented_df[augmented_df["date"] >= start].copy()
    else:
        df_filtered = augmented_df.copy()

    items: list[IndicatorItem] = []
    for _, row in df_filtered.iterrows():
        ind_dict: dict[str, float | None] = {}
        for s in spans:
            col_name = f"ema_{s}"
            val = row.get(col_name)
            ind_dict[col_name] = _safe_float(val)

        if "high_52w" in row:
            ind_dict["high_52w"] = _safe_float(row.get("high_52w"))

        items.append(
            IndicatorItem(
                date=str(row["date"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                adj_close=float(row["adj_close"]),
                volume=float(row.get("volume", 0.0)),
                ema_20=_safe_float(row.get("ema_20")),
                ema_50=_safe_float(row.get("ema_50")),
                ema_150=_safe_float(row.get("ema_150")),
                ema_200=_safe_float(row.get("ema_200")),
                high_52w=_safe_float(row.get("high_52w")),
                indicators=ind_dict,
            )
        )
    return items


@router.get(
    "/nifty",
    response_model=IndicatorResponse,
    summary="Get NIFTY Benchmark Indicators",
    description="Returns NIFTY benchmark index OHLCV with EMAs (default 50 and 200).",
)
def api_get_nifty_indicators(
    start: Annotated[
        str | None, Query(description="Optional start date (YYYY-MM-DD)")
    ] = None,
    end: Annotated[
        str | None, Query(description="Optional end date (YYYY-MM-DD)")
    ] = None,
    spans: Annotated[
        str,
        Query(
            description="Comma-separated list of EMA spans",
            examples=["50,200"],
        ),
    ] = "50,200",
    session: Annotated[Session, Depends(get_session)] = None,
) -> IndicatorResponse:
    span_list = _parse_spans(spans)
    df = _fetch_nifty_df(session, end=end)
    augmented = compute_nifty_indicators(df, spans=span_list)
    items = _build_indicator_items(augmented, spans=span_list, start=start)

    return IndicatorResponse(
        symbol="NIFTY50",
        count=len(items),
        indicators=items,
    )


@router.get(
    "/{symbol}",
    response_model=IndicatorResponse,
    summary="Get Symbol Technical Indicators",
    description=(
        "Returns historical OHLCV augmented with EMAs (20, 50, 150, 200) and 52W high."
    ),
)
def api_get_symbol_indicators(
    symbol: str,
    start: Annotated[
        str | None, Query(description="Optional start date (YYYY-MM-DD)")
    ] = None,
    end: Annotated[
        str | None, Query(description="Optional end date (YYYY-MM-DD)")
    ] = None,
    spans: Annotated[
        str,
        Query(
            description="Comma-separated list of EMA spans",
            examples=["20,50,150,200"],
        ),
    ] = "20,50,150,200",
    session: Annotated[Session, Depends(get_session)] = None,
) -> IndicatorResponse:
    clean_sym = symbol.strip().upper()
    span_list = _parse_spans(spans)
    df = _fetch_equity_df(clean_sym, session, end=end)

    config = IndicatorConfig(
        spans=span_list, include_high_52w=True, high_52w_lookback=252
    )
    augmented = compute_indicators(df, config=config)
    items = _build_indicator_items(augmented, spans=span_list, start=start)

    return IndicatorResponse(
        symbol=clean_sym,
        count=len(items),
        indicators=items,
    )


@router.post(
    "/preview",
    response_model=IndicatorResponse,
    summary="Preview Custom Indicators",
    description="Calculates custom indicators dynamically with given configuration.",
)
def api_preview_indicators(
    req: IndicatorPreviewRequest,
    session: Annotated[Session, Depends(get_session)],
) -> IndicatorResponse:
    clean_sym = req.symbol.strip().upper()
    is_nifty = clean_sym in ["NIFTY", "NIFTY50", "^NSEI"]

    if is_nifty:
        df = _fetch_nifty_df(session, end=req.end)
    else:
        df = _fetch_equity_df(clean_sym, session, end=req.end)

    config = IndicatorConfig(
        spans=req.config.spans,
        include_high_52w=req.config.include_high_52w,
        high_52w_lookback=req.config.high_52w_lookback,
    )
    augmented = compute_indicators(df, config=config)
    items = _build_indicator_items(augmented, spans=req.config.spans, start=req.start)

    return IndicatorResponse(
        symbol=clean_sym,
        count=len(items),
        indicators=items,
    )
