"""REST API router for backtest simulation engine (REQ-5.4)."""

import itertools
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import Session, col, select

from app.api.v1.schemas import (
    BacktestAuditResponse,
    BacktestCompareResponse,
    BacktestEquityResponse,
    BacktestRunCreateResponse,
    BacktestRunRequest,
    BacktestStatusResponse,
    BacktestTradesResponse,
    CompareMetricItem,
    EquityPoint,
    SweepRunCreateResponse,
    SweepRunItem,
    SweepRunRequest,
    SweepStatusResponse,
    TradeItem,
)
from app.data.source import get_price_source
from app.data.universe import get_universe
from app.db.models import BacktestRun, BacktestSweep
from app.db.session import engine, get_session
from app.engine.backtest import Backtest
from app.engine.result import BacktestResult
from app.strategy.config import StrategyConfig
from app.validation.audit import load_run_audit, record_run_audit

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
                strat_config = StrategyConfig(**cfg_data)
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
                eval_date = req.start or "2022-01-01"
                tickers, _, _ = get_universe(
                    date=eval_date,
                    session=session,
                    start_rank=strat_config.universe_start_rank,
                    end_rank=strat_config.universe_end_rank,
                )
                symbols_to_load = tickers

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

            # Prepare dynamic point-in-time universe provider (AUD-C-002)
            if symbols_requested:

                def universe_provider(eval_date: str) -> tuple[list[str], bool]:
                    return symbols_requested, False

            else:

                def universe_provider(eval_date: str) -> tuple[list[str], bool]:
                    tickers, bias, _ = get_universe(
                        date=eval_date,
                        session=session,
                        start_rank=strat_config.universe_start_rank,
                        end_rank=strat_config.universe_end_rank,
                    )
                    return tickers, bias

            # Run backtest
            backtest = Backtest(
                config=strat_config,
                prices=prices,
                nifty=nifty_df,
                universe_provider=universe_provider,
            )
            result = backtest.run(start=req.start, end=req.end)

            # Persist result blob
            blob_path = repo_root / "data" / "backtests" / f"{run_id}.json"
            result.save(blob_path)

            # Record audit provenance
            record_run_audit(
                run_id=run_id,
                config=strat_config.model_dump(),
                symbols=symbols_to_load,
                created_at=run_record.created_at,
            )

            # Update DB record
            run_record.status = "completed"
            run_record.result_blob_path = str(blob_path)
            run_record.final_capital = result.final_capital
            run_record.total_return_pct = result.total_return_pct
            run_record.cagr = result.cagr
            run_record.total_trades = result.total_trades
            run_record.win_rate = result.win_rate
            run_record.max_drawdown_pct = result.max_drawdown_pct
            session.add(run_record)
            session.commit()
            logger.info("Backtest %s completed successfully", run_id)

        except Exception as err:
            logger.exception("Backtest %s failed: %s", run_id, err)
            run_record.status = "failed"
            run_record.error_message = str(err)
            session.add(run_record)
            session.commit()


