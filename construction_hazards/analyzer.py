"""
Construction hazard analysis for a single site photo.

Runs the three steps described in prompts.py (detect -> verify -> PPE check)
against the chosen provider: Claude (claude_client.py) or Domo (domo_client.py). Every hazard list is parsed as JSON and
validated against the client HAZARD_SCHEMA (schema.py).

Invalid JSON / schema failures / HTTP errors are retried up to
config.MAX_ATTEMPTS times per call before HazardAnalysisError is raised.

The only post-processing on a valid response is a *stable* sort by severity
(High > Medium > Low). This enforces the prompt's "most to least severe"
rule without reordering hazards within the same severity.
"""
import json
import re
import time
from pathlib import Path

import anthropic
import jsonschema
import requests


from construction_hazards import config, prompts
from construction_hazards import claude_client, domo_client
from construction_hazards.claude_client import ClaudeResponseError
from construction_hazards.domo_client import DomoResponseError
from construction_hazards.schema import HAZARD_SCHEMA, OUTPUT_SCHEMA, summary_message

_SEVERITY_RANK = {"High": 0, "Medium": 1, "Low": 2}


class HazardAnalysisError(RuntimeError):
    pass


class ProviderUnavailableError(HazardAnalysisError):
    pass


def _client_for(provider: str):
    if provider == "claude":
        if not config.CLAUDE_AVAILABLE:
            raise ProviderUnavailableError("Claude is not configured (ANTHROPIC_API_KEY missing in .env)")
        return claude_client.image_to_text
    if provider == "domo":
        if not config.DOMO_AVAILABLE:
            raise ProviderUnavailableError("Domo is not configured (DOMO_BASE_URL / DOMO_API_KEY missing in .env)")
        return domo_client.image_to_text
    raise ValueError(f"Unknown provider: {provider!r} (use one of {config.PROVIDERS})")


def _parse_json(text: str) -> dict:
    """Tolerates accidental ```json fences or stray prose around the object,
    even though the prompt forbids them."""
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


_PPE_VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "body_part": {"type": "string"},
        "verdict": {"type": "string", "enum": ["missing", "present", "unclear"]},
    },
    "required": ["body_part", "verdict"],
    "additionalProperties": False,
}


def _call_json(path: Path, prompt: str, system: str, model: str | None, schema: dict, step: str, provider: str) -> dict:
    image_to_text = _client_for(provider)
    last_err: Exception | None = None
    for attempt in range(1, config.MAX_ATTEMPTS + 1):
        try:
            result = _parse_json(image_to_text(path, prompt, system=system, model=model, schema=schema, step=step))
            jsonschema.validate(result, schema)
            return result
        except (ValueError, jsonschema.ValidationError, ClaudeResponseError, anthropic.APIError,
                DomoResponseError, requests.RequestException) as e:
            last_err = e
            if attempt < config.MAX_ATTEMPTS:
                time.sleep(2 * attempt)
    raise HazardAnalysisError(f"{path.name}: failed after {config.MAX_ATTEMPTS} attempts: {last_err}")


def _call_validated(path: Path, prompt: str, system: str, model: str | None, step: str, provider: str) -> dict:
    result = _call_json(path, prompt, system, model, HAZARD_SCHEMA, step, provider)
    result["hazards"].sort(key=lambda h: _SEVERITY_RANK[h["severity"]])
    return result


def _confirm_ppe_claims(path: Path, result: dict, model: str | None, provider: str) -> dict:
    """Keep a PPE hazard only if a focused look confirms the equipment is
    clearly missing. Other hazards pass through untouched."""
    kept = []
    for h in result["hazards"]:
        if h["category"] == prompts.PPE_CHECK_CATEGORY:
            check = _call_json(path, prompts.ppe_check_input(h), prompts.PPE_CHECK_SYSTEM, model, _PPE_VERDICT_SCHEMA, "ppe_check", provider)
            if check["verdict"] != "missing":
                continue
        kept.append(h)
    return {"hazards": kept}


def analyze_image_with_draft(
    image_path: str | Path, model: str | None = None, provider: str = config.DEFAULT_PROVIDER
) -> tuple[dict, dict]:
    """Return (output, draft). output matches OUTPUT_SCHEMA (message + hazards);
    draft is the step-1 list (HAZARD_SCHEMA), kept to audit what verify changed."""
    path = Path(image_path)
    draft = _call_validated(path, prompts.INPUT_PROMPT, prompts.DETECT_SYSTEM, model, "detect", provider)
    final = _call_validated(path, prompts.verify_input(draft), prompts.VERIFY_SYSTEM, model, "verify", provider)
    hazards = _confirm_ppe_claims(path, final, model, provider)["hazards"]
    output = {"message": summary_message(len(hazards)), "hazards": hazards}
    jsonschema.validate(output, OUTPUT_SCHEMA)
    return output, draft


def analyze_image(image_path: str | Path, model: str | None = None, provider: str = config.DEFAULT_PROVIDER) -> dict:
    """Return {"message": "...", "hazards": [...]} validated against OUTPUT_SCHEMA."""
    return analyze_image_with_draft(image_path, model, provider)[0]
