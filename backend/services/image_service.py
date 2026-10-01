"""Upload validation and resizing."""
import io
import re
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from backend import settings
from construction_hazards.claude_client import MEDIA_TYPES


def safe_name(name: str | None) -> str:
    stem = Path(name or "upload").name
    stem = re.sub(r"[^A-Za-z0-9._ -]", "_", stem).strip() or "upload"
    return stem[:120]


def prepare_image(data: bytes, filename: str) -> tuple[bytes, str]:
    """Check the bytes really are a supported image, and shrink very large
    photos (e.g. from phones). Returns (image bytes, file suffix)."""
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"Image is larger than {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")

    suffix = Path(filename).suffix.lower()
    if suffix not in MEDIA_TYPES:
        raise HTTPException(415, f"Unsupported file type '{suffix or 'none'}'. Use PNG, JPEG, WEBP or GIF.")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "The file is not a valid image.")

    if len(data) <= settings.SEND_LIMIT_BYTES:
        return data, suffix

    with Image.open(io.BytesIO(data)) as img:
        img = img.convert("RGB")
        img.thumbnail((settings.MAX_LONG_EDGE, settings.MAX_LONG_EDGE))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=90)
    return out.getvalue(), ".jpg"