def _execute_sweep_task(sweep_id: str, child_tasks: list[tuple[str, dict]]) -> None:
    """Background task executing all permutations in a parameter sweep."""
    with Session(engine) as session:
        sweep_record = session.get(BacktestSweep, sweep_id)
        if not sweep_record:
            return
        sweep_record.status = "running"
        session.add(sweep_record)
        session.commit()

    completed = 0
    failed = 0
    for run_id, payload in child_tasks:
        try:
            _execute_backtest_task(run_id, payload)
            with Session(engine) as session:
                r = session.get(BacktestRun, run_id)
                if r and r.status == "completed":
                    completed += 1
                else:
                    failed += 1
                sweep_record = session.get(BacktestSweep, sweep_id)
                if sweep_record:
                    sweep_record.completed_runs = completed
                    session.add(sweep_record)
                    session.commit()
        except Exception as err:
            logger.exception("Error executing sweep child run %s: %s", run_id, err)
            failed += 1

    with Session(engine) as session:
        sweep_record = session.get(BacktestSweep, sweep_id)
        if sweep_record:
            if completed == len(child_tasks):
                sweep_record.status = "completed"
            elif completed > 0:
                sweep_record.status = "partial"
            else:
                sweep_record.status = "failed"
            sweep_record.completed_runs = completed
            session.add(sweep_record)
            session.commit()
    logger.info(
        "Sweep %s completed with %d successes and %d failures",
        sweep_id,
        completed,
        failed,
    )


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
    init_cap = (
        request.config.capital
        if (request.config and request.config.capital is not None)
        else (request.config.corpus if request.config else 500000.0)
    )

    run_record = BacktestRun(
        id=run_id,
        created_at=datetime.now(UTC).isoformat(),
        status="pending",
        config_version="1.0",
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


@router.post(
    "/sweep",
    response_model=SweepRunCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Parameter Sweep",
    description=(
        "Generates permutation child runs across parameter grid and "
        "launches simulation (REQ-6.2)."
    ),
)
def api_run_sweep(
    request: SweepRunRequest,
    background_tasks: BackgroundTasks,
    session: Annotated[Session, Depends(get_session)],
) -> SweepRunCreateResponse:
    if not request.param_grid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="param_grid must not be empty",
        )

    for k, v in request.param_grid.items():
        if not isinstance(v, list) or len(v) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parameter '{k}' must have a non-empty list of values",
            )

    # Normalize percentage parameters if provided as whole numbers (e.g. 5 -> 0.05)
    normalized_grid: dict[str, list[Any]] = {}
    for k, v_list in request.param_grid.items():
        if k in ("sl_pct", "stop_loss_pct", "risk_pct"):
            normalized_grid[k] = [
                val / 100.0 if (isinstance(val, (int, float)) and val >= 1.0) else val
                for val in v_list
            ]
        else:
            normalized_grid[k] = list(v_list)

    param_keys = list(normalized_grid.keys())
    value_combinations = list(
        itertools.product(*(normalized_grid[k] for k in param_keys))
    )

    if len(value_combinations) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Sweep size {len(value_combinations)} exceeds "
                "maximum allowed of 50 permutations"
            ),
        )

    sweep_id = f"sweep_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(UTC).isoformat()

    child_run_ids: list[str] = []
    child_tasks: list[tuple[str, dict]] = []

    base_dict = request.base_config.model_dump() if request.base_config else {}

    for combo in value_combinations:
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        child_run_ids.append(run_id)

        combo_dict = dict(zip(param_keys, combo, strict=True))
        child_cfg_dict = dict(base_dict)
        child_cfg_dict.update(combo_dict)

        child_req_dict = {
            "start": request.start,
            "end": request.end,
            "symbols": request.symbols,
            "config": child_cfg_dict,
        }
        child_tasks.append((run_id, child_req_dict))

        init_cap = float(
            child_cfg_dict.get("capital") or child_cfg_dict.get("corpus") or 500000.0
        )

        child_run_record = BacktestRun(
            id=run_id,
            created_at=now_iso,
            status="pending",
            sweep_id=sweep_id,
            config_version="1.0",
            start_date=request.start,
            end_date=request.end,
            config_json=json.dumps(child_cfg_dict),
            initial_capital=init_cap,
        )
        session.add(child_run_record)

    sweep_record = BacktestSweep(
        id=sweep_id,
        created_at=now_iso,
        status="pending",
        base_config_json=json.dumps(base_dict),
        param_grid_json=json.dumps(request.param_grid),
        total_runs=len(value_combinations),
        completed_runs=0,
    )
    session.add(sweep_record)
    session.commit()

    background_tasks.add_task(_execute_sweep_task, sweep_id, child_tasks)

    return SweepRunCreateResponse(
        sweep_id=sweep_id,
        total_runs=len(value_combinations),
        run_ids=child_run_ids,
        status="pending",
        message="Parameter sweep execution queued successfully",
    )


@router.get(
    "/sweep/{sweep_id}",
    response_model=SweepStatusResponse,
    summary="Get Parameter Sweep Status",
    description=(
        "Returns lifecycle status and summary metrics for all child runs "
        "in a sweep (REQ-6.2)."
    ),
)
def api_get_sweep_status(
    sweep_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> SweepStatusResponse:
    sweep_record = session.get(BacktestSweep, sweep_id)
    if not sweep_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sweep '{sweep_id}' not found",
        )

    stmt = (
        select(BacktestRun)
        .where(BacktestRun.sweep_id == sweep_id)
        .order_by(BacktestRun.created_at)
    )
    child_runs = session.exec(stmt).all()

    param_grid = json.loads(sweep_record.param_grid_json or "{}")

    items = []
    completed_count = 0
    for r in child_runs:
        if r.status == "completed":
            completed_count += 1
        cfg = json.loads(r.config_json or "{}")
        params = {k: cfg.get(k) for k in param_grid.keys() if k in cfg}
        items.append(
            SweepRunItem(
                run_id=r.id,
                status=r.status,
                params=params,
                initial_capital=r.initial_capital,
                final_capital=r.final_capital,
                total_return_pct=r.total_return_pct,
                cagr=r.cagr,
                total_trades=r.total_trades,
                win_rate=r.win_rate,
                max_drawdown_pct=r.max_drawdown_pct,
                error_message=r.error_message,
            )
        )

    return SweepStatusResponse(
        sweep_id=sweep_record.id,
        status=sweep_record.status,
        created_at=sweep_record.created_at,
        param_grid=param_grid,
        total_runs=sweep_record.total_runs,
        completed_runs=completed_count,
        runs=items,
    )


