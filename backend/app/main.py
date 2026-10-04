"""
OrgIntel Backend Application Entry Point
FastAPI application with lifecycle management, middleware, static UI mounting, and REST API routes.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.app.config import settings
from backend.app.database import init_db
from backend.app.api.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown events."""
    # Initialize SQLite database schema
    await init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered company intelligence for Norwegian organizations. Traceable evidence from public sources.",
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS Middleware
cors_origins = (
    [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    if settings.CORS_ORIGINS != "*"
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST API Routes
app.include_router(api_router)

# Mount Frontend Static Assets
frontend_dir = settings.BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(frontend_dir / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Serve static file if exists, otherwise fallback to index.html for SPA routes
        target_file = frontend_dir / full_path
        if target_file.is_file():
            return FileResponse(target_file)
        return FileResponse(frontend_dir / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
