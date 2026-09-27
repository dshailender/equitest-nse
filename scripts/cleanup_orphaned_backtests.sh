#!/usr/bin/env bash
# scripts/cleanup_orphaned_backtests.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${1:-$REPO_ROOT/dev.db}"

echo "==> Auditing backtest storage using database: $DB_PATH"

python3 - <<EOF
import sqlite3
import os
from pathlib import Path

repo_root = Path("$REPO_ROOT")
db_path = Path("$DB_PATH")
backtests_dir = repo_root / "data" / "backtests"
reports_dir = repo_root / "data" / "reports"

if not db_path.exists():
    print(f"Error: Database {db_path} does not exist.")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 1. Fetch valid IDs
cur.execute("SELECT id FROM backtest_runs")
valid_ids = {row[0] for row in cur.fetchall()}
print(f"Found {len(valid_ids)} registered run IDs in database.")

# 2. Scan data/backtests
deleted_json = 0
deleted_audit = 0
retained_json = 0

if backtests_dir.exists():
    for file_path in backtests_dir.glob("*.json"):
        filename = file_path.name
        if filename.endswith("_audit.json"):
            run_id = filename[:-11]
            if run_id not in valid_ids:
                file_path.unlink()
                deleted_audit += 1
        else:
            run_id = filename[:-5]
            if run_id not in valid_ids:
                file_path.unlink()
                deleted_json += 1
            else:
                retained_json += 1

# 3. Scan data/reports
deleted_pdf = 0
if reports_dir.exists():
    for pdf_path in reports_dir.glob("backtest_*.pdf"):
        run_id = pdf_path.stem.replace("backtest_", "")
        if run_id not in valid_ids:
            pdf_path.unlink()
            deleted_pdf += 1

print(f"Cleanup Completed:")
print(f"  - Deleted {deleted_json} orphaned result JSON files")
print(f"  - Deleted {deleted_audit} orphaned audit JSON files")
print(f"  - Deleted {deleted_pdf} orphaned PDF reports")
print(f"  - Retained {retained_json} valid run artifacts")
EOF
