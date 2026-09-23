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


from app.api.v1.data import router as data_router  # noqa: E402

api_router.include_router(data_router)