@router.get(
    "/compare",
    response_model=BacktestCompareResponse,
    summary="Compare Multiple Backtest Runs",
    description=(
        "Returns aligned metrics table and overlaid equity curves for "
        "given run IDs (REQ-6.3)."
    ),
)
def api_compare_backtest_runs(
    run_ids: str,
    session: Annotated[Session, Depends(get_session)],
) -> BacktestCompareResponse:
    id_list = [rid.strip() for rid in run_ids.split(",") if rid.strip()]
    if not id_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No run_ids provided for comparison",
        )

    runs_map: dict[str, CompareMetricItem] = {}
    curves_map: dict[str, list[EquityPoint]] = {}

    for rid in id_list:
        run_record = session.get(BacktestRun, rid)
        if not run_record:
            continue

        cfg = json.loads(run_record.config_json or "{}")
        avg_profit = None
        avg_loss = None

        if (
            run_record.status == "completed"
            and run_record.result_blob_path
            and Path(run_record.result_blob_path).exists()
        ):
            try:
                res = BacktestResult.load(run_record.result_blob_path)
                avg_profit = res.avg_profit
                avg_loss = res.avg_loss
                points = []
                for _, pt in res.equity_curve.iterrows():
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
                curves_map[rid] = points
            except Exception as e:
                logger.warning("Could not load equity curve for %s: %s", rid, e)

        runs_map[rid] = CompareMetricItem(
            run_id=run_record.id,
            status=run_record.status,
            config=cfg,
            initial_capital=run_record.initial_capital,
            final_capital=run_record.final_capital,
            total_return_pct=run_record.total_return_pct,
            cagr=run_record.cagr,
            total_trades=run_record.total_trades,
            win_rate=run_record.win_rate,
            max_drawdown_pct=run_record.max_drawdown_pct,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
        )

    return BacktestCompareResponse(
        run_ids=id_list,
        runs=runs_map,
        equity_curves=curves_map,
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
            config_version=r.config_version,
            sweep_id=r.sweep_id,
            initial_capital=r.initial_capital,
            final_capital=r.final_capital,
            total_return_pct=r.total_return_pct,
            cagr=r.cagr,
            total_trades=r.total_trades,
            win_rate=r.win_rate,
            max_drawdown_pct=r.max_drawdown_pct,
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
        config_version=run_record.config_version,
        sweep_id=run_record.sweep_id,
        initial_capital=run_record.initial_capital,
        final_capital=run_record.final_capital,
        total_return_pct=run_record.total_return_pct,
        cagr=run_record.cagr,
        total_trades=run_record.total_trades,
        win_rate=run_record.win_rate,
        max_drawdown_pct=run_record.max_drawdown_pct,
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

    # Attempt to resolve benchmark equity curve (AUD-H-001)
    bench_map: dict[str, float] = {}
    if not result.equity_curve.empty and "date" in result.equity_curve.columns:
        if "benchmark_equity" in result.equity_curve.columns:
            for _, pt in result.equity_curve.iterrows():
                if pd.notna(pt.get("benchmark_equity")):
                    bench_map[str(pt["date"])[:10]] = float(pt["benchmark_equity"])
        else:
            try:
                from app.reports.metrics import resolve_benchmark_prices

                start_str = str(result.equity_curve["date"].iloc[0])[:10]
                end_str = str(result.equity_curve["date"].iloc[-1])[:10]
                b_df = resolve_benchmark_prices(start_str, end_str)
                if b_df is not None and not b_df.empty and "date" in b_df.columns:
                    close_col = (
                        "close"
                        if "close" in b_df.columns
                        else ("adj_close" if "adj_close" in b_df.columns else None)
                    )
                    if close_col:
                        b_sorted = b_df.sort_values("date").reset_index(drop=True)
                        b0 = float(b_sorted[close_col].iloc[0])
                        if b0 > 0:
                            for _, b_row in b_sorted.iterrows():
                                d_key = str(b_row["date"])[:10]
                                bench_map[d_key] = round(
                                    result.initial_capital
                                    * (float(b_row[close_col]) / b0),
                                    2,
                                )
            except Exception:
                pass

    for _, pt in result.equity_curve.iterrows():
        d_str = str(pt["date"])
        d_key = d_str[:10]
        bench_val = bench_map.get(d_key)
        points.append(
            EquityPoint(
                date=d_str,
                equity=round(float(pt["equity"]), 2),
                cash=round(float(pt["cash"]), 2),
                positions_value=round(float(pt["positions_value"]), 2),
                open_positions=int(pt["open_positions"]),
                daily_return=round(float(pt["daily_return"]), 4),
                drawdown=round(float(pt["drawdown"]), 2),
                drawdown_pct=round(float(pt["drawdown_pct"]), 4),
                benchmark_equity=(
                    round(float(bench_val), 2) if bench_val is not None else None
                ),
            )
        )

    return BacktestEquityResponse(run_id=run_id, count=len(points), equity_curve=points)


@router.get(
    "/{run_id}/audit",
    response_model=BacktestAuditResponse,
    summary="Get Backtest Run Audit Provenance",
    description=(
        "Returns audit and reproducibility provenance record for a backtest "
        "run (REQ-8.2), including Git commit SHA, config parameters, "
        "data snapshot hash, and library versions."
    ),
)
def api_get_backtest_audit(
    run_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> BacktestAuditResponse:
    try:
        audit_data = load_run_audit(run_id, session)
        return BacktestAuditResponse(**audit_data)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except Exception as err:
        logger.exception("Failed loading audit for run %s: %s", run_id, err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed loading audit record: {err}",
        ) from err
