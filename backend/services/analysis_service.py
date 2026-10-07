"""Runs the 3-step hazard analysis for one uploaded image and collects its usage."""
import secrets
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backend.services import domo_usage
from construction_hazards import analyzer, config, usage_log


@dataclass
class RequestUsage:
    provider: str
    model: str
    run_id: str
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float | None  # None = not known (Domo bills through its own contract)
    duration_s: float

    def headers(self) -> dict[str, str]:
        return {
            "X-Provider": self.provider,
            "X-Model": self.model,
            "X-Run-Id": self.run_id,
            "X-API-Calls": str(self.calls),
            "X-Input-Tokens": str(self.input_tokens),
            "X-Output-Tokens": str(self.output_tokens),
            "X-Cost-USD": "n/a" if self.cost_usd is None else f"{self.cost_usd:.6f}",
            "X-Duration-S": f"{self.duration_s:.1f}",
        }


def analyze_upload(image_bytes: bytes, name: str, suffix: str, provider: str) -> tuple[dict, RequestUsage]:
    """Return ({"message", "hazards"}, usage). Raises analyzer.HazardAnalysisError."""
    run_id = f"api-{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"
    acc: dict = {}
    usage_log.current_run_id.set(run_id)   # one run_id per request in logs/api_usage.csv
    usage_log.request_usage.set(acc)
    started = datetime.now()
    t0 = time.time()
    status = "error"
    try:
        # Keep the original file name so the usage log shows what was analyzed.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / (Path(name).stem + suffix)
            path.write_bytes(image_bytes)
            result = analyzer.analyze_image(path, provider=provider)
        status = "ok"
    finally:
        usage_log.request_usage.set(None)
        usage = RequestUsage(
            provider=provider,
            model=config.CLAUDE_MODEL if provider == "claude" else config.DOMO_MODEL,
            run_id=run_id,
            calls=acc.get("calls", 0),
            input_tokens=acc.get("input_tokens", 0),
            output_tokens=acc.get("output_tokens", 0),
            cost_usd=None if acc.get("cost_unknown") else acc.get("cost_usd", 0.0),
            duration_s=time.time() - t0,
        )
        # One row per image in Domo; failed runs too, since their calls are still billed.
        # Domo-provider runs have no cost, so they are not sent.
        if provider == "claude" and usage.calls:
            domo_usage.record(
                date=f"{started:%Y-%m-%d}", time_=f"{started:%H:%M:%S}", run_id=run_id, image=name,
                model=usage.model, input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
                cost_usd=usage.cost_usd or 0.0, duration_s=usage.duration_s, status=status,
            )
    return result, usage
