#!/usr/bin/env bash
# ====================================================================
# EquiTest NSE - PostgreSQL 16 Multi-Database Initialization
# Creates 5 isolated logical databases for microservice boundaries
# ====================================================================
set -e

DATABASES=(
    "equitest_data"
    "equitest_engine"
    "equitest_sweep"
    "equitest_reports"
    "equitest_validation"
)

echo "==> Initializing EquiTest logical databases..."

for db in "${DATABASES[@]}"; do
    echo "==> Checking database: $db"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        SELECT 'CREATE DATABASE $db'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
        GRANT ALL PRIVILEGES ON DATABASE $db TO $POSTGRES_USER;
EOSQL
    echo "==> Database '$db' ready."
done

echo "==> All 5 logical databases successfully provisioned."
