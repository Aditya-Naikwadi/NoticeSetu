"""Cached regional voice brief synthesis (Sarvam AI / Bhashini / none) with Supabase or memory storage."""

import base64
from typing import Literal

import httpx
from supabase import create_client

from app.config import get_settings
from app.services.cache import get_cache

LANG_CODE_MAP: dict[str, str] = {
    "en": "en-IN",
    "hi": "hi-IN",
    "mr": "mr-IN",
}

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


class TTSUnavailableError(Exception):
    """Raised when TTS provider is disabled or missing credentials."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


async def _synthesize_sarvam(text: str, lang: Literal["en", "hi", "mr"]) -> bytes:
    settings = get_settings()
    if not settings.SARVAM_API_KEY:
        raise TTSUnavailableError(503, "Sarvam TTS API key is not configured.")

    payload = {
        "text": text[:450],
        "target_language_code": LANG_CODE_MAP[lang],
        "model": settings.SARVAM_TTS_MODEL,
        "speaker": settings.SARVAM_TTS_SPEAKER,
        "output_audio_codec": "mp3",
    }
    headers = {
        "api-subscription-key": settings.SARVAM_API_KEY,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.post(SARVAM_TTS_URL, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise TTSUnavailableError(502, "Failed to reach Sarvam TTS service.") from exc

    if resp.status_code >= 400:
        raise TTSUnavailableError(
            502,
            f"Sarvam TTS returned HTTP {resp.status_code}.",
        )

    data = resp.json()
    audios = data.get("audios") or []
    if not audios:
        raise TTSUnavailableError(502, "Sarvam TTS returned no audio payload.")
    return base64.b64decode(audios[0])


async def _synthesize_bhashini(text: str, lang: Literal["en", "hi", "mr"]) -> bytes:
    settings = get_settings()
    if not settings.BHASHINI_API_KEY:
        raise TTSUnavailableError(503, "Bhashini TTS credentials are not configured.")
    raise TTSUnavailableError(503, "Bhashini TTS endpoint is not configured in this environment.")


def _get_supabase_client():
    settings = get_settings()
    if settings.SUPABASE_URL and settings.SUPABASE_KEY:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return None


async def get_or_create_audio(
    notice_hash: str,
    lang: Literal["en", "hi", "mr"],
    voice_script: str,
) -> bytes:
    """Return cached MP3 bytes or synthesize and cache once per (notice_hash, lang)."""
    cache = get_cache()
    settings = get_settings()

    # 1. Check in-memory audio cache first
    mem_audio = await cache.get_memory_audio(notice_hash, lang)
    if mem_audio is not None:
        return mem_audio

    # 2. Check Supabase Storage if cached reference exists
    storage_path = f"{notice_hash}/{lang}.mp3"
    cached_ref = await cache.get_audio_ref(notice_hash, lang)
    supabase_client = _get_supabase_client()
    if cached_ref and supabase_client is not None:
        try:
            downloaded = supabase_client.storage.from_(
                settings.SUPABASE_AUDIO_BUCKET
            ).download(storage_path)
            if downloaded:
                await cache.save_memory_audio(notice_hash, lang, downloaded)
                return downloaded
        except Exception:
            pass

    # 3. Synthesize based on TTS_PROVIDER
    provider = settings.TTS_PROVIDER
    if provider == "none":
        raise TTSUnavailableError(503, "Regional voice synthesis is disabled (TTS_PROVIDER=none).")
    if not voice_script.strip():
        raise TTSUnavailableError(404, "No spoken brief available for this circular.")

    if provider == "sarvam":
        audio_bytes = await _synthesize_sarvam(voice_script.strip()[:380], lang)
    elif provider == "bhashini":
        audio_bytes = await _synthesize_bhashini(voice_script.strip()[:380], lang)
    else:
        raise TTSUnavailableError(503, f"Unsupported TTS provider: {provider}")

    # 4. Store in Supabase Storage (or memory fallback) and record cache key
    if supabase_client is not None:
        try:
            supabase_client.storage.from_(settings.SUPABASE_AUDIO_BUCKET).upload(
                path=storage_path,
                file=audio_bytes,
                file_options={"content-type": "audio/mpeg", "upsert": "true"},
            )
            await cache.save_audio_ref(notice_hash, lang, storage_path)
        except Exception:
            # Degrade smoothly to in-memory audio store if bucket upload fails
            await cache.save_audio_ref(notice_hash, lang, f"memory://{storage_path}")
    else:
        await cache.save_audio_ref(notice_hash, lang, f"memory://{storage_path}")

    await cache.save_memory_audio(notice_hash, lang, audio_bytes)
    return audio_bytes

