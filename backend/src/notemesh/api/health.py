"""Health check API endpoints."""

from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db_session
from ..core.services import HealthService
from ..core.schemas.common import HealthCheckResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthCheckResponse)
async def health_check(session: AsyncSession = Depends(get_db_session)):
    """Get overall system health status."""
    health_service = HealthService(session)
    return await health_service.get_health_status()


@router.get("/database", response_model=Dict[str, Any])
async def database_health(session: AsyncSession = Depends(get_db_session)):
    """Check database connectivity."""
    health_service = HealthService(session)
    return await health_service.check_database_health()


@router.get("/redis", response_model=Dict[str, Any])
async def redis_health(session: AsyncSession = Depends(get_db_session)):
    """Check Redis connectivity."""
    health_service = HealthService(session)
    return await health_service.check_redis_health()


@router.get("/metrics", response_model=Dict[str, Any])
async def system_metrics(session: AsyncSession = Depends(get_db_session)):
    """Get system metrics."""
    health_service = HealthService(session)
    return await health_service.get_system_metrics()