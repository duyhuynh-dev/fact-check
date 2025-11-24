from fastapi import FastAPI

from backend.app.db.session import init_db


def create_app() -> FastAPI:
    """Application factory to keep wiring testable."""
    app = FastAPI(
        title="Antisemitism Fact-Check API",
        version="0.1.0",
        description="Prototype API for ingestion, retrieval, and verification services.",
    )

    @app.on_event("startup")
    async def on_startup() -> None:
        init_db()

    @app.get("/healthz", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

