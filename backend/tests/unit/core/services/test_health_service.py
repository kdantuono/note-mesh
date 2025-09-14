import asyncio
import types
import pytest

from src.notemesh.core.services.health_service import HealthService


class FakeScalarResult:
    def __init__(self, scalar_value):
        self._scalar_value = scalar_value
    def scalar(self):
        return self._scalar_value


class FakeSession:
    def __init__(self, ok=True):
        self.ok = ok
        self.executed = []
    async def execute(self, stmt):
        self.executed.append(stmt)
        if self.ok:
            return FakeScalarResult(1)
        raise RuntimeError("db down")


class DummyRedis:
    def __init__(self, ok=True, delay=0):
        self.ok = ok
        self.delay = delay
        self.closed = False
        self.pings = 0
    async def ping(self):
        self.pings += 1
        if self.delay:
            await asyncio.sleep(0)
        if not self.ok:
            raise RuntimeError("redis down")
        return True
    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_get_health_status_all_ok(monkeypatch):
    session = FakeSession(ok=True)
    svc = HealthService(session)

    # Patch redis.from_url to return DummyRedis
    import src.notemesh.core.services.health_service as hs
    monkeypatch.setattr(hs.redis, "from_url", lambda url: DummyRedis(ok=True), raising=True)

    resp = await svc.get_health_status()
    assert resp.status == "healthy"
    assert resp.checks["database"]["connected"] is True
    assert resp.checks["redis"]["connected"] is True


@pytest.mark.asyncio
async def test_get_health_status_db_down(monkeypatch):
    session = FakeSession(ok=False)
    svc = HealthService(session)

    import src.notemesh.core.services.health_service as hs
    monkeypatch.setattr(hs.redis, "from_url", lambda url: DummyRedis(ok=True), raising=True)

    resp = await svc.get_health_status()
    assert resp.status == "unhealthy"
    assert resp.checks["database"]["connected"] is False
    assert resp.checks["redis"]["connected"] is True


@pytest.mark.asyncio
async def test_get_health_status_redis_down(monkeypatch):
    session = FakeSession(ok=True)
    svc = HealthService(session)

    import src.notemesh.core.services.health_service as hs
    monkeypatch.setattr(hs.redis, "from_url", lambda url: DummyRedis(ok=False), raising=True)

    resp = await svc.get_health_status()
    assert resp.status == "unhealthy"
    assert resp.checks["database"]["connected"] is True
    assert resp.checks["redis"]["connected"] is False
