"""
Sends one usage row per Claude analysis to a Domo dataset, so live costs on the
deployed API are kept (the local logs/api_usage.csv is wiped on each Render deploy).

Rows are queued and uploaded by a background thread, so Domo is never in the
request path and a Domo outage never fails an analysis. Upload = the Domo
Product API with the developer token already used for the AI Gateway:

  POST {instance}/api/data/v3/datasources/{id}/uploads                      -> uploadId
  PUT  {instance}/api/data/v3/datasources/{id}/uploads/{uploadId}/parts/1   CSV rows, no header
  PUT  {instance}/api/data/v3/datasources/{id}/uploads/{uploadId}/commit    {"action": "APPEND"}

Enabled when DOMO_USAGE_DATASET_ID, DOMO_BASE_URL and DOMO_API_KEY are set in .env.
Columns must match the dataset's schema order (COLUMNS below).
"""
import atexit
import csv
import io
import logging
import queue
import threading
import time
from urllib.parse import urlparse

import requests

from construction_hazards import config

log = logging.getLogger("domo_usage")

COLUMNS = ["date", "time", "run_id", "image", "model", "input_tokens", "output_tokens", "cost_usd", "duration", "status"]

MAX_ATTEMPTS = 3
TIMEOUT_S = 30
MAX_BATCH = 50

ENABLED = bool(config.DOMO_USAGE_DATASET_ID and config.DOMO_BASE_URL and config.DOMO_API_KEY)

_queue: queue.Queue[dict] = queue.Queue()
_worker: threading.Thread | None = None
_start_lock = threading.Lock()


def _uploads_url() -> str:
    host = urlparse(config.DOMO_BASE_URL).netloc
    return f"https://{host}/api/data/v3/datasources/{config.DOMO_USAGE_DATASET_ID}/uploads"


def _to_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    for row in rows:
        writer.writerow([row.get(c, "") for c in COLUMNS])
    return buf.getvalue()


def upload_rows(rows: list[dict]) -> None:
    """Append rows to the Domo dataset (3-step upload). Raises on failure."""
    headers = {"X-DOMO-Developer-Token": config.DOMO_API_KEY, "Accept": "application/json"}
    url = _uploads_url()
    r = requests.post(url, json={"action": None, "appendId": None}, headers=headers, timeout=TIMEOUT_S)
    r.raise_for_status()
    upload_id = r.json()["uploadId"]
    r = requests.put(f"{url}/{upload_id}/parts/1", data=_to_csv(rows).encode("utf-8"),
                     headers={**headers, "Content-Type": "text/csv"}, timeout=TIMEOUT_S)
    r.raise_for_status()
    r = requests.put(f"{url}/{upload_id}/commit", json={"action": "APPEND", "index": True},
                     headers=headers, timeout=TIMEOUT_S)
    r.raise_for_status()


def _send(rows: list[dict]) -> None:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            upload_rows(rows)
            log.info("Sent %d usage row(s) to Domo", len(rows))
            return
        except (requests.RequestException, KeyError, ValueError) as e:
            if attempt == MAX_ATTEMPTS:
                # The rows are still in logs/api_usage.csv (per call).
                log.error("Domo usage upload failed after %d attempts: %s; rows: %s", attempt, e, rows)
            else:
                time.sleep(2 * attempt)


def _drain(first: dict) -> list[dict]:
    rows = [first]
    while len(rows) < MAX_BATCH:
        try:
            rows.append(_queue.get_nowait())
        except queue.Empty:
            break
    return rows


def _run() -> None:
    while True:
        _send(_drain(_queue.get()))


def _start() -> None:
    global _worker
    with _start_lock:
        if _worker is None:
            _worker = threading.Thread(target=_run, name="domo-usage", daemon=True)
            _worker.start()


def record(*, date: str, time_: str, run_id: str, image: str, model: str, input_tokens: int,
           output_tokens: int, cost_usd: float, duration_s: float, status: str) -> None:
    """Queue one row; returns immediately. No-op when Domo logging is not configured."""
    if not ENABLED:
        return
    _queue.put({
        "date": date, "time": time_, "run_id": run_id, "image": image, "model": model,
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "cost_usd": f"{cost_usd:.6f}", "duration": f"{duration_s:.1f}", "status": status,
    })
    _start()


@atexit.register
def _flush() -> None:
    """On shutdown, send whatever is still queued (best effort)."""
    rows = []
    while True:
        try:
            rows.append(_queue.get_nowait())
        except queue.Empty:
            break
    if rows:
        _send(rows)
