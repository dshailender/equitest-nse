#!/usr/bin/env python3
"""Phase 0: Contract Extractor Script.

Extracts golden request/response behavioral contracts from the running FastAPI monolith
and freezes them as executable contract fixtures under data/migration/contracts/.

Invariants asserted:
- INV-10: Paisa-level determinism (₹482,707.20 final capital on tiny universe)
- INV-9: Cryptographic run provenance
- INV-1..INV-8: Trading strategy and risk constraints
"""

import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure backend is on Python path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
os.environ["DATA_SOURCE"] = "CSV"

from app.db.models import BacktestRun
from app.db.session import engine
from app.main import app
from app.reports.jobs import job_manager
from fastapi.testclient import TestClient
from sqlmodel import Session


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: Any) -> str:
    """Canonical JSON serializer: recursive sorted keys, compact separators, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def run_extraction():
    print("=" * 70)
    print("EQUITYTEST NSE: Phase 0 Contract Extraction & Behavioral Freeze")
    print("=" * 70)

    contracts_dir = REPO_ROOT / "data" / "migration" / "contracts"
    endpoints_dir = contracts_dir / "endpoints"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    endpoints_dir.mkdir(parents=True, exist_ok=True)

    client = TestClient(app)

    # -------------------------------------------------------------------------
    # 1. Health Endpoints
    # -------------------------------------------------------------------------
    print("\n[1/8] Extracting Health Contracts...")
    health_fixtures = []

    res = client.get("/health")
    assert res.status_code == 200, f"/health failed: {res.text}"
    health_fixtures.append(
        {
            "id": "health_root",
            "endpoint": "/health",
            "method": "GET",
            "scenario": "Root service operational check",
            "request": {"url": "/health", "headers": {}, "body": None},
            "response": {
                "status_code": res.status_code,
                "headers": {"content-type": res.headers.get("content-type")},
                "body": res.json(),
            },
        }
    )

    res = client.get("/api/v1/health")
    assert res.status_code == 200, f"/api/v1/health failed: {res.text}"
    health_fixtures.append(
        {
            "id": "health_api_v1",
            "endpoint": "/api/v1/health",
            "method": "GET",
            "scenario": "API v1 service operational check",
            "request": {"url": "/api/v1/health", "headers": {}, "body": None},
            "response": {
                "status_code": res.status_code,
                "headers": {"content-type": res.headers.get("content-type")},
                "body": res.json(),
            },
        }
    )

    with open(endpoints_dir / "health.json", "w", encoding="utf-8") as f:
        json.dump(health_fixtures, f, indent=2)

    # -------------------------------------------------------------------------
    # 2. Data & Coverage Endpoints
    # -------------------------------------------------------------------------
    print("\n[2/8] Extracting Data, Ingest & Coverage Contracts...")
    data_fixtures = []

    # POST /api/v1/data/ingest
    ingest_req = {
        "start": "2020-01-01",
        "end": "2021-12-31",
        "symbols": ["RELIANCE", "INFY"],
    }
    res = client.post("/api/v1/data/ingest", json=ingest_req)
    assert res.status_code == 200, f"/data/ingest failed: {res.text}"
    data_fixtures.append(
        {
            "id": "data_ingest_standard",
            "endpoint": "/api/v1/data/ingest",
            "method": "POST",
            "scenario": "Ingest market data for RELIANCE and INFY",
            "request": {
                "url": "/api/v1/data/ingest",
                "headers": {"Content-Type": "application/json"},
                "body": ingest_req,
            },
            "response": {
                "status_code": res.status_code,
                "headers": {"content-type": res.headers.get("content-type")},
                "body": res.json(),
            },
        }
    )

    # GET /api/v1/data/coverage
    res = client.get("/api/v1/data/coverage")
    assert res.status_code == 200, f"/data/coverage failed: {res.text}"
    data_fixtures.append(
        {
            "id": "data_coverage",
            "endpoint": "/api/v1/data/coverage",
            "method": "GET",
            "scenario": "Query stored date ranges and session counts",
            "request": {"url": "/api/v1/data/coverage", "headers": {}, "body": None},
            "response": {
                "status_code": res.status_code,
                "headers": {"content-type": res.headers.get("content-type")},
                "body": res.json(),
            },
        }
    )

    with open(endpoints_dir / "data.json", "w", encoding="utf-8") as f:
        json.dump(data_fixtures, f, indent=2)

    # -------------------------------------------------------------------------
    # 3. Universe & Prices Endpoints
    # -------------------------------------------------------------------------
    print("\n[3/8] Extracting Universe & Prices Contracts...")
    universe_fixtures = []

    # GET /api/v1/universe (dated)
    res = client.get("/api/v1/universe?date=2021-06-01")
    assert res.status_code == 200, f"/universe dated failed: {res.text}"
    u_body = res.json()
    assert (
        u_body["count"] == 650
    ), f"Expected 650 universe tickers, got {u_body['count']}"
    assert u_body["survivorship_bias"] is False
    universe_fixtures.append(
        {
            "id": "universe_point_in_time",
            "endpoint": "/api/v1/universe",
            "method": "GET",
            "scenario": "Point-in-time universe query (INV-2: Survivorship Bias Prevention, INV-3: Top 100 Exclusion)",
            "invariants": ["INV-2", "INV-3"],
            "request": {
                "url": "/api/v1/universe?date=2021-06-01",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": res.status_code,
                "headers": {"content-type": res.headers.get("content-type")},
                "body_summary": {
                    "date": u_body["date"],
                    "count": u_body["count"],
                    "survivorship_bias": u_body["survivorship_bias"],
                    "sample_tickers": u_body["tickers"][:5],
                    "sample_details": u_body["details"][:2],
                },
            },
        }
    )

    with open(endpoints_dir / "universe.json", "w", encoding="utf-8") as f:
        json.dump(universe_fixtures, f, indent=2)

    prices_fixtures = []
    # GET /api/v1/prices/{symbol}
    res = client.get("/api/v1/prices/RELIANCE?start=2021-01-01&end=2021-01-15")
    assert res.status_code == 200, f"/prices/RELIANCE failed: {res.text}"
    p_body = res.json()
    prices_fixtures.append(
        {
            "id": "prices_symbol_range",
            "endpoint": "/api/v1/prices/{symbol}",
            "method": "GET",
            "scenario": "Historical OHLCV for RELIANCE filtered chronologically",
            "request": {
                "url": "/api/v1/prices/RELIANCE?start=2021-01-01&end=2021-01-15",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": res.status_code,
                "headers": {"content-type": res.headers.get("content-type")},
                "body": p_body,
            },
        }
    )

    # GET /api/v1/prices/{symbol} unknown 404
    res = client.get("/api/v1/prices/UNKNOWN_SYMBOL_XYZ")
    assert (
        res.status_code == 404
    ), f"Expected 404 for unknown symbol, got {res.status_code}"
    prices_fixtures.append(
        {
            "id": "prices_symbol_unknown_404",
            "endpoint": "/api/v1/prices/{symbol}",
            "method": "GET",
            "scenario": "Unknown symbol price query yields 404",
            "request": {
                "url": "/api/v1/prices/UNKNOWN_SYMBOL_XYZ",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 404,
                "headers": {"content-type": res.headers.get("content-type")},
                "body": res.json(),
            },
        }
    )

    with open(endpoints_dir / "prices.json", "w", encoding="utf-8") as f:
        json.dump(prices_fixtures, f, indent=2)

    # -------------------------------------------------------------------------
    # 4. Indicators & Signals Endpoints
    # -------------------------------------------------------------------------
    print("\n[4/8] Extracting Indicators & Signals Contracts...")
    ind_fixtures = []

    # GET /api/v1/indicators/{symbol}
    res = client.get("/api/v1/indicators/ALPHA")
    assert res.status_code == 200, f"/indicators/ALPHA failed: {res.text}"
    ind_body = res.json()
    ind_fixtures.append(
        {
            "id": "indicators_symbol",
            "endpoint": "/api/v1/indicators/{symbol}",
            "method": "GET",
            "scenario": "EMA (20, 50, 150, 200) and 52-week rolling high (INV-1, INV-8)",
            "invariants": ["INV-1", "INV-8"],
            "request": {"url": "/api/v1/indicators/ALPHA", "headers": {}, "body": None},
            "response": {
                "status_code": res.status_code,
                "headers": {"content-type": res.headers.get("content-type")},
                "body_summary": {
                    "symbol": ind_body["symbol"],
                    "count": ind_body["count"],
                    "sample_points": ind_body["indicators"][-2:],
                },
            },
        }
    )

    # GET /api/v1/indicators/nifty
    res = client.get("/api/v1/indicators/nifty")
    assert res.status_code == 200, f"/indicators/nifty failed: {res.text}"
    nifty_body = res.json()
    ind_fixtures.append(
        {
            "id": "indicators_nifty",
            "endpoint": "/api/v1/indicators/nifty",
            "method": "GET",
            "scenario": "NIFTY regime filter benchmark indicator series (INV-3)",
            "invariants": ["INV-3"],
            "request": {"url": "/api/v1/indicators/nifty", "headers": {}, "body": None},
            "response": {
                "status_code": res.status_code,
                "headers": {"content-type": res.headers.get("content-type")},
                "body_summary": {
                    "symbol": nifty_body["symbol"],
                    "count": nifty_body["count"],
                    "sample_points": nifty_body["indicators"][-2:],
                },
            },
        }
    )

    # POST /api/v1/indicators/preview
    prev_req = {"symbol": "ALPHA", "emas": [20, 50, 200]}
    res = client.post("/api/v1/indicators/preview", json=prev_req)
    assert res.status_code == 200, f"/indicators/preview failed: {res.text}"
    ind_fixtures.append(
        {
            "id": "indicators_preview",
            "endpoint": "/api/v1/indicators/preview",
            "method": "POST",
            "scenario": "Dynamic parameter EMA computation preview",
            "request": {
                "url": "/api/v1/indicators/preview",
                "headers": {"Content-Type": "application/json"},
                "body": prev_req,
            },
            "response": {
                "status_code": res.status_code,
                "headers": {"content-type": res.headers.get("content-type")},
                "body_summary": {
                    "symbol": res.json()["symbol"],
                    "count": res.json()["count"],
                    "sample_points": res.json()["indicators"][-2:],
                },
            },
        }
    )

    with open(endpoints_dir / "indicators.json", "w", encoding="utf-8") as f:
        json.dump(ind_fixtures, f, indent=2)

    sig_fixtures = []
    # GET /api/v1/signals/{symbol}
    res = client.get("/api/v1/signals/ALPHA")
    assert res.status_code == 200, f"/signals/ALPHA failed: {res.text}"
    sig_fixtures.append(
        {
            "id": "signals_symbol",
            "endpoint": "/api/v1/signals/{symbol}",
            "method": "GET",
            "scenario": "Entry and exit signals with candidate ranking (INV-1, INV-5)",
            "invariants": ["INV-1", "INV-5"],
            "request": {"url": "/api/v1/signals/ALPHA", "headers": {}, "body": None},
            "response": {
                "status_code": res.status_code,
                "headers": {"content-type": res.headers.get("content-type")},
                "body_summary": {
                    "symbol": res.json()["symbol"],
                    "count": res.json()["count"],
                    "sample_points": res.json()["signals"][-2:],
                },
            },
        }
    )

    # GET /api/v1/signals/screen
    res = client.get("/api/v1/signals/screen?date=2021-05-24")
    assert res.status_code == 200, f"/signals/screen failed: {res.text}"
    sig_fixtures.append(
        {
            "id": "signals_screen",
            "endpoint": "/api/v1/signals/screen",
            "method": "GET",
            "scenario": "Point-in-time universe screening for entry candidates ranked by momentum (INV-5)",
            "invariants": ["INV-5"],
            "request": {
                "url": "/api/v1/signals/screen?date=2021-05-24",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": res.status_code,
                "headers": {"content-type": res.headers.get("content-type")},
                "body": res.json(),
            },
        }
    )

    with open(endpoints_dir / "signals.json", "w", encoding="utf-8") as f:
        json.dump(sig_fixtures, f, indent=2)

    # -------------------------------------------------------------------------
    # 5. Risk Endpoints
    # -------------------------------------------------------------------------
    print("\n[5/8] Extracting Risk Contracts...")
    risk_fixtures = []

    # POST /api/v1/risk/size
    size_req = {
        "corpus": 500000.0,
        "entry": 200.0,
        "sl_pct": 0.07,
        "risk_pct": 0.02,
        "lot_size": 1,
    }
    res = client.post("/api/v1/risk/size", json=size_req)
    assert res.status_code == 200, f"/risk/size failed: {res.text}"
    r_body = res.json()
    assert r_body["qty"] == 714, f"Expected 714 qty floored, got {r_body.get('qty')}"
    risk_fixtures.append(
        {
            "id": "risk_position_sizing",
            "endpoint": "/api/v1/risk/size",
            "method": "POST",
            "scenario": "Position sizing floored to lot size with 2% capital risk (INV-6)",
            "invariants": ["INV-6"],
            "request": {
                "url": "/api/v1/risk/size",
                "headers": {"Content-Type": "application/json"},
                "body": size_req,
            },
            "response": {
                "status_code": res.status_code,
                "headers": {"content-type": res.headers.get("content-type")},
                "body": r_body,
            },
        }
    )

    # GET /api/v1/risk/config
    res = client.get("/api/v1/risk/config")
    assert res.status_code == 200, f"/risk/config failed: {res.text}"
    risk_fixtures.append(
        {
            "id": "risk_config",
            "endpoint": "/api/v1/risk/config",
            "method": "GET",
            "scenario": "Risk configuration defaults",
            "request": {"url": "/api/v1/risk/config", "headers": {}, "body": None},
            "response": {
                "status_code": res.status_code,
                "headers": {"content-type": res.headers.get("content-type")},
                "body": res.json(),
            },
        }
    )

    with open(endpoints_dir / "risk.json", "w", encoding="utf-8") as f:
        json.dump(risk_fixtures, f, indent=2)

    # -------------------------------------------------------------------------
    # 6. Backtest Simulation Lifecycle & Golden Run (INV-10: ₹482,707.20)
    # -------------------------------------------------------------------------
    print(
        "\n[6/8] Extracting Golden Backtest (₹482,707.20) & Backtest Lifecycle Contracts..."
    )
    backtest_fixtures = []

    golden_payload = {
        "start": "2020-06-01",
        "end": "2022-04-29",
        "symbols": ["ALPHA", "BETA", "GAMMA"],
        "config": {
            "corpus": 500000.0,
            "risk_pct": 0.02,
            "stop_loss_pct": 0.07,
            "lot_size": 1,
            "cost_bps": 10.0,
        },
    }

    # Trigger golden backtest
    post_res = client.post("/api/v1/backtest/run", json=golden_payload)
    assert post_res.status_code == 202, f"POST /backtest/run failed: {post_res.text}"
    run_create_data = post_res.json()
    golden_run_id = run_create_data["run_id"]
    print(f"   Golden run executed: {golden_run_id}")

    backtest_fixtures.append(
        {
            "id": "backtest_run_create",
            "endpoint": "/api/v1/backtest/run",
            "method": "POST",
            "scenario": "Execute synchronous/background simulation run (INV-10)",
            "invariants": ["INV-1", "INV-4", "INV-6", "INV-7", "INV-10"],
            "request": {
                "url": "/api/v1/backtest/run",
                "headers": {"Content-Type": "application/json"},
                "body": golden_payload,
            },
            "response": {
                "status_code": 202,
                "headers": {"content-type": post_res.headers.get("content-type")},
                "body": run_create_data,
            },
        }
    )

    # GET /api/v1/backtest/{run_id}
    status_res = client.get(f"/api/v1/backtest/{golden_run_id}")
    assert (
        status_res.status_code == 200
    ), f"GET /backtest/{golden_run_id} failed: {status_res.text}"
    status_data = status_res.json()
    assert (
        status_data["status"] == "completed"
    ), f"Status not completed: {status_data['status']}"
    assert (
        status_data["final_capital"] == 482707.20
    ), f"INV-10 VIOLATION: expected 482707.20, got {status_data['final_capital']}"
    assert (
        status_data["total_trades"] == 2
    ), f"Expected 2 trades, got {status_data['total_trades']}"
    print(
        f"   Golden determinism confirmed: ₹{status_data['final_capital']:,.2f} across {status_data['total_trades']} trades."
    )

    backtest_fixtures.append(
        {
            "id": "backtest_status_completed",
            "endpoint": "/api/v1/backtest/{run_id}",
            "method": "GET",
            "scenario": "Get completed backtest run status & performance metrics (INV-10)",
            "invariants": ["INV-10"],
            "request": {
                "url": f"/api/v1/backtest/{golden_run_id}",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {"content-type": status_res.headers.get("content-type")},
                "body": status_data,
            },
        }
    )

    # GET /api/v1/backtest/{run_id}/trades
    trades_res = client.get(f"/api/v1/backtest/{golden_run_id}/trades")
    assert trades_res.status_code == 200
    trades_data = trades_res.json()
    assert trades_data["count"] == 2
    assert trades_data["trades"][0]["exit_reason"] == "gap", "INV-4 gap down check"
    backtest_fixtures.append(
        {
            "id": "backtest_trades_ledger",
            "endpoint": "/api/v1/backtest/{run_id}/trades",
            "method": "GET",
            "scenario": "Retrieve complete executed trades ledger (INV-4, INV-7, INV-10)",
            "invariants": ["INV-4", "INV-7", "INV-10"],
            "request": {
                "url": f"/api/v1/backtest/{golden_run_id}/trades",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {"content-type": trades_res.headers.get("content-type")},
                "body": trades_data,
            },
        }
    )

    # GET /api/v1/backtest/{run_id}/equity
    equity_res = client.get(f"/api/v1/backtest/{golden_run_id}/equity")
    assert equity_res.status_code == 200
    equity_data = equity_res.json()
    assert equity_data["count"] == 500
    assert equity_data["equity_curve"][-1]["equity"] == 482707.20
    backtest_fixtures.append(
        {
            "id": "backtest_equity_curve",
            "endpoint": "/api/v1/backtest/{run_id}/equity",
            "method": "GET",
            "scenario": "Retrieve chronological daily equity curve (INV-10)",
            "invariants": ["INV-10"],
            "request": {
                "url": f"/api/v1/backtest/{golden_run_id}/equity",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {"content-type": equity_res.headers.get("content-type")},
                "body_summary": {
                    "run_id": equity_data["run_id"],
                    "count": equity_data["count"],
                    "first_point": equity_data["equity_curve"][0],
                    "last_point": equity_data["equity_curve"][-1],
                },
            },
        }
    )

    # GET /api/v1/backtest (list runs)
    list_res = client.get("/api/v1/backtest")
    assert list_res.status_code == 200
    backtest_fixtures.append(
        {
            "id": "backtest_list_history",
            "endpoint": "/api/v1/backtest",
            "method": "GET",
            "scenario": "List historical executed backtest runs",
            "request": {"url": "/api/v1/backtest", "headers": {}, "body": None},
            "response": {
                "status_code": 200,
                "headers": {"content-type": list_res.headers.get("content-type")},
                "body_summary": {
                    "count": len(list_res.json()),
                    "latest_run_id": list_res.json()[0]["run_id"],
                },
            },
        }
    )

    # GET /api/v1/backtest/{run_id}/audit
    audit_res = client.get(f"/api/v1/backtest/{golden_run_id}/audit")
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert "git_sha" in audit_data and "data_hash" in audit_data, "INV-9 check"
    backtest_fixtures.append(
        {
            "id": "backtest_audit_provenance",
            "endpoint": "/api/v1/backtest/{run_id}/audit",
            "method": "GET",
            "scenario": "Retrieve cryptographic provenance record (INV-9)",
            "invariants": ["INV-9"],
            "request": {
                "url": f"/api/v1/backtest/{golden_run_id}/audit",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {"content-type": audit_res.headers.get("content-type")},
                "body": audit_data,
            },
        }
    )

    with open(endpoints_dir / "backtest.json", "w", encoding="utf-8") as f:
        json.dump(backtest_fixtures, f, indent=2)

    # -------------------------------------------------------------------------
    # Save Dedicated Golden Backtest Run Snapshot (INV-10 Benchmark)
    # -------------------------------------------------------------------------
    golden_snapshot = {
        "benchmark": "INV-10 Paisa-Level Determinism",
        "target_equity": 482707.20,
        "request_payload": golden_payload,
        "run_id": golden_run_id,
        "status_response": status_data,
        "trades": trades_data["trades"],
        "equity_curve": equity_data["equity_curve"],
        "provenance": audit_data,
    }
    with open(contracts_dir / "golden-backtest-run.json", "w", encoding="utf-8") as f:
        json.dump(golden_snapshot, f, indent=2)
    print(
        "   Frozen golden backtest saved: data/migration/contracts/golden-backtest-run.json"
    )

    # -------------------------------------------------------------------------
    # 7. Sweep & Compare Endpoints
    # -------------------------------------------------------------------------
    print("\n[7/8] Extracting Sweep & Compare Contracts...")
    sweep_fixtures = []

    sweep_req = {
        "start": "2020-06-01",
        "end": "2022-04-29",
        "symbols": ["ALPHA", "BETA", "GAMMA"],
        "base_config": {
            "corpus": 500000.0,
            "cost_bps": 10.0,
        },
        "param_grid": {
            "sl_pct": [0.05, 0.07],
            "risk_pct": [0.02],
        },
    }
    sweep_post = client.post("/api/v1/backtest/sweep", json=sweep_req)
    assert sweep_post.status_code == 202
    sweep_data = sweep_post.json()
    sweep_id = sweep_data["sweep_id"]
    sweep_fixtures.append(
        {
            "id": "backtest_sweep_create",
            "endpoint": "/api/v1/backtest/sweep",
            "method": "POST",
            "scenario": "Trigger parameter sweep permutation matrix",
            "request": {
                "url": "/api/v1/backtest/sweep",
                "headers": {"Content-Type": "application/json"},
                "body": sweep_req,
            },
            "response": {
                "status_code": 202,
                "headers": {"content-type": sweep_post.headers.get("content-type")},
                "body": sweep_data,
            },
        }
    )

    # GET /api/v1/backtest/sweep/{sweep_id}
    sweep_status = client.get(f"/api/v1/backtest/sweep/{sweep_id}")
    assert sweep_status.status_code == 200
    sweep_fixtures.append(
        {
            "id": "backtest_sweep_status",
            "endpoint": "/api/v1/backtest/sweep/{sweep_id}",
            "method": "GET",
            "scenario": "Get parameter sweep execution status and child runs",
            "request": {
                "url": f"/api/v1/backtest/sweep/{sweep_id}",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {"content-type": sweep_status.headers.get("content-type")},
                "body": sweep_status.json(),
            },
        }
    )

    # GET /api/v1/backtest/compare
    child_ids = sweep_data["run_ids"][:2]
    compare_res = client.get(f"/api/v1/backtest/compare?run_ids={','.join(child_ids)}")
    assert compare_res.status_code == 200
    sweep_fixtures.append(
        {
            "id": "backtest_compare_runs",
            "endpoint": "/api/v1/backtest/compare",
            "method": "GET",
            "scenario": "Compare performance metrics and overlaid equity curves across runs",
            "request": {
                "url": f"/api/v1/backtest/compare?run_ids={','.join(child_ids)}",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {"content-type": compare_res.headers.get("content-type")},
                "body_summary": {
                    "run_ids": compare_res.json()["run_ids"],
                    "runs_keys": list(compare_res.json()["runs"].keys()),
                },
            },
        }
    )

    with open(endpoints_dir / "sweep_and_compare.json", "w", encoding="utf-8") as f:
        json.dump(sweep_fixtures, f, indent=2)

    # -------------------------------------------------------------------------
    # 8. Reports & Validation Endpoints
    # -------------------------------------------------------------------------
    print("\n[8/8] Extracting Reports & Validation Contracts...")
    reports_fixtures = []

    # GET /api/v1/reports/{run_id}/summary
    rep_sum_res = client.get(f"/api/v1/reports/{golden_run_id}/summary")
    assert rep_sum_res.status_code == 200
    assert rep_sum_res.json()["metrics"]["final_capital"] == 482707.20
    reports_fixtures.append(
        {
            "id": "reports_summary_metrics",
            "endpoint": "/api/v1/reports/{run_id}/summary",
            "method": "GET",
            "scenario": "Comprehensive performance analytics and return metrics (INV-10)",
            "invariants": ["INV-10"],
            "request": {
                "url": f"/api/v1/reports/{golden_run_id}/summary",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {"content-type": rep_sum_res.headers.get("content-type")},
                "body": rep_sum_res.json(),
            },
        }
    )

    # GET /api/v1/reports/{run_id}/monthly
    rep_month_res = client.get(f"/api/v1/reports/{golden_run_id}/monthly")
    assert rep_month_res.status_code == 200
    reports_fixtures.append(
        {
            "id": "reports_monthly_matrix",
            "endpoint": "/api/v1/reports/{run_id}/monthly",
            "method": "GET",
            "scenario": "Month x Year compounded returns matrix",
            "request": {
                "url": f"/api/v1/reports/{golden_run_id}/monthly",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {"content-type": rep_month_res.headers.get("content-type")},
                "body": rep_month_res.json(),
            },
        }
    )

    # GET /api/v1/reports/{run_id}/export?format=csv
    csv_res = client.get(f"/api/v1/reports/{golden_run_id}/export?format=csv")
    assert csv_res.status_code == 200
    reports_fixtures.append(
        {
            "id": "reports_export_csv",
            "endpoint": "/api/v1/reports/{run_id}/export",
            "method": "GET",
            "scenario": "Export trade ledger as CSV attachment",
            "request": {
                "url": f"/api/v1/reports/{golden_run_id}/export?format=csv",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {
                    "content-type": csv_res.headers.get("content-type"),
                    "content-disposition": csv_res.headers.get("content-disposition"),
                },
                "body": csv_res.text,
            },
        }
    )

    # GET /api/v1/reports/{run_id}/export?format=xlsx
    xlsx_res = client.get(f"/api/v1/reports/{golden_run_id}/export?format=xlsx")
    assert xlsx_res.status_code == 200
    reports_fixtures.append(
        {
            "id": "reports_export_xlsx",
            "endpoint": "/api/v1/reports/{run_id}/export",
            "method": "GET",
            "scenario": "Export metrics and trades workbook as Excel (.xlsx)",
            "request": {
                "url": f"/api/v1/reports/{golden_run_id}/export?format=xlsx",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {
                    "content-type": xlsx_res.headers.get("content-type"),
                    "content-disposition": xlsx_res.headers.get("content-disposition"),
                },
                "is_binary": True,
                "binary_sha256": _hash_bytes(xlsx_res.content),
                "byte_size": len(xlsx_res.content),
            },
        }
    )

    # GET /api/v1/reports/{run_id}/export?format=zip
    zip_res = client.get(f"/api/v1/reports/{golden_run_id}/export?format=zip")
    assert zip_res.status_code == 200
    reports_fixtures.append(
        {
            "id": "reports_export_zip",
            "endpoint": "/api/v1/reports/{run_id}/export",
            "method": "GET",
            "scenario": "Export multi-CSV bundle archive (.zip)",
            "request": {
                "url": f"/api/v1/reports/{golden_run_id}/export?format=zip",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {
                    "content-type": zip_res.headers.get("content-type"),
                    "content-disposition": zip_res.headers.get("content-disposition"),
                },
                "is_binary": True,
                "binary_sha256": _hash_bytes(zip_res.content),
                "byte_size": len(zip_res.content),
            },
        }
    )

    # GET /api/v1/reports/{run_id}/export?format=pdf (sync for small trades)
    pdf_res = client.get(f"/api/v1/reports/{golden_run_id}/export?format=pdf")
    assert pdf_res.status_code == 200
    reports_fixtures.append(
        {
            "id": "reports_export_pdf_sync",
            "endpoint": "/api/v1/reports/{run_id}/export",
            "method": "GET",
            "scenario": "Export print-ready tear sheet PDF for <=2000 trades",
            "request": {
                "url": f"/api/v1/reports/{golden_run_id}/export?format=pdf",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {
                    "content-type": pdf_res.headers.get("content-type"),
                    "content-disposition": pdf_res.headers.get("content-disposition"),
                },
                "is_binary": True,
                "byte_size": len(pdf_res.content),
                "starts_with_pdf_magic": pdf_res.content.startswith(b"%PDF"),
            },
        }
    )

    # POST /api/v1/reports/{run_id}/export/pdf/async
    async_pdf_res = client.post(f"/api/v1/reports/{golden_run_id}/export/pdf/async")
    assert async_pdf_res.status_code == 202
    async_pdf_data = async_pdf_res.json()
    job_id = async_pdf_data["job_id"]
    reports_fixtures.append(
        {
            "id": "reports_export_pdf_async",
            "endpoint": "/api/v1/reports/{run_id}/export/pdf/async",
            "method": "POST",
            "scenario": "Explicit asynchronous PDF dispatch (REQ-9.4)",
            "request": {
                "url": f"/api/v1/reports/{golden_run_id}/export/pdf/async",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 202,
                "headers": {
                    "content-type": async_pdf_res.headers.get("content-type"),
                    "location": async_pdf_res.headers.get("location"),
                },
                "body": async_pdf_data,
            },
        }
    )

    # GET /api/v1/reports/jobs/{job_id}
    job_res = client.get(f"/api/v1/reports/jobs/{job_id}")
    assert job_res.status_code == 200
    job_data = job_res.json()
    reports_fixtures.append(
        {
            "id": "reports_job_status",
            "endpoint": "/api/v1/reports/jobs/{job_id}",
            "method": "GET",
            "scenario": "Async PDF generation job status",
            "request": {
                "url": f"/api/v1/reports/jobs/{job_id}",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {"content-type": job_res.headers.get("content-type")},
                "body": job_data,
            },
        }
    )

    # GET /api/v1/reports/jobs/{job_id}/download (when ready)
    job_dl_res = client.get(f"/api/v1/reports/jobs/{job_id}/download")
    assert job_dl_res.status_code == 200
    reports_fixtures.append(
        {
            "id": "reports_job_download",
            "endpoint": "/api/v1/reports/jobs/{job_id}/download",
            "method": "GET",
            "scenario": "Stream completed PDF report",
            "request": {
                "url": f"/api/v1/reports/jobs/{job_id}/download",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {
                    "content-type": job_dl_res.headers.get("content-type"),
                    "content-disposition": job_dl_res.headers.get(
                        "content-disposition"
                    ),
                },
                "is_binary": True,
                "byte_size": len(job_dl_res.content),
                "starts_with_pdf_magic": job_dl_res.content.startswith(b"%PDF"),
            },
        }
    )

    # GET /api/v1/reports/{run_id}/preview.png
    preview_res = client.get(f"/api/v1/reports/{golden_run_id}/preview.png")
    assert preview_res.status_code == 200
    reports_fixtures.append(
        {
            "id": "reports_preview_png",
            "endpoint": "/api/v1/reports/{run_id}/preview.png",
            "method": "GET",
            "scenario": "Render first page of PDF tear sheet as PNG preview",
            "request": {
                "url": f"/api/v1/reports/{golden_run_id}/preview.png",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {"content-type": preview_res.headers.get("content-type")},
                "is_binary": True,
                "byte_size": len(preview_res.content),
                "starts_with_png_magic": preview_res.content.startswith(
                    b"\x89PNG\r\n\x1a\n"
                ),
            },
        }
    )

    with open(endpoints_dir / "reports.json", "w", encoding="utf-8") as f:
        json.dump(reports_fixtures, f, indent=2)

    # Validation Endpoints
    val_fixtures = []
    # GET /api/v1/validation/{run_id}/{symbol} (JSON)
    val_res = client.get(f"/api/v1/validation/{golden_run_id}/ALPHA")
    assert val_res.status_code == 200
    val_data = val_res.json()
    val_fixtures.append(
        {
            "id": "validation_cross_check_json",
            "endpoint": "/api/v1/validation/{run_id}/{symbol}",
            "method": "GET",
            "scenario": "TradingView cross-check time series comparison data (REQ-8.1)",
            "request": {
                "url": f"/api/v1/validation/{golden_run_id}/ALPHA",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {"content-type": val_res.headers.get("content-type")},
                "body_summary": {
                    "run_id": val_data["run_id"],
                    "symbol": val_data["symbol"],
                    "count": val_data["count"],
                    "sample_point": val_data["rows"][-1],
                },
            },
        }
    )

    # GET /api/v1/validation/{run_id}/{symbol}?format=csv
    val_csv_res = client.get(f"/api/v1/validation/{golden_run_id}/ALPHA?format=csv")
    assert val_csv_res.status_code == 200
    val_fixtures.append(
        {
            "id": "validation_cross_check_csv",
            "endpoint": "/api/v1/validation/{run_id}/{symbol}",
            "method": "GET",
            "scenario": "TradingView cross-check raw CSV attachment",
            "request": {
                "url": f"/api/v1/validation/{golden_run_id}/ALPHA?format=csv",
                "headers": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {
                    "content-type": val_csv_res.headers.get("content-type"),
                    "content-disposition": val_csv_res.headers.get(
                        "content-disposition"
                    ),
                },
                "body": val_csv_res.text[:500] + "\n...",
            },
        }
    )

    with open(endpoints_dir / "validation.json", "w", encoding="utf-8") as f:
        json.dump(val_fixtures, f, indent=2)

    # -------------------------------------------------------------------------
    # 9. Reports Not Ready Protocol Fixtures
    # -------------------------------------------------------------------------
    print("\n[9/9] Extracting 'Reports Not Ready' & Edge Case Contract Fixtures...")
    not_ready_fixtures = []

    unknown_id = "run_nonexistent_99999"

    # 404 on unknown run
    endpoints_404 = [
        f"/api/v1/backtest/{unknown_id}",
        f"/api/v1/backtest/{unknown_id}/trades",
        f"/api/v1/backtest/{unknown_id}/equity",
        f"/api/v1/backtest/{unknown_id}/audit",
        f"/api/v1/reports/{unknown_id}/summary",
        f"/api/v1/reports/{unknown_id}/monthly",
        f"/api/v1/reports/{unknown_id}/export?format=csv",
        f"/api/v1/reports/{unknown_id}/export?format=pdf",
        f"/api/v1/reports/{unknown_id}/preview.png",
        f"/api/v1/validation/{unknown_id}/ALPHA",
    ]
    for ep in endpoints_404:
        r404 = client.get(ep)
        assert r404.status_code == 404, f"Expected 404 for {ep}, got {r404.status_code}"
        not_ready_fixtures.append(
            {
                "id": f"not_ready_unknown_{ep.split('/')[-1]}",
                "endpoint": ep,
                "method": "GET",
                "scenario": f"Unknown run_id returns 404: {ep}",
                "request": {"url": ep, "headers": {}, "body": None},
                "response": {"status_code": 404, "body": r404.json()},
            }
        )

    # Seed an incomplete/running run record into DB
    pending_run_id = "run_sim_pending_extract"
    with Session(engine) as session:
        pending_record = BacktestRun(
            id=pending_run_id,
            status="running",
            created_at=datetime.now(UTC).isoformat(),
            config_version="1.0",
            initial_capital=500000.0,
        )
        session.merge(pending_record)
        session.commit()

    # Incomplete run behaviors
    # 400 Bad Request on summary, monthly, export(csv)
    for sub in ["summary", "monthly", "export?format=csv"]:
        r_pend = client.get(f"/api/v1/reports/{pending_run_id}/{sub}")
        assert r_pend.status_code == 400
        not_ready_fixtures.append(
            {
                "id": f"not_ready_incomplete_reports_{sub.split('?')[0]}",
                "endpoint": f"/api/v1/reports/{{run_id}}/{sub}",
                "method": "GET",
                "scenario": f"Incomplete/running run returns 400 for {sub}",
                "request": {
                    "url": f"/api/v1/reports/{pending_run_id}/{sub}",
                    "headers": {},
                    "body": None,
                },
                "response": {"status_code": 400, "body": r_pend.json()},
            }
        )

    # 422 Unprocessable Content on export?format=pdf, export/pdf/async, preview.png
    r_pdf_422 = client.get(f"/api/v1/reports/{pending_run_id}/export?format=pdf")
    assert r_pdf_422.status_code == 422
    not_ready_fixtures.append(
        {
            "id": "not_ready_incomplete_export_pdf",
            "endpoint": "/api/v1/reports/{run_id}/export?format=pdf",
            "method": "GET",
            "scenario": "Incomplete/running run returns 422 for synchronous PDF export",
            "request": {
                "url": f"/api/v1/reports/{pending_run_id}/export?format=pdf",
                "headers": {},
                "body": None,
            },
            "response": {"status_code": 422, "body": r_pdf_422.json()},
        }
    )

    r_async_422 = client.post(f"/api/v1/reports/{pending_run_id}/export/pdf/async")
    assert r_async_422.status_code == 422
    not_ready_fixtures.append(
        {
            "id": "not_ready_incomplete_export_pdf_async",
            "endpoint": "/api/v1/reports/{run_id}/export/pdf/async",
            "method": "POST",
            "scenario": "Incomplete/running run returns 422 for async PDF export trigger",
            "request": {
                "url": f"/api/v1/reports/{pending_run_id}/export/pdf/async",
                "headers": {},
                "body": None,
            },
            "response": {"status_code": 422, "body": r_async_422.json()},
        }
    )

    r_prev_422 = client.get(f"/api/v1/reports/{pending_run_id}/preview.png")
    assert r_prev_422.status_code == 422
    not_ready_fixtures.append(
        {
            "id": "not_ready_incomplete_preview_png",
            "endpoint": "/api/v1/reports/{run_id}/preview.png",
            "method": "GET",
            "scenario": "Incomplete/running run returns 422 for preview PNG",
            "request": {
                "url": f"/api/v1/reports/{pending_run_id}/preview.png",
                "headers": {},
                "body": None,
            },
            "response": {"status_code": 422, "body": r_prev_422.json()},
        }
    )

    # Empty 200 responses for trades and equity when run is incomplete
    r_tr_pend = client.get(f"/api/v1/backtest/{pending_run_id}/trades")
    assert r_tr_pend.status_code == 200 and r_tr_pend.json()["count"] == 0
    not_ready_fixtures.append(
        {
            "id": "not_ready_incomplete_trades_empty",
            "endpoint": "/api/v1/backtest/{run_id}/trades",
            "method": "GET",
            "scenario": "Incomplete run returns 200 with empty trades list",
            "request": {
                "url": f"/api/v1/backtest/{pending_run_id}/trades",
                "headers": {},
                "body": None,
            },
            "response": {"status_code": 200, "body": r_tr_pend.json()},
        }
    )

    r_eq_pend = client.get(f"/api/v1/backtest/{pending_run_id}/equity")
    assert r_eq_pend.status_code == 200 and r_eq_pend.json()["count"] == 0
    not_ready_fixtures.append(
        {
            "id": "not_ready_incomplete_equity_empty",
            "endpoint": "/api/v1/backtest/{run_id}/equity",
            "method": "GET",
            "scenario": "Incomplete run returns 200 with empty equity list",
            "request": {
                "url": f"/api/v1/backtest/{pending_run_id}/equity",
                "headers": {},
                "body": None,
            },
            "response": {"status_code": 200, "body": r_eq_pend.json()},
        }
    )

    # 409 Conflict on downloading a pending job
    dummy_job = job_manager.create_job("run_dummy_job_test")
    r_job_dl = client.get(f"/api/v1/reports/jobs/{dummy_job.job_id}/download")
    assert r_job_dl.status_code == 409
    not_ready_fixtures.append(
        {
            "id": "not_ready_job_download_conflict_409",
            "endpoint": "/api/v1/reports/jobs/{job_id}/download",
            "method": "GET",
            "scenario": "Attempting download on pending PDF job returns 409 Conflict",
            "request": {
                "url": f"/api/v1/reports/jobs/{dummy_job.job_id}/download",
                "headers": {},
                "body": None,
            },
            "response": {"status_code": 409, "body": r_job_dl.json()},
        }
    )

    with open(endpoints_dir / "reports_not_ready.json", "w", encoding="utf-8") as f:
        json.dump(not_ready_fixtures, f, indent=2)

    print("\n" + "=" * 70)
    print("Contract Extraction Completed Successfully!")
    print(f"Contracts written to: {contracts_dir}")
    print("=" * 70)


if __name__ == "__main__":
    run_extraction()
