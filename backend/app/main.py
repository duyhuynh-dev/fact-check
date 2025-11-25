from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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

    # Serve frontend static files
    frontend_path = Path(__file__).parent.parent.parent / "frontend"
    if frontend_path.exists():
        # Serve CSS and JS files
        app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

        @app.get("/")
        async def serve_frontend():
            """Serve the frontend index page."""
            index_path = frontend_path / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            return {"message": "Frontend not found"}

        # Serve CSS and JS directly
        @app.get("/styles.css")
        async def serve_css():
            css_path = frontend_path / "styles.css"
            if css_path.exists():
                return FileResponse(str(css_path), media_type="text/css")
            return {"error": "CSS not found"}

        @app.get("/app.js")
        async def serve_js():
            js_path = frontend_path / "app.js"
            if js_path.exists():
                return FileResponse(str(js_path), media_type="application/javascript")
            return {"error": "JS not found"}

    return app


app = create_app()

