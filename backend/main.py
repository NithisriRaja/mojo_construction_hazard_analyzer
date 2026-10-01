"""
FastAPI backend for the construction hazard analyzer.

  GET  /api/health       service status, model and effort
  GET  /api/categories   the 39 categories and 3 severities
  POST /api/analyze          Claude (default)  multipart field "file" -> {"message", "hazards"}
  POST /api/analyze/claude   Claude Opus
  POST /api/analyze/domo     Domo AI Gateway (model from DOMO_MODEL)
  GET  /docs             interactive API docs

The Claude API key stays on the server (.env); browsers only talk to this
API. Every Claude call is logged to logs/api_usage.csv.

Run from the project root:
    venv\\Scripts\\python -m uvicorn backend.main:app --port 8000
If frontend/dist exists (npm run build), it is served at "/" as well.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend import settings
from backend.routes import analyze, health

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Construction Hazard Analyzer API",
    version="1.0.0",
    description="Upload a construction site photo; get the visible safety hazards as JSON.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["X-Provider", "X-Model", "X-Run-Id", "X-API-Calls", "X-Input-Tokens", "X-Output-Tokens", "X-Cost-USD", "X-Duration-S"],
)

app.include_router(health.router)
app.include_router(analyze.router)

if settings.FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=settings.FRONTEND_DIST, html=True), name="frontend")
