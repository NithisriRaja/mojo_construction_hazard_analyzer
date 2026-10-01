"""Backend-only settings (API limits, CORS). Model settings live in construction_hazards/config.py."""
from dotenv import dotenv_values

from construction_hazards import config

_ENV = dotenv_values(config.PROJECT_ROOT / ".env")

# Origins allowed to call the API from a browser (comma-separated in .env).
CORS_ORIGINS = [
    o.strip()
    for o in (_ENV.get("CORS_ORIGINS") or "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]

MAX_UPLOAD_BYTES = 20 * 1024 * 1024   # reject anything larger outright
SEND_LIMIT_BYTES = 4 * 1024 * 1024    # above this, downscale before sending to Claude
MAX_LONG_EDGE = 2000                  # px; Claude downsizes large images itself, this keeps requests small

FRONTEND_DIST = config.PROJECT_ROOT / "frontend" / "dist"
