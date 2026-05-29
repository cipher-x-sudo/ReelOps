# ReelOps

ReelOps is a standalone reel automation control system. It imports niche production guides, creates editable niche workflows, manages users with workspace-scoped RBAC, calls Flow2API for image/video generation, and renders finished reel exports with Remotion.

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:8080`.

Default credentials come from:

- `REELOPS_ADMIN_USER`
- `REELOPS_ADMIN_PASSWORD`

## Local Services

- ReelOps API + dashboard: `http://localhost:8080`
- Postgres: `localhost:5437`
- Generated artifacts: `./artifacts`

## Important Environment Variables

- `DATABASE_URL`: Postgres connection string.
- `FLOW2API_BASE_URL`: Existing Flow2API service URL.
- `FLOW2API_API_KEY`: Managed API key used for image/video generation.
- `ARTIFACTS_DIR`: Where generated clips, captions, renders, and CapCut packages are stored.
- `NICHES_DIR`: Folder containing source DOCX/PDF niche guides.
- `NICHE_CONFIGS_DIR`: Folder containing editable generated niche configs.

## Project Layout

- `backend/`: FastAPI API, RBAC, worker, providers, niche importer.
- `frontend/`: React dashboard.
- `renderer/`: Remotion reel renderer.
- `niches/`: Imported source guide files.
- `configs/niches/`: Editable per-niche workflow configs.
- `artifacts/`: Runtime outputs, ignored by Git.
