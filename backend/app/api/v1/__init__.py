from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import settings


class HealthResponse(BaseModel):
    status: str = Field(
        default="ok", description="Operational status of the service", examples=["ok"]
    )
    version: str = Field(
        default="0.1.0", description="Semantic application version", examples=["0.1.0"]
    )


api_router = APIRouter(prefix="/api/v1")


@api_router.get(
    "/health",
    response_model=HealthResponse,
    summary="API v1 Health Check",
    description="Returns the current operational status and version of the API.",
    tags=["health"],
)
async def api_v1_health() -> HealthResponse:
    return HealthResponse(status="ok", version=settings.APP_VERSION)


from app.api.v1.backtest import router as backtest_router  # noqa: E402
from app.api.v1.data import router as data_router  # noqa: E402
from app.api.v1.indicators import router as indicators_router  # noqa: E402
from app.api.v1.reports import router as reports_router  # noqa: E402
from app.api.v1.risk import router as risk_router  # noqa: E402
from app.api.v1.signals import router as signals_router  # noqa: E402
from app.api.v1.validation import router as validation_router  # noqa: E402

api_router.include_router(data_router)
api_router.include_router(indicators_router)
api_router.include_router(signals_router)
api_router.include_router(risk_router)
api_router.include_router(backtest_router)
api_router.include_router(reports_router)
api_router.include_router(validation_router)

