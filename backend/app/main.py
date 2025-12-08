from contextlib import asynccontextmanager
from pathlib import Path
import re
from typing import List

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.db.session import init_db
from backend.app.routes.documents import router as documents_router
from backend.app.routes.evidence import router as evidence_router
from backend.app.core.config import get_settings


class WildcardCORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware that supports wildcard patterns like *.vercel.app"""
    
    def __init__(self, app: FastAPI, allowed_origins: List[str]):
        super().__init__(app)
        self.allowed_origins = allowed_origins
        self.allowed_patterns: List[re.Pattern] = []
        self.exact_origins: List[str] = []
        self.allow_all = False
        
        for origin in allowed_origins:
            if origin == "*":
                self.allow_all = True
                return
            elif "*" in origin:
                # Convert wildcard pattern to regex
                pattern = origin.replace(".", r"\.").replace("*", r".*")
                self.allowed_patterns.append(re.compile(f"^{pattern}$"))
            else:
                self.exact_origins.append(origin)
    
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            if self.allow_all or (origin and self._is_origin_allowed(origin)):
                response = Response()
                response.headers["Access-Control-Allow-Origin"] = origin or "*"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
                response.headers["Access-Control-Allow-Headers"] = "*"
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Max-Age"] = "3600"
                return response
        
        response = await call_next(request)
        
        # Add CORS headers to response
        if origin and (self.allow_all or self._is_origin_allowed(origin)):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        elif self.allow_all:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        return response
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed based on exact matches or patterns"""
        if origin in self.exact_origins:
            return True
        
        for pattern in self.allowed_patterns:
            if pattern.match(origin):
                return True
        
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
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

    # Configure CORS with wildcard support
    if settings.app_env == "development" or settings.cors_origins == "*":
        cors_origins = ["*"]
    else:
        cors_origins = [origin.strip() for origin in settings.cors_origins.split(",")]
    
    # Use custom middleware for wildcard support (e.g., *.vercel.app)
    app.add_middleware(WildcardCORSMiddleware, allowed_origins=cors_origins)

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

