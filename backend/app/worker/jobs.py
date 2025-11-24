"""arq worker configuration for ingestion jobs."""

from backend.app.services.tasks import run_ingestion_job


async def ingestion_job(ctx, document_id: str) -> None:
    """Entrypoint executed by the arq worker."""
    run_ingestion_job(document_id=document_id)


class WorkerSettings:
    functions = [ingestion_job]
    max_jobs = 1

