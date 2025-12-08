import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.db.session import init_db
from backend.app.routes.documents import router as documents_router
from backend.app.routes.evidence import router as evidence_router
from backend.app.core.config import get_settings

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
    # Comprehensive frontend status logging on startup
    current_dir = Path.cwd()
    frontend_docker = Path("/app/frontend")
    frontend_local = current_dir / "frontend"
    
    logger.info("=" * 60)
    logger.info("APPLICATION STARTUP - FILESYSTEM CHECK")
    logger.info("=" * 60)
    logger.info(f"Current working directory: {current_dir}")
    logger.info(f"Main file location: {Path(__file__)}")
    logger.info(f"Is Docker environment: {Path('/.dockerenv').exists()}")
    
    # Check /app directory
    app_dir = Path("/app")
    if app_dir.exists():
        logger.info(f"/app directory exists. Contents:")
        try:
            for item in sorted(app_dir.iterdir()):
                item_type = "DIR" if item.is_dir() else "FILE"
                logger.info(f"  [{item_type}] {item.name}")
        except Exception as e:
            logger.error(f"Error listing /app: {e}")
    else:
        logger.warning("/app directory does NOT exist")
    
    # Check frontend paths
    logger.info("Frontend path checks:")
    logger.info(f"  /app/frontend exists: {frontend_docker.exists()}")
    logger.info(f"  {current_dir}/frontend exists: {frontend_local.exists()}")
    
    if frontend_docker.exists():
        logger.info(f"  /app/frontend contents:")
        try:
            for item in sorted(frontend_docker.iterdir()):
                logger.info(f"    - {item.name}")
        except Exception as e:
            logger.error(f"  Error listing /app/frontend: {e}")
    else:
        logger.error("  ✗ /app/frontend does NOT exist - this is the problem!")
        logger.error("  This means the frontend directory was not copied into the Docker image")
    
    if frontend_local.exists():
        logger.info(f"  {current_dir}/frontend contents:")
        try:
            for item in sorted(frontend_local.iterdir()):
                logger.info(f"    - {item.name}")
        except Exception as e:
            logger.error(f"  Error listing {current_dir}/frontend: {e}")
    
    logger.info("=" * 60)
    yield


def create_app() -> FastAPI:
    """Application factory to keep wiring testable."""
    settings = get_settings()
    
    app = FastAPI(
        title="Antisemitism Fact-Check API",
        version="0.1.0",
        description="Prototype API for ingestion, retrieval, and verification services.",
        lifespan=lifespan,
    )
    
    # Add exception handler for unhandled errors
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(exc)}"}
        )

    # CORS configuration - MUST be added LAST (outermost layer)
    # Filter out wildcard patterns from exact origins
    exact_origins = [origin for origin in settings.cors_origins if "*" not in origin]
    # Extract wildcard patterns for regex matching
    wildcard_patterns = [origin for origin in settings.cors_origins if "*" in origin]
    
    # Convert wildcard patterns to regex (e.g., "https://*.vercel.app" -> r"https://.*\.vercel\.app")
    origin_regex_patterns = []
    for pattern in wildcard_patterns:
        # Convert wildcard to regex: escape dots, replace * with .*
        regex = pattern.replace(".", r"\.").replace("*", ".*")
        origin_regex_patterns.append(regex)
    
    # Combine regex patterns if any exist
    origin_regex = "|".join([f"^{p}$" for p in origin_regex_patterns]) if origin_regex_patterns else None
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=exact_origins if exact_origins else [],
        allow_origin_regex=origin_regex,  # This handles wildcard patterns!
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz", tags=["health"])
    async def healthcheck() -> dict:
        """Health check endpoint with system status."""
        from backend.app.core.config import get_settings
        from backend.app.db.session import get_engine
        from pathlib import Path
        
        status = {"status": "ok"}
        
        # Check database
        try:
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            status["database"] = "ok"
        except Exception as e:
            status["database"] = f"error: {str(e)}"
            status["status"] = "degraded"
        
        # Check file directories
        settings = get_settings()
        try:
            uploads_dir = Path(settings.ingest_bucket_path)
            uploads_dir.mkdir(parents=True, exist_ok=True)
            status["uploads_dir"] = "ok" if uploads_dir.exists() and uploads_dir.is_dir() else "missing"
        except Exception as e:
            status["uploads_dir"] = f"error: {str(e)}"
        
        try:
            processed_dir = Path(settings.processed_text_path)
            processed_dir.mkdir(parents=True, exist_ok=True)
            status["processed_dir"] = "ok" if processed_dir.exists() and processed_dir.is_dir() else "missing"
        except Exception as e:
            status["processed_dir"] = f"error: {str(e)}"
        
        return status
    
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
            "root_contents": [],
            "root_tree": {}
        }
        
        # Check root directory contents with full tree
        try:
            root_path = Path("/app") if Path("/app").exists() else current_dir
            if root_path.exists():
                results["root_contents"] = [item.name for item in root_path.iterdir()]
                # Build a tree structure
                def build_tree(path: Path, max_depth: int = 3, current_depth: int = 0):
                    if current_depth >= max_depth:
                        return None
                    if not path.exists():
                        return None
                    if path.is_file():
                        return path.name
                    if path.is_dir():
                        try:
                            children = {}
                            for child in path.iterdir():
                                child_tree = build_tree(child, max_depth, current_depth + 1)
                                if child_tree is not None:
                                    children[child.name] = child_tree
                            return children if children else "empty"
                        except PermissionError:
                            return "permission_denied"
                    return None
                
                results["root_tree"] = build_tree(root_path, max_depth=2)
        except Exception as e:
            results["root_contents_error"] = str(e)
        
        # Check each possible frontend path
        for path in possible_frontend_paths:
            abs_path = path.resolve() if path.is_absolute() else current_dir / path
            exists = abs_path.exists()
            has_index = (abs_path / "index.html").exists() if exists else False
            contents = []
            if exists and abs_path.is_dir():
                try:
                    contents = [item.name for item in abs_path.iterdir()]
                except Exception as e:
                    contents = [f"error: {str(e)}"]
            
            results["paths_checked"].append({
                "path": str(path),
                "resolved": str(abs_path),
                "exists": exists,
                "has_index.html": has_index,
                "contents": contents
            })
        
        return results
    
    @app.get("/debug/filesystem", tags=["debug"])
    async def debug_filesystem() -> dict:
        """Comprehensive filesystem inspection for debugging."""
        import subprocess
        current_dir = Path.cwd()
        
        results = {
            "current_directory": str(current_dir),
            "ls_root": [],
            "ls_app": [],
            "find_frontend": [],
            "docker_check": {}
        }
        
        # Try to list root directory
        try:
            root = Path("/app")
            if root.exists():
                results["ls_app"] = [item.name for item in root.iterdir()]
        except Exception as e:
            results["ls_app_error"] = str(e)
        
        # Try to find frontend using find command (if available)
        try:
            result = subprocess.run(
                ["find", "/app", "-name", "index.html", "-type", "f", "2>/dev/null"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                results["find_frontend"] = result.stdout.strip().split("\n") if result.stdout.strip() else []
        except Exception as e:
            results["find_error"] = str(e)
        
        # Check if we're in Docker
        results["docker_check"] = {
            "is_docker": Path("/.dockerenv").exists(),
            "app_exists": Path("/app").exists(),
            "frontend_exists": Path("/app/frontend").exists(),
            "frontend_index_exists": Path("/app/frontend/index.html").exists() if Path("/app/frontend").exists() else False
        }
        
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

