from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import SessionLocal
from .models import Niche
from .routers import api_keys, audit, auth, jobs, niches, roles, settings as settings_router, users, workspaces
from .seed import create_schema, seed_defaults
from .services.niche_importer import import_niches


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    settings.niches_dir.mkdir(parents=True, exist_ok=True)
    settings.niche_configs_dir.mkdir(parents=True, exist_ok=True)
    create_schema()
    with SessionLocal() as db:
        seed_defaults(db)
        if not db.query(Niche).first():
            import_niches(db)
    yield


app = FastAPI(title="ReelOps", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(roles.router)
app.include_router(users.router)
app.include_router(api_keys.router)
app.include_router(niches.router)
app.include_router(jobs.router)
app.include_router(settings_router.router)
app.include_router(audit.router)


@app.get("/api/health")
def health():
    return {"ok": True, "service": "reelops"}


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    index = frontend_dist / "index.html"
    if index.exists() and not full_path.startswith("api/"):
        return FileResponse(index)
    return {"service": "reelops", "dashboard": "frontend build not found"}
