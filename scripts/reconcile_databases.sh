#!/usr/bin/env bash
# scripts/reconcile_databases.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DB="$REPO_ROOT/dev.db"
BACKEND_DB="$REPO_ROOT/backend/dev.db"

echo "==> Reconciling root dev.db and backend/dev.db..."

python3 - <<EOF
import sqlite3
from pathlib import Path

root_db = Path("$ROOT_DB")
backend_db = Path("$BACKEND_DB")

# If both exist, merge backend/dev.db runs into root dev.db if missing
if backend_db.exists() and root_db.exists():
    print("Both databases exist. Checking for unique runs in backend/dev.db...")
    conn_root = sqlite3.connect(root_db)
    conn_backend = sqlite3.connect(backend_db)

    cur_b = conn_backend.cursor()
    cur_r = conn_root.cursor()

    cur_r.execute("SELECT id FROM backtest_runs")
    root_ids = {row[0] for row in cur_r.fetchall()}

    cur_b.execute("SELECT * FROM backtest_runs")
    backend_rows = cur_b.fetchall()

    # Get column names
    col_names = [d[0] for d in cur_b.description]
    placeholders = ",".join(["?"] * len(col_names))

    inserted = 0
    for row in backend_rows:
        run_id = row[0]
        if run_id not in root_ids:
            try:
                cur_r.execute(
                    f"INSERT OR IGNORE INTO backtest_runs ({','.join(col_names)}) VALUES ({placeholders})",
                    row,
                )
                inserted += 1
            except Exception as e:
                pass

    conn_root.commit()
    conn_root.close()
    conn_backend.close()
    print(f"Merged {inserted} additional run records from backend/dev.db into dev.db.")

    # Remove backend/dev.db to prevent future divergence
    backend_db.unlink()
    print("Removed duplicate backend/dev.db.")

# Vacuum and shrink root_db
if root_db.exists():
    conn = sqlite3.connect(root_db)
    print("Vacuuming dev.db to reclaim free disk pages...")
    conn.execute("VACUUM;")
    conn.close()
    print("Database compacted successfully.")
EOF
