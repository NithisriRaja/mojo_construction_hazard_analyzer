import logging

from fastapi import APIRouter, File, HTTPException, Response, UploadFile

from backend import settings
from backend.schemas import AnalysisResponse, ErrorResponse
from backend.services import analysis_service, image_service
from construction_hazards.analyzer import HazardAnalysisError, ProviderUnavailableError

log = logging.getLogger("hazard_api")

router = APIRouter(prefix="/api", tags=["analysis"])

_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Empty or invalid image"},
    413: {"model": ErrorResponse, "description": "Image too large"},
    415: {"model": ErrorResponse, "description": "Unsupported file type"},
    502: {"model": ErrorResponse, "description": "Analysis failed upstream"},
    503: {"model": ErrorResponse, "description": "Provider not configured"},
}
_FILE = File(..., description="Site photo (PNG, JPEG, WEBP or GIF)")


def _run(provider: str, response: Response, file: UploadFile) -> dict:
    data = file.file.read(settings.MAX_UPLOAD_BYTES + 1)
    name = image_service.safe_name(file.filename)
    image_bytes, suffix = image_service.prepare_image(data, name)
    try:
        result, usage = analysis_service.analyze_upload(image_bytes, name, suffix, provider)
    except ProviderUnavailableError as e:
        raise HTTPException(503, str(e))
    except HazardAnalysisError as e:
        log.exception("[%s] analysis failed for %s", provider, name)
        raise HTTPException(502, f"Analysis failed: {e}")
    response.headers.update(usage.headers())
    cost = "n/a" if usage.cost_usd is None else f"${usage.cost_usd:.4f}"
    log.info("[%s] %s: %d hazards, %d calls, %s, %.1fs", provider, name, len(result["hazards"]), usage.calls, cost, usage.duration_s)
    return result


_DOC = """Detect construction hazards in one photo with {who}.

Body: `{{"message": "...", "hazards": [...]}}`. Usage for this request is in
headers: X-Provider, X-Model, X-Run-Id, X-API-Calls, X-Input-Tokens,
X-Output-Tokens, X-Cost-USD ("n/a" for Domo), X-Duration-S.
"""


@router.post("/analyze", response_model=AnalysisResponse, responses=_RESPONSES, description=_DOC.format(who="Claude (default provider)"))
def analyze(response: Response, file: UploadFile = _FILE) -> dict:
    return _run("claude", response, file)


@router.post("/analyze/claude", response_model=AnalysisResponse, responses=_RESPONSES, description=_DOC.format(who="Claude Opus"))
def analyze_claude(response: Response, file: UploadFile = _FILE) -> dict:
    return _run("claude", response, file)


@router.post("/analyze/domo", response_model=AnalysisResponse, responses=_RESPONSES, description=_DOC.format(who="the Domo AI Gateway (model from DOMO_MODEL)"))
def analyze_domo(response: Response, file: UploadFile = _FILE) -> dict:
    return _run("domo", response, file)
