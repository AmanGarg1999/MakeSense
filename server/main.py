"""MakeSense API Server — Unified backend for the learning platform."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from server.config import settings
from server.database import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    await init_db()
    from server.database import get_pool
    app.state.db_pool = await get_pool()
    yield
    await close_db()


app = FastAPI(
    title="MakeSense API",
    description="Personalized learning content platform with gamification",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from server.routers import topics, content, quiz, feedback, paths, streaks, achievements, reviews
app.include_router(topics.router, prefix="/api", tags=["Topics"])
app.include_router(content.router, prefix="/api", tags=["Content"])
app.include_router(quiz.router, prefix="/api", tags=["Quiz"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])
app.include_router(paths.router, prefix="/api/paths", tags=["Learning Paths"])
app.include_router(streaks.router, prefix="/api", tags=["Streaks"])
app.include_router(achievements.router, prefix="/api", tags=["Achievements"])
app.include_router(reviews.router, prefix="/api", tags=["Reviews"])

# Import gamification router
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from gamification.api import router as gamification_router
    app.include_router(gamification_router, tags=["Gamification"])
except ImportError as e:
    print(f"Warning: Could not import gamification router: {e}")

# Serve static files
ROOT_DIR = Path(__file__).parent.parent

# Serve generated content
generated_dir = ROOT_DIR / "generated-content"
if generated_dir.exists():
    app.mount("/generated-content", StaticFiles(directory=str(generated_dir)), name="generated-content")

# Serve data directory (for legacy compatibility)
data_dir = ROOT_DIR / "data"
if data_dir.exists():
    app.mount("/data", StaticFiles(directory=str(data_dir)), name="data")

# Serve frontend dist if built
frontend_dist = ROOT_DIR / "frontend" / "dist"
if frontend_dist.exists():
    assets_dist = frontend_dist / "assets"
    if assets_dist.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dist)), name="assets")

    icons_dist = frontend_dist / "icons"
    if icons_dist.exists():
        app.mount("/icons", StaticFiles(directory=str(icons_dist)), name="icons")

    # Serve all root-level PWA files (sw.js, workbox-*.js, manifest, icons, etc.)
    for item in frontend_dist.iterdir():
        if item.is_file() and item.name != "index.html":
            filename = item.name
            def make_endpoint(fn=filename):
                @app.get(f"/{fn}", include_in_schema=False)
                async def serve_file():
                    return FileResponse(str(frontend_dist / fn))
                return serve_file
            make_endpoint()

    app.mount("/app", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

# Serve root static files (CSS, JS)
for static_file in ["styles.css", "app.js"]:
    filepath = ROOT_DIR / static_file
    if filepath.exists():
        @app.get(f"/{static_file}", include_in_schema=False)
        async def serve_static(file=static_file):
            return FileResponse(str(ROOT_DIR / file))

# Serve src directory files
src_dir = ROOT_DIR / "src"
if src_dir.exists():
    app.mount("/src", StaticFiles(directory=str(src_dir)), name="src")

# HTML page routes
@app.get("/", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
async def serve_index():
    return FileResponse(str(ROOT_DIR / "index.html"))

@app.get("/library", include_in_schema=False)
@app.get("/library.html", include_in_schema=False)
async def serve_library():
    return FileResponse(str(ROOT_DIR / "library.html"))

@app.get("/admin", include_in_schema=False)
@app.get("/admin-dashboard.html", include_in_schema=False)
async def serve_admin():
    return FileResponse(str(ROOT_DIR / "admin-dashboard.html"))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
