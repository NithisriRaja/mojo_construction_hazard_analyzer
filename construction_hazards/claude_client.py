"""
Thin client for the Claude Messages API (image + text -> JSON text).

Replaces domo_client.py from the Domo version; the function signature is the
same so the analyzer and prompts are unchanged.

- Structured outputs (output_config.format) make the API return JSON that
  matches the given schema; the analyzer still validates it with jsonschema.
- fallbacks="default": if a safety classifier declines a request, the API
  re-runs it on Anthropic's recommended fallback model instead of failing.
- No temperature: Claude Opus 5.5 does not accept sampling parameters.
"""
import base64
import time
from pathlib import Path

import anthropic

from construction_hazards import config, usage_log

MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not config.CLAUDE_AVAILABLE:
            raise ClaudeResponseError("Claude is not configured (ANTHROPIC_API_KEY missing in .env)")
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=config.REQUEST_TIMEOUT_S, max_retries=2)
    return _client


class ClaudeResponseError(RuntimeError):
    pass


def image_to_text(
    image_path: str | Path,
    prompt: str,
    system: str = "",
    model: str | None = None,
    schema: dict | None = None,
    step: str = "",
) -> str:
    """Every call is logged to logs/api_usage.csv (see usage_log.py)."""
    path = Path(image_path)
    media_type = MEDIA_TYPES.get(path.suffix.lower())
    if not media_type:
        raise ValueError(f"Unsupported image type: {path.suffix}")

    output_config: dict = {"effort": config.CLAUDE_EFFORT}
    if schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": schema}

    model = model or config.CLAUDE_MODEL
    t0 = time.time()
    try:
        response = _create(path, media_type, prompt, system, model, output_config)
    except Exception as e:
        usage_log.log_call(image=path.name, step=step, model=model, duration_s=time.time() - t0,
                           status=f"error: {type(e).__name__}")
        raise
    u = response.usage
    usage_log.log_call(
        image=path.name, step=step, model=response.model,
        input_tokens=u.input_tokens, output_tokens=u.output_tokens,
        cache_read=u.cache_read_input_tokens or 0, cache_write=u.cache_creation_input_tokens or 0,
        duration_s=time.time() - t0, stop_reason=response.stop_reason or "",
        status="ok" if response.stop_reason == "end_turn" else str(response.stop_reason),
    )

    if response.stop_reason == "refusal":
        category = response.stop_details.category if response.stop_details else None
        raise ClaudeResponseError(f"Request declined by safety classifier (category: {category})")
    if response.stop_reason == "max_tokens":
        raise ClaudeResponseError("Response hit max_tokens before finishing")

    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise ClaudeResponseError(f"No text block in response (stop_reason={response.stop_reason})")
    return text


def _create(path: Path, media_type: str, prompt: str, system: str, model: str, output_config: dict):
    return _get_client().beta.messages.create(
        model=model,
        max_tokens=config.MAX_TOKENS,
        system=system or anthropic.NOT_GIVEN,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64.standard_b64encode(path.read_bytes()).decode("utf-8"),
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }],
        output_config=output_config,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
