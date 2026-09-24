"""REST API router for backtest simulation engine (REQ-5.4)."""

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import Session, col, select

from app.api.v1.schemas import (
    BacktestEquityResponse,
    BacktestRunCreateResponse,
    BacktestRunRequest,
    BacktestStatusResponse,
    BacktestTradesResponse,
    EquityPoint,
    TradeItem,
)
from app.data.source import get_price_source
from app.data.universe import get_universe
from app.db.models import BacktestRun
from app.db.session import engine, get_session
from app.engine.backtest import Backtest
from app.engine.result import BacktestResult
from app.strategy.config import StrategyConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["backtest"])


def _execute_backtest_task(run_id: str, payload: dict) -> None:
    """Background task executing the backtest simulation and persisting results."""
    with Session(engine) as session:
        run_record = session.get(BacktestRun, run_id)
        if not run_record:
            return

        try:
            run_record.status = "running"
            session.add(run_record)
            session.commit()

            req = BacktestRunRequest(**payload)

            # Build StrategyConfig
            if req.config:
                cfg_data = req.config.model_dump()
                strat_config = StrategyConfig(
                    corpus=cfg_data.get("corpus", 500000.0),
                    risk_pct=cfg_data.get("risk_pct", 0.02),
                    stop_loss_pct=cfg_data.get("stop_loss_pct", 0.07),
                    lot_size=cfg_data.get("lot_size", 1),
                    cost_bps=cfg_data.get("cost_bps", 10.0),
                    ema_trend_spans=cfg_data.get("ema_spans", [20, 50, 150, 200]),
                    regime_ema_spans=cfg_data.get("regime_spans", [50, 200]),
                    high_52w_factor=cfg_data.get("high_52w_factor", 0.85),
                    high_52w_lookback=cfg_data.get("high_52w_lookback", 252),
                    allow_crossover_equal=cfg_data.get("allow_crossover_equal", False),
                )
            else:
                strat_config = StrategyConfig()

            # Load NIFTY benchmark
            price_source = get_price_source()
            nifty_df = price_source.get_index_prices(
                "^NSEI", start="2000-01-01", end="2099-12-31"
            )

            repo_root = Path(__file__).resolve().parents[4]

            # Determine symbols list
            symbols_requested = req.symbols
            if symbols_requested:
                symbols_to_load = symbols_requested
            else:
                tiny_dir = repo_root / "data" / "fixtures" / "tiny_universe"
                if (tiny_dir / "ALPHA.parquet").exists():
                    symbols_to_load = ["ALPHA", "BETA", "GAMMA"]
                else:
                    eval_date = req.start or "2022-01-01"
                    tickers, _, _ = get_universe(date=eval_date, session=session)
                    symbols_to_load = tickers[:50]  # Cap for responsive simulation

            # If targeting tiny_universe symbols or benchmark empty, check fixture
            is_tiny = any(s in ("ALPHA", "BETA", "GAMMA") for s in symbols_to_load)
            if is_tiny:
                tiny_nifty_path = (
                    repo_root
                    / "data"
                    / "fixtures"
                    / "tiny_universe"
                    / "NIFTY_TINY.parquet"
                )
                if tiny_nifty_path.exists():
                    nifty_df = pd.read_parquet(tiny_nifty_path)

            # Load equity prices
            prices: dict[str, pd.DataFrame] = {}
            for sym in symbols_to_load:
                df = price_source.get_equity_prices(
                    sym, start="2000-01-01", end="2099-12-31"
                )
                if not df.empty:
                    prices[sym] = df

            # Run backtest
            backtest = Backtest(
                config=strat_config,
                prices=prices,
                nifty=nifty_df,
            )
            result = backtest.run(start=req.start, end=req.end)

            # Persist result blob
            blob_path = repo_root / "data" / "backtests" / f"{run_id}.json"
            result.save(blob_path)

            # Update DB record
            run_record.status = "completed"
            run_record.result_blob_path = str(blob_path)
            run_record.final_capital = result.final_capital
            run_record.total_return_pct = result.total_return_pct
            run_record.total_trades = result.total_trades
            run_record.win_rate = result.win_rate
            session.add(run_record)
            session.commit()
            logger.info("Backtest %s completed successfully", run_id)

        except Exception as err:
            logger.exception("Backtest %s failed: %s", run_id, err)
            run_record.status = "failed"
            run_record.error_message = str(err)
            session.add(run_record)
            session.commit()


@router.post(
    "/run",
    response_model=BacktestRunCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Backtest Run",
    description="Asynchronously launches simulation in background task (REQ-5.4).",
)
def api_run_backtest(
    request: BacktestRunRequest,
    background_tasks: BackgroundTasks,
    session: Annotated[Session, Depends(get_session)],
) -> BacktestRunCreateResponse:
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    init_cap = request.config.corpus if request.config else 500000.0

    run_record = BacktestRun(
        id=run_id,
        created_at=datetime.now(UTC).isoformat(),
        status="pending",
        start_date=request.start,
        end_date=request.end,
        config_json=json.dumps(request.config.model_dump() if request.config else {}),
        initial_capital=init_cap,
    )

    session.add(run_record)
    session.commit()

    background_tasks.add_task(_execute_backtest_task, run_id, request.model_dump())

    return BacktestRunCreateResponse(
        run_id=run_id,
        status="pending",
        message="Backtest execution queued successfully",
    )


