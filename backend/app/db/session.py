from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# SQLite requires check_same_thread=False when used across threads in FastAPI
connect_args = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)


def init_db() -> None:
    """Initialize database tables for SQLModel metadata."""
    from sqlalchemy import text

    from app.db import models  # noqa: F401

    SQLModel.metadata.create_all(engine)

    # Lightweight migration for existing SQLite databases
    with engine.connect() as conn:
        cursor = conn.connection.cursor()
        cursor.execute("PRAGMA table_info(backtest_runs)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        if existing_cols:
            if "config_version" not in existing_cols:
                conn.execute(
                    text(
                        "ALTER TABLE backtest_runs ADD COLUMN config_version "
                        "VARCHAR DEFAULT '1.0'"
                    )
                )
            if "sweep_id" not in existing_cols:
                conn.execute(
                    text("ALTER TABLE backtest_runs ADD COLUMN sweep_id VARCHAR")
                )
            if "cagr" not in existing_cols:
                conn.execute(text("ALTER TABLE backtest_runs ADD COLUMN cagr FLOAT"))
            if "max_drawdown_pct" not in existing_cols:
                conn.execute(
                    text("ALTER TABLE backtest_runs ADD COLUMN max_drawdown_pct FLOAT")
                )
            conn.commit()

        # Seed price coverage database if not already populated (AUD-E-001)
        cursor.execute("SELECT count(DISTINCT symbol) FROM prices")
        sym_count = cursor.fetchone()[0]
        if sym_count < 650:
            from app.data.ingest import seed_price_coverage

            seed_price_coverage(conn.connection)


def get_session() -> Generator[Session, None, None]:
    """Dependency generator that yields a database session."""
    with Session(engine) as session:
        yield session
