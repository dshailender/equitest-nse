from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, select

from app.api.v1.indicators import _fetch_equity_df, _fetch_nifty_df, _safe_float
from app.api.v1.schemas import ScreenResponse, SignalItem, SignalsResponse
from app.data.source import get_price_source
from app.data.universe import get_universe
from app.db.models import Price
from app.db.session import get_session
from app.strategy.config import StrategyConfig
from app.strategy.signals import entry_signal, generate_signals, market_regime_ok

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get(
    "/screen",
    response_model=ScreenResponse,
    summary="Screen Universe for Entry Signals",
    description=(
        "Returns point-in-time universe constituent symbols with an active "
        "entry signal on the given date (REQ-3.4)."
    ),
)
def api_screen_signals(
    date: Annotated[
        str,
        Query(
            description="Target evaluation date in YYYY-MM-DD format",
            examples=["2020-06-25"],
            pattern=r"^\d{4}-\d{2}-\d{2}$",
        ),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ScreenResponse:
    # 1. Fetch NIFTY benchmark up to target date
    try:
        nifty_df = _fetch_nifty_df(session, end=date)
    except HTTPException:
        # If no benchmark data exists at all
        tickers, survivorship_bias, _ = get_universe(date, session=session)
        return ScreenResponse(
            date=date,
            count=0,
            symbols=[],
            survivorship_bias=survivorship_bias,
        )

    # 2. Check NIFTY regime on target date
    regime = market_regime_ok(nifty_df)
    regime_valid = bool(regime.get(date, False))

    # Resolve universe constituents on target date
    tickers, survivorship_bias, _ = get_universe(date, session=session)

    # If regime is False, rule REQ-3.1 dictates zero trades take place
    if not regime_valid:
        return ScreenResponse(
            date=date,
            count=0,
            symbols=[],
            survivorship_bias=survivorship_bias,
        )

    # 3. Identify candidate symbols that have price records
    # Check DB prices on date
    db_candidates = session.exec(
        select(Price.symbol).where(col(Price.symbol).in_(tickers), Price.date == date)
    ).all()
    candidate_set = set(db_candidates)

    # Also check fixtures if in CSV mode
    price_source = get_price_source()
    if hasattr(price_source, "fixtures_dir"):
        for sym in tickers:
            fpath = price_source.fixtures_dir / f"{sym}.parquet"
            if fpath.exists():
                candidate_set.add(sym)

    # 4. For each candidate symbol, evaluate entry signal on date
    matching_symbols: list[str] = []
    # 400 calendar days covers 252-day 52W high and 200-day EMA
    import pandas as pd

    screen_start = (pd.to_datetime(date) - pd.DateOffset(days=400)).strftime("%Y-%m-%d")
    for sym in sorted(candidate_set):
        try:
            stock_df = _fetch_equity_df(sym, session, end=date, start=screen_start)
            if stock_df.empty:
                continue

            # Ensure data covers target date
            if "date" in stock_df.columns:
                last_bar_date = str(stock_df["date"].iloc[-1])
                if last_bar_date != date:
                    continue

            sig = entry_signal(stock_df, nifty_df)
            if not sig.empty and bool(sig.iloc[-1]):
                matching_symbols.append(sym)
        except Exception:
            continue

    return ScreenResponse(
        date=date,
        count=len(matching_symbols),
        symbols=matching_symbols,
        survivorship_bias=survivorship_bias,
    )


@router.get(
    "/{symbol}",
    response_model=SignalsResponse,
    summary="Get Symbol Trading Signals",
    description=(
        "Returns chronological series of OHLCV bars with technical indicators, "
        "filters, and entry/exit signal evaluations (REQ-3.4, REQ-3.5)."
    ),
)
def api_get_symbol_signals(
    symbol: str,
    start: Annotated[
        str | None, Query(description="Optional start date (YYYY-MM-DD)")
    ] = None,
    end: Annotated[
        str | None, Query(description="Optional end date (YYYY-MM-DD)")
    ] = None,
    session: Annotated[Session, Depends(get_session)] = None,
) -> SignalsResponse:
    clean_sym = symbol.strip().upper()

    # 1. Fetch equity and benchmark data
    stock_df = _fetch_equity_df(clean_sym, session, end=end)
    nifty_df = _fetch_nifty_df(session, end=end)

    # 2. Generate signals
    cfg = StrategyConfig()
    augmented = generate_signals(stock_df, nifty_df, config=cfg)

    # 3. Filter by start date if provided
    if start:
        df_filtered = augmented[augmented["date"] >= start].copy()
    else:
        df_filtered = augmented.copy()

    # 4. Construct SignalItem objects
    items: list[SignalItem] = []
    for _, row in df_filtered.iterrows():
        items.append(
            SignalItem(
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
                regime_ok=bool(row["regime_ok"]),
                trend_ok=bool(row["trend_ok"]),
                near_52w_high=bool(row["near_52w_high"]),
                crossover=bool(row["crossover"]),
                entry=bool(row["entry"]),
                exit=bool(row["exit"]),
            )
        )

    return SignalsResponse(
        symbol=clean_sym,
        count=len(items),
        signals=items,
    )
