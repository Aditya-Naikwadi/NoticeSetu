"""NoticeSetu REST API routes for simplification, Q&A, .ics export, and audio."""

import io
import re
from typing import Literal

from fastapi import APIRouter, File, Form, Request, Response, UploadFile
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.schemas import ActionCardResponse, QARequest, QAResponse
from app.services.cache import get_cache
from app.services.calendar_ics import generate_ics
from app.services.extractor import UnreadableDocumentError
from app.services.pii_guard import PIIBlockedError
from app.services.security import (
    MAX_FILE_BYTES,
    SecurityValidationError,
    get_rate_limiter,
    safe_fetch_url,
)
from app.services.simplifier import SimplifierError, answer_notice_question, process_notice_bytes
from app.services.tts import TTSUnavailableError, get_or_create_audio

router = APIRouter(prefix="/api", tags=["notices"])

SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def _client_ip_from_request(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, "message": message})


async def _read_upload_in_memory(upload: UploadFile) -> bytes:
    """Read UploadFile strictly into io.BytesIO with 10 MB ceiling."""
    buf = io.BytesIO()
    total = 0
    while True:
        chunk = await upload.read(65536)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_FILE_BYTES:
            raise SecurityValidationError(
                status_code=413,
                code="FILE_TOO_LARGE",
                message="Uploaded file exceeds the 10 MB limit.",
            )
        buf.write(chunk)
    return buf.getvalue()


@router.post("/simplify", response_model=ActionCardResponse)
async def simplify_notice(
    request: Request,
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
):
    """Ingest a PDF/image file or public circular URL and return a structured Action Card."""
    settings = get_settings()
    try:
        await get_rate_limiter().check(
            _client_ip_from_request(request),
            settings.RATE_LIMIT_MAX_REQUESTS,
            settings.RATE_LIMIT_WINDOW_SECONDS,
        )
    except SecurityValidationError as exc:
        return _error_response(exc.status_code, exc.code, exc.message)

    clean_url = url.strip() if url else ""
    if (file is None and not clean_url) or (file is not None and clean_url):
        return _error_response(
            400,
            "INVALID_INPUT",
            "Provide either a PDF/image file upload or a public circular URL.",
        )

    try:
        if clean_url:
            raw_bytes, _ = await safe_fetch_url(clean_url)
            source_hint = "url"
        else:
            assert file is not None
            raw_bytes = await _read_upload_in_memory(file)
            source_hint = "upload"

        return await process_notice_bytes(raw_bytes, source_hint=source_hint)
    except SecurityValidationError as exc:
        return _error_response(exc.status_code, exc.code, exc.message)
    except UnreadableDocumentError as exc:
        return _error_response(422, "UNREADABLE_DOCUMENT", exc.message)
    except PIIBlockedError as exc:
        return _error_response(422, exc.code, exc.message)
    except SimplifierError as exc:
        return _error_response(exc.status_code, exc.code, exc.message)


@router.get("/notice/{notice_hash}", response_model=ActionCardResponse)
async def get_notice(notice_hash: str):
    """Retrieve a cached Action Card by SHA-256 hash."""
    normalized_hash = notice_hash.strip().lower()
    if not SHA256_HEX_RE.match(normalized_hash):
        return _error_response(400, "INVALID_HASH", "Malformed notice hash.")

    cache = get_cache()
    card, _ = await cache.get_by_sha256(normalized_hash)
    if card is None:
        return _error_response(
            404,
            "NOTICE_NOT_FOUND",
            "Notice not found or expired after the 14-day retention window.",
        )
    return card


@router.post("/qa", response_model=QAResponse)
async def notice_qa(request: Request, req: QARequest):
    """Answer a student question strictly grounded in the cached circular."""
    settings = get_settings()
    try:
        await get_rate_limiter().check(
            _client_ip_from_request(request),
            settings.RATE_LIMIT_MAX_REQUESTS,
            settings.RATE_LIMIT_WINDOW_SECONDS,
        )
    except SecurityValidationError as exc:
        return _error_response(exc.status_code, exc.code, exc.message)

    normalized_hash = req.notice_hash.strip().lower()
    cache = get_cache()
    resolved_hash = await cache.resolve_hash_prefix(normalized_hash) or normalized_hash
    card, source_text = await cache.get_by_sha256(resolved_hash)
    if card is None:
        return _error_response(
            404,
            "NOTICE_NOT_FOUND",
            "Notice not found or expired. Please re-upload the circular.",
        )

    try:
        return await answer_notice_question(
            card=card,
            source_text=source_text,
            question=req.question,
            lang=req.lang,
        )
    except SimplifierError as exc:
        return _error_response(exc.status_code, exc.code, exc.message)


@router.get("/notice/{notice_hash}/ics")
async def export_notice_ics(notice_hash: str):
    """Generate and download an RFC-5545 .ics calendar file for extracted deadlines."""
    normalized_hash = notice_hash.strip().lower()
    if not SHA256_HEX_RE.match(normalized_hash):
        return _error_response(400, "INVALID_HASH", "Malformed notice hash.")

    cache = get_cache()
    card, _ = await cache.get_by_sha256(normalized_hash)
    if card is None:
        return _error_response(404, "NOTICE_NOT_FOUND", "Notice not found or expired.")

    try:
        ics_content = generate_ics(card)
    except ValueError as exc:
        return _error_response(404, "NO_CALENDAR_DEADLINES", str(exc))

    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="noticesetu-{normalized_hash[:12]}.ics"'
        },
    )


@router.get("/audio/{notice_hash}/{lang}")
async def get_notice_audio(notice_hash: str, lang: str):
    """Serve cached or freshly synthesized regional voice brief MP3."""
    normalized_hash = notice_hash.strip().lower()
    if not SHA256_HEX_RE.match(normalized_hash):
        return _error_response(400, "INVALID_HASH", "Malformed notice hash.")
    if lang not in {"en", "hi", "mr"}:
        return _error_response(400, "INVALID_LANGUAGE", "Supported audio languages are en, hi, mr.")

    cache = get_cache()
    card, _ = await cache.get_by_sha256(normalized_hash)
    if card is None:
        return _error_response(404, "NOTICE_NOT_FOUND", "Notice not found or expired.")

    typed_lang: Literal["en", "hi", "mr"] = lang  # type: ignore[assignment]
    voice_script = getattr(card.extraction, typed_lang).voice_script

    try:
        audio_bytes = await get_or_create_audio(normalized_hash, typed_lang, voice_script)
    except TTSUnavailableError as exc:
        return _error_response(exc.status_code, "TTS_UNAVAILABLE", exc.message)

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )

