"""
Thin client for the Domo AI Service Gateway (image + text -> text).

  POST {DOMO_BASE_URL}/ai/v1/image/text
  Auth: X-DOMO-Developer-Token

Same signature as claude_client.image_to_text so the analyzer can use either.
Domo has no structured-output mode, so `schema` is not sent; the analyzer
validates every reply against the schema itself. Calls are logged to
logs/api_usage.csv (cost is left blank: Domo bills through its own contract).
"""
import base64
import time
from pathlib import Path

import requests

from construction_hazards import config, usage_log
from construction_hazards.claude_client import MEDIA_TYPES


class DomoResponseError(RuntimeError):
    pass


# Models that rejected the temperature parameter; it is not sent to them again.
_NO_TEMPERATURE: set[str] = set()


def _extract_output(data: dict) -> str:
    if data.get("output"):
        return str(data["output"])
    choices = data.get("choices") or []
    if choices and isinstance(choices[0], dict) and choices[0].get("output"):
        return str(choices[0]["output"])
    raise DomoResponseError(f"Unrecognized Domo response shape: keys={list(data)}")


def _post(payload: dict) -> dict:
    resp = requests.post(
        f"{config.DOMO_BASE_URL}/ai/v1/image/text",
        headers={
            "X-DOMO-Developer-Token": config.DOMO_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=payload,
        timeout=config.REQUEST_TIMEOUT_S,
    )
    resp.raise_for_status()
    return resp.json()


def image_to_text(
    image_path: str | Path,
    prompt: str,
    system: str = "",
    model: str | None = None,
    schema: dict | None = None,  # accepted for interface parity; Domo cannot enforce it
    step: str = "",
) -> str:
    if not config.DOMO_AVAILABLE:
        raise DomoResponseError("Domo is not configured (DOMO_BASE_URL / DOMO_API_KEY missing in .env)")
    path = Path(image_path)
    media_type = MEDIA_TYPES.get(path.suffix.lower())
    if not media_type:
        raise ValueError(f"Unsupported image type: {path.suffix}")

    model = model or config.DOMO_MODEL
    payload = {
        "input": prompt,
        "image": {
            "data": base64.b64encode(path.read_bytes()).decode("utf-8"),
            "type": "base64",
            "mediaType": media_type,
        },
        "model": model,
    }
    if system:
        payload["system"] = system
    if config.DOMO_TEMPERATURE is not None and model not in _NO_TEMPERATURE:
        payload["temperature"] = config.DOMO_TEMPERATURE

    t0 = time.time()
    try:
        try:
            data = _post(payload)
        except requests.HTTPError as e:
            # Some models (e.g. OpenAI reasoning models) reject a custom temperature:
            # retry once without it and remember that for this model.
            if "temperature" not in payload or e.response is None or e.response.status_code != 400:
                raise
            payload.pop("temperature")
            data = _post(payload)
            _NO_TEMPERATURE.add(model)
    except Exception as e:
        usage_log.log_call(image=path.name, step=step, model=model, effort="", duration_s=time.time() - t0,
                           status=f"error: {type(e).__name__}")
        raise
    u = data.get("modelProviderUsage") or {}
    usage_log.log_call(
        image=path.name, step=step, model=data.get("modelId") or model, effort="",
        input_tokens=int(u.get("inputTokens") or 0), output_tokens=int(u.get("outputTokens") or 0),
        duration_s=time.time() - t0, stop_reason="", status="ok",
    )
    return _extract_output(data)
