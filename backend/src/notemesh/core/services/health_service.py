"""Health service implementation."""

import asyncio
from datetime import datetime
from typing import Any, Dict

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import get_settings
from ..schemas.common import HealthCheckResponse
from .interfaces import IHealthService


class HealthService(IHealthService):
    """Health check service implementation."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()

    async def get_health_status(self) -> HealthCheckResponse:
        """Get app health status."""
        db_health = await self.check_database_health()
        redis_health = await self.check_redis_health()

        overall_status = "healthy"
        if not db_health["connected"] or not redis_health["connected"]:
            overall_status = "unhealthy"

        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version="0.1.0",
            checks={"database": db_health, "redis": redis_health},
        )

    async def check_database_health(self) -> Dict[str, Any]:
        """Check DB connection."""
        try:
            # Measure response time
            start_time = asyncio.get_event_loop().time()
            result = await self.session.execute(text("SELECT 1"))
            result.scalar()
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000

            return {
                "connected": True,
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
            }
        except Exception as e:
            return {
                "connected": False,
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": 0.0,
            }

    async def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connection."""
        try:
            # Create Redis connection
            r = redis.from_url(self.settings.redis_url)

            # Test connection with ping
            start_time = asyncio.get_event_loop().time()
            await r.ping()
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000

            await r.aclose()

            return {
                "connected": True,
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
            }
        except Exception as e:
            return {
                "connected": False,
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": None,
            }

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics."""
        # Basic system metrics
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": None,  # Could be implemented
            "memory_usage_mb": None,  # Could be implemented
            "cpu_usage_percent": None,  # Could be implemented
            "active_connections": None,  # Could be implemented
        }
