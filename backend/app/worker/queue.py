"""Job queue abstractions for ingestion work."""

from __future__ import annotations

from typing import Protocol

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings

from backend.app.core.config import get_settings
from backend.app.services.tasks import run_ingestion_job


class JobQueue(Protocol):
    async def enqueue(self, document_id: str) -> None: ...


class SyncJobQueue:
    """Simple queue that runs jobs inline (default dev/test behavior)."""

    async def enqueue(self, document_id: str) -> None:
        run_ingestion_job(document_id)


class ArqJobQueue:
    """Redis-backed queue powered by arq."""

    def __init__(self, redis_settings: RedisSettings):
        self.redis_settings = redis_settings
        self._pool: ArqRedis | None = None

    async def _get_pool(self) -> ArqRedis:
        if self._pool is None:
            self._pool = await create_pool(self.redis_settings)
        return self._pool

    async def enqueue(self, document_id: str) -> None:
        pool = await self._get_pool()
        await pool.enqueue_job("ingestion_job", document_id=document_id)


def resolve_job_queue() -> JobQueue:
    settings = get_settings()
    if settings.queue_backend.lower() == "arq":
        if not settings.redis_dsn:
            raise RuntimeError("REDIS_DSN must be set when QUEUE_BACKEND=arq")
        redis_settings = RedisSettings.from_dsn(settings.redis_dsn)
        return ArqJobQueue(redis_settings)
    return SyncJobQueue()

