"""
Settings loaded from the project-root .env.

Two providers run the same prompts and pipeline:
  claude -- Anthropic API      (ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_EFFORT)
  domo   -- Domo AI Gateway    (DOMO_BASE_URL, DOMO_API_KEY, DOMO_MODEL, DOMO_TEMPERATURE)
Each is optional; a provider without credentials is reported as unavailable.

Settings are read from the .env file only (never from the shell environment),
so unrelated variables such as a global CLAUDE_EFFORT cannot change them.
ANTHROPIC_API_KEY alone falls back to the environment.
"""
import os
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV = dotenv_values(PROJECT_ROOT / ".env")

# --- Claude ---------------------------------------------------------------
ANTHROPIC_API_KEY = _ENV.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
CLAUDE_MODEL = _ENV.get("CLAUDE_MODEL") or "claude-opus-5-5"
# Thinking depth. Opus 5.5 defaults to "medium"; set explicitly so runs are comparable.
CLAUDE_EFFORT = _ENV.get("CLAUDE_EFFORT") or "high"
CLAUDE_AVAILABLE = bool(ANTHROPIC_API_KEY)

# --- Domo -----------------------------------------------------------------
DOMO_BASE_URL = (_ENV.get("DOMO_BASE_URL") or "").rstrip("/")
DOMO_API_KEY = _ENV.get("DOMO_API_KEY")
DOMO_MODEL = _ENV.get("DOMO_MODEL") or "domo.google.gemini-3.5-flash"
# 0 = repeatable answers (verified with Gemini on the Domo gateway). Set
# DOMO_TEMPERATURE= (empty) in .env to never send it; some models (e.g. OpenAI
# reasoning models) only accept their default, and domo_client also drops it
# automatically if the gateway rejects it.
_t = _ENV.get("DOMO_TEMPERATURE", "0")
DOMO_TEMPERATURE: float | None = float(_t) if _t not in (None, "") else None
DOMO_AVAILABLE = bool(DOMO_BASE_URL and DOMO_API_KEY)

if not (CLAUDE_AVAILABLE or DOMO_AVAILABLE):
    raise RuntimeError(f"No provider configured: set ANTHROPIC_API_KEY and/or DOMO_BASE_URL + DOMO_API_KEY in {PROJECT_ROOT / '.env'}")

PROVIDERS = ("claude", "domo")
DEFAULT_PROVIDER = "claude"

MAX_TOKENS = 16000
REQUEST_TIMEOUT_S = 300
MAX_ATTEMPTS = 3

DEFAULT_IMAGE_DIR = PROJECT_ROOT / "Mojo Site image file"
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "results"
