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
        """Enqueue job - run in background thread to avoid blocking."""
        import asyncio
        import logging
        import concurrent.futures
        logger = logging.getLogger(__name__)
        
        # Run the sync function in a thread pool to avoid blocking
        # Use a separate executor to prevent blocking the event loop
        loop = asyncio.get_event_loop()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        def run_job():
            try:
                run_ingestion_job(document_id)
                logger.info(f"Job completed for document {document_id}")
            except Exception as e:
                logger.error(f"Job failed for document {document_id}: {str(e)}", exc_info=True)
                # Update document status to failed
                try:
                    from backend.app.db.session import get_engine
                    from backend.app.db.models import Document
                    from sqlmodel import Session
                    with Session(get_engine()) as session:
                        doc = session.get(Document, document_id)
                        if doc:
                            doc.ingest_status = "failed"
                            doc.ingest_failure_reason = str(e)
                            session.add(doc)
                            session.commit()
                except Exception as db_error:
                    logger.error(f"Failed to update document status: {str(db_error)}")
        
        # Fire and forget - don't wait for completion
        loop.run_in_executor(executor, run_job)
        logger.info(f"Job enqueued (background) for document {document_id}")


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

