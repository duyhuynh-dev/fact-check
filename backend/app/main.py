import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.db.session import init_db
from backend.app.routes.documents import router as documents_router
from backend.app.routes.evidence import router as evidence_router

logger = logging.getLogger(__name__)


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
    
    @app.get("/debug/paths", tags=["debug"])
    async def debug_paths() -> dict:
        """Debug endpoint to check filesystem paths."""
        import os
        current_dir = Path.cwd()
        main_file = Path(__file__)
        possible_frontend_paths = [
            main_file.parent.parent.parent / "frontend",
            Path("/app/frontend"),
            Path("frontend"),
        ]
        
        results = {
            "current_dir": str(current_dir),
            "__file__": str(main_file),
            "paths_checked": [],
            "root_contents": []
        }
        
        # Check root directory contents
        try:
            root_path = Path("/app") if Path("/app").exists() else current_dir
            if root_path.exists():
                results["root_contents"] = [item.name for item in root_path.iterdir() if item.is_dir() or item.name.endswith(('.html', '.css', '.js'))]
        except Exception as e:
            results["root_contents_error"] = str(e)
        
        # Check each possible frontend path
        for path in possible_frontend_paths:
            abs_path = path.resolve() if path.is_absolute() else current_dir / path
            exists = abs_path.exists()
            has_index = (abs_path / "index.html").exists() if exists else False
            results["paths_checked"].append({
                "path": str(path),
                "resolved": str(abs_path),
                "exists": exists,
                "has_index.html": has_index,
                "contents": list(abs_path.iterdir()) if exists and abs_path.is_dir() else []
            })
        
        return results

    app.include_router(documents_router)
    app.include_router(evidence_router)

    # Serve frontend static files
    # Try multiple paths to find frontend (works in both local and Docker)
    possible_paths = [
        Path(__file__).parent.parent.parent / "frontend",  # Local development: backend/app/main.py -> backend -> project root -> frontend
        Path("/app/frontend"),  # Docker container (WORKDIR is /app)
        Path("frontend"),  # Relative to working directory
    ]
    
    frontend_path = None
    for path in possible_paths:
        abs_path = path.resolve() if path.is_absolute() else Path.cwd() / path
        logger.info(f"Checking frontend path: {abs_path} (exists: {abs_path.exists()})")
        if abs_path.exists() and (abs_path / "index.html").exists():
            frontend_path = abs_path
            logger.info(f"Found frontend at: {frontend_path}")
            break
    
    if frontend_path:
        # Serve CSS and JS files
        app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

        @app.get("/")
        async def serve_frontend():
            """Serve the frontend index page."""
            index_path = frontend_path / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            logger.error(f"Frontend index.html not found at {index_path}")
            return {"message": f"Frontend not found at {index_path}", "checked_paths": [str(p) for p in possible_paths]}

        # Serve CSS and JS directly
        @app.get("/styles.css")
        async def serve_css():
            css_path = frontend_path / "styles.css"
            if css_path.exists():
                return FileResponse(str(css_path), media_type="text/css")
            return {"error": f"CSS not found at {css_path}"}

        @app.get("/app.js")
        async def serve_js():
            js_path = frontend_path / "app.js"
            if js_path.exists():
                return FileResponse(str(js_path), media_type="application/javascript")
            return {"error": f"JS not found at {js_path}"}
    else:
        # Fallback: return API info if frontend not found
        logger.warning(f"Frontend not found. Checked paths: {[str(p.resolve() if p.is_absolute() else Path.cwd() / p) for p in possible_paths]}")
        @app.get("/")
        async def root():
            return {
                "message": "Fact-Check API is running",
                "docs": "/docs",
                "health": "/healthz",
                "frontend": "Frontend files not found",
                "checked_paths": [str(p) for p in possible_paths],
                "current_dir": str(Path.cwd()),
                "__file__": str(Path(__file__))
            }

    return app


app = create_app()

