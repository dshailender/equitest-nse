import argparse
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import HealthResponse, api_router
from app.core.config import settings
from app.core.logging import RequestIdLoggingMiddleware, setup_logging
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup structured logging
    setup_logging(settings.LOG_LEVEL)
    # Initialize DB (creates SQLite tables if defined)
    init_db()
    # Enforce backtest retention policy at startup
    try:
        from sqlmodel import Session

        from app.db.session import engine
        from app.engine.retention import enforce_backtest_retention

        with Session(engine) as session:
            enforce_backtest_retention(session)
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning(
            "Startup retention enforcement failed: %s", exc
        )
    yield


def create_app() -> FastAPI:
    """Factory creating and configuring the FastAPI application instance."""
    app = FastAPI(
        title="EquiTest NSE Backtesting API",
        description="Quantitative backtesting framework backend for Indian equities",
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # CORS configuration
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID and structured logging middleware
    app.add_middleware(RequestIdLoggingMiddleware)

    # Root health endpoint
    @app.get(
        "/health",
        response_model=HealthResponse,
        summary="Service Health Check",
        description="Returns service operational status and version",
        tags=["health"],
    )
    async def root_health() -> HealthResponse:
        return HealthResponse(status="ok", version=settings.APP_VERSION)

    # Mount versioned API routes
    app.include_router(api_router)

    return app


app = create_app()


def export_openapi(dest_path: Path | str) -> None:
    """Export the OpenAPI schema to the target JSON path."""
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print(f"OpenAPI schema successfully exported to {dest}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EquiTest NSE Backend CLI")
    parser.add_argument(
        "--export-openapi",
        type=str,
        help="Export OpenAPI JSON schema to specified path and exit",
    )
    args = parser.parse_args()

    if args.export_openapi:
        export_openapi(args.export_openapi)
    else:
        import uvicorn

        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
