from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.db.session import init_db
from backend.app.routes.documents import router as documents_router
from backend.app.routes.evidence import router as evidence_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    """Application factory to keep wiring testable."""
    app = FastAPI(
        title="Antisemitism Fact-Check API",
        version="0.1.0",
        description="Prototype API for ingestion, retrieval, and verification services.",
        lifespan=lifespan,
    )

    @app.get("/healthz", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(documents_router)
    app.include_router(evidence_router)

    return app


app = create_app()

