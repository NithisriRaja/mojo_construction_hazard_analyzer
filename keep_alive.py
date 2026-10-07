"""
Keeps the Render free-tier service awake by calling /api/health every 5 minutes
(Render spins a free service down after 15 minutes without traffic).

Run it on a machine that stays on:
    venv\\Scripts\\python keep_alive.py https://<service>.onrender.com
or set KEEP_ALIVE_URL instead of passing the URL. Stop with Ctrl+C.
"""
import os
import sys
import time
from datetime import datetime

import requests

INTERVAL_S = 5 * 60
TIMEOUT_S = 60  # a cold start can take ~30-60 s


def main() -> None:
    base = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("KEEP_ALIVE_URL", "")).rstrip("/")
    if not base:
        sys.exit("Usage: python keep_alive.py https://<service>.onrender.com  (or set KEEP_ALIVE_URL)")
    url = f"{base}/api/health"
    print(f"Pinging {url} every {INTERVAL_S // 60} min. Ctrl+C to stop.")
    while True:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            start = time.monotonic()
            res = requests.get(url, timeout=TIMEOUT_S)
            print(f"{stamp}  HTTP {res.status_code}  {time.monotonic() - start:.1f}s", flush=True)
        except requests.RequestException as e:
            print(f"{stamp}  failed: {e}", flush=True)
        time.sleep(INTERVAL_S)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
