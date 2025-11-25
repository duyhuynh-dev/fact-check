import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.db.session import init_db
from backend.app.routes.documents import router as documents_router
from backend.app.routes.evidence import router as evidence_router

# Configure logging to show INFO level messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Log frontend status on startup
    current_dir = Path.cwd()
    frontend_docker = Path("/app/frontend")
    frontend_local = current_dir / "frontend"
    logger.info(f"Startup: Current directory = {current_dir}")
    logger.info(f"Startup: Docker frontend path exists = {frontend_docker.exists()}")
    logger.info(f"Startup: Local frontend path exists = {frontend_local.exists()}")
    if frontend_docker.exists():
        logger.info(f"Startup: Docker frontend contents = {list(frontend_docker.iterdir())}")
    if frontend_local.exists():
        logger.info(f"Startup: Local frontend contents = {list(frontend_local.iterdir())}")
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
    current_dir = Path.cwd()
    main_file_path = Path(__file__)
    
    possible_paths = [
        main_file_path.parent.parent.parent / "frontend",  # Local: backend/app/main.py -> backend -> project root -> frontend
        Path("/app/frontend"),  # Docker container (WORKDIR is /app)
        current_dir / "frontend",  # Relative to current working directory
    ]
    
    frontend_path = None
    checked_paths_info = []
    
    for path in possible_paths:
        # For absolute paths, use as-is; for relative, resolve from current_dir
        if path.is_absolute():
            abs_path = path
        else:
            abs_path = current_dir / path
        
        exists = abs_path.exists()
        has_index = (abs_path / "index.html").exists() if exists else False
        
        checked_paths_info.append({
            "original": str(path),
            "resolved": str(abs_path),
            "exists": exists,
            "has_index": has_index
        })
        
        logger.info(f"Checking frontend path: {abs_path} (exists: {exists}, has_index: {has_index})")
        
        if exists and has_index:
            frontend_path = abs_path
            logger.info(f"✓ Found frontend at: {frontend_path}")
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
            return {
                "error": "Frontend file not found",
                "expected_path": str(index_path),
                "frontend_dir": str(frontend_path),
                "checked_paths": checked_paths_info
            }

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
        logger.error(f"Frontend not found! Checked paths: {checked_paths_info}")
        logger.error(f"Current working directory: {current_dir}")
        logger.error(f"Main file location: {main_file_path}")
        
        @app.get("/")
        async def root():
            return {
                "message": "Fact-Check API is running",
                "docs": "/docs",
                "health": "/healthz",
                "debug": "/debug/paths",
                "error": "Frontend files not found",
                "checked_paths": checked_paths_info,
                "current_dir": str(current_dir),
                "__file__": str(main_file_path),
                "frontend_expected_at": "/app/frontend (Docker) or ./frontend (local)"
            }

    return app


app = create_app()

