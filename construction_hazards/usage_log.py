"""
API usage log: one CSV row per Claude API call, appended to logs/api_usage.csv.

Columns: date, time, run_id, image, step, model, effort, input_tokens,
output_tokens (includes thinking tokens), cache_read_tokens,
cache_write_tokens, cost_usd, duration_s, stop_reason, status.

cost_usd is an estimate from the per-token prices below (USD per 1M tokens).
Update PRICES if Anthropic's pricing changes.
"""
import contextvars
import csv
import logging
import threading
from datetime import datetime
from pathlib import Path

from construction_hazards import config

LOG_FILE = config.PROJECT_ROOT / "logs" / "api_usage.csv"
PENDING_FILE = LOG_FILE.with_name("api_usage_pending.csv")
log = logging.getLogger("usage_log")

# model -> (input, output) USD per 1M tokens. Cache reads bill at 0.1x input
# and 5-minute cache writes at 1.25x input.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-fable-5-1": (10.00, 50.00),
}

COLUMNS = [
    "date", "time", "run_id", "image", "step", "model", "effort",
    "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens",
    "cost_usd", "duration_s", "stop_reason", "status",
]

RUN_ID = datetime.now().strftime("%Y%m%d-%H%M%S")  # one id per process / CLI run
# The web API sets a fresh id per request (see backend/app.py).
current_run_id: contextvars.ContextVar[str] = contextvars.ContextVar("current_run_id", default=RUN_ID)
# Optional per-request accumulator: the web API sets a dict here to collect the
# tokens and cost of one analysis (returned in response headers).
request_usage: contextvars.ContextVar[dict | None] = contextvars.ContextVar("request_usage", default=None)

_lock = threading.Lock()
_totals = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}


def estimate_cost(model: str, input_tokens: int, output_tokens: int, cache_read: int = 0, cache_write: int = 0) -> float | None:
    price = PRICES.get(model)
    if price is None:
        return None
    inp, out = price
    return (input_tokens * inp + output_tokens * out + cache_read * inp * 0.1 + cache_write * inp * 1.25) / 1_000_000


def log_call(
    *, image: str, step: str, model: str, input_tokens: int = 0, output_tokens: int = 0,
    cache_read: int = 0, cache_write: int = 0, duration_s: float, stop_reason: str = "", status: str = "ok",
    effort: str | None = None,
) -> None:
    now = datetime.now()
    cost = estimate_cost(model, input_tokens, output_tokens, cache_read, cache_write)
    row = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "run_id": current_run_id.get(),
        "image": image,
        "step": step,
        "model": model,
        "effort": config.CLAUDE_EFFORT if effort is None else effort,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read,
        "cache_write_tokens": cache_write,
        "cost_usd": "" if cost is None else f"{cost:.6f}",
        "duration_s": f"{duration_s:.1f}",
        "stop_reason": stop_reason,
        "status": status,
    }
    with _lock:
        _write_row(row)
        _totals["calls"] += 1
        _totals["input_tokens"] += input_tokens
        _totals["output_tokens"] += output_tokens
        _totals["cost_usd"] += cost or 0.0
    acc = request_usage.get()
    if acc is not None:
        acc["calls"] = acc.get("calls", 0) + 1
        acc["input_tokens"] = acc.get("input_tokens", 0) + input_tokens
        acc["output_tokens"] = acc.get("output_tokens", 0) + output_tokens
        acc["cost_usd"] = acc.get("cost_usd", 0.0) + (cost or 0.0)
        if cost is None:
            acc["cost_unknown"] = True  # e.g. Domo: billed through the Domo contract


def _append(path: Path, row: dict) -> None:
    path.parent.mkdir(exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def _write_row(row: dict) -> None:
    """Logging must never fail an analysis. If the CSV is locked (e.g. open in
    Excel), the row goes to api_usage_pending.csv instead; merge it later."""
    try:
        _append(LOG_FILE, row)
    except OSError:
        try:
            _append(PENDING_FILE, row)
            log.warning("%s is locked (open in Excel?); row written to %s", LOG_FILE.name, PENDING_FILE.name)
        except OSError:
            log.error("Could not write usage log row: %s", row)


def run_totals() -> dict:
    with _lock:
        return dict(_totals, run_id=RUN_ID)