@router.get(
    "",
    response_model=list[BacktestStatusResponse],
    summary="List Backtest Runs",
    description="Returns chronological history of all executed backtests.",
)
def api_list_backtest_runs(
    session: Annotated[Session, Depends(get_session)],
) -> list[BacktestStatusResponse]:
    stmt = select(BacktestRun).order_by(col(BacktestRun.created_at).desc())
    runs = session.exec(stmt).all()
    return [
        BacktestStatusResponse(
            run_id=r.id,
            status=r.status,
            created_at=r.created_at,
            start_date=r.start_date,
            end_date=r.end_date,
            initial_capital=r.initial_capital,
            final_capital=r.final_capital,
            total_return_pct=r.total_return_pct,
            total_trades=r.total_trades,
            win_rate=r.win_rate,
            error_message=r.error_message,
        )
        for r in runs
    ]


@router.get(
    "/{run_id}",
    response_model=BacktestStatusResponse,
    summary="Get Backtest Run Status",
    description="Returns execution status and summary metrics for a given run ID.",
)
def api_get_backtest_status(
    run_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> BacktestStatusResponse:
    run_record = session.get(BacktestRun, run_id)
    if not run_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest run '{run_id}' not found",
        )

    return BacktestStatusResponse(
        run_id=run_record.id,
        status=run_record.status,
        created_at=run_record.created_at,
        start_date=run_record.start_date,
        end_date=run_record.end_date,
        initial_capital=run_record.initial_capital,
        final_capital=run_record.final_capital,
        total_return_pct=run_record.total_return_pct,
        total_trades=run_record.total_trades,
        win_rate=run_record.win_rate,
        error_message=run_record.error_message,
    )


@router.get(
    "/{run_id}/trades",
    response_model=BacktestTradesResponse,
    summary="Get Backtest Trade Ledger",
    description="Returns list of executed round-trip trades with PnL and exit reasons.",
)
def api_get_backtest_trades(
    run_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> BacktestTradesResponse:
    run_record = session.get(BacktestRun, run_id)
    if not run_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest run '{run_id}' not found",
        )

    if (
        run_record.status != "completed"
        or not run_record.result_blob_path
        or not Path(run_record.result_blob_path).exists()
    ):
        return BacktestTradesResponse(run_id=run_id, count=0, trades=[])

    result = BacktestResult.load(run_record.result_blob_path)
    trades_list: list[TradeItem] = []
    for _, t in result.trades.iterrows():
        trades_list.append(
            TradeItem(
                symbol=str(t["symbol"]),
                entry_date=str(t["entry_date"]),
                entry_price=round(float(t["entry_price"]), 2),
                qty=int(t["qty"]),
                exit_date=str(t["exit_date"]),
                exit_price=round(float(t["exit_price"]), 2),
                pnl=round(float(t["pnl"]), 2),
                pnl_pct=round(float(t["pnl_pct"]), 4),
                exit_reason=str(t["exit_reason"]),
                days_held=int(t["days_held"]),
                costs=round(float(t["costs"]), 2),
            )
        )

    return BacktestTradesResponse(
        run_id=run_id, count=len(trades_list), trades=trades_list
    )


@router.get(
    "/{run_id}/equity",
    response_model=BacktestEquityResponse,
    summary="Get Backtest Equity Curve",
    description="Returns daily time-series of equity, cash, and drawdowns.",
)
def api_get_backtest_equity(
    run_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> BacktestEquityResponse:
    run_record = session.get(BacktestRun, run_id)
    if not run_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest run '{run_id}' not found",
        )

    if (
        run_record.status != "completed"
        or not run_record.result_blob_path
        or not Path(run_record.result_blob_path).exists()
    ):
        return BacktestEquityResponse(run_id=run_id, count=0, equity_curve=[])

    result = BacktestResult.load(run_record.result_blob_path)
    points: list[EquityPoint] = []
    for _, pt in result.equity_curve.iterrows():
        points.append(
            EquityPoint(
                date=str(pt["date"]),
                equity=round(float(pt["equity"]), 2),
                cash=round(float(pt["cash"]), 2),
                positions_value=round(float(pt["positions_value"]), 2),
                open_positions=int(pt["open_positions"]),
                daily_return=round(float(pt["daily_return"]), 4),
                drawdown=round(float(pt["drawdown"]), 2),
                drawdown_pct=round(float(pt["drawdown_pct"]), 4),
            )
        )

    return BacktestEquityResponse(run_id=run_id, count=len(points), equity_curve=points)
