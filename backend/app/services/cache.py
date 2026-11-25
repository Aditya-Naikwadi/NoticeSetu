"""Two-tier Upstash Redis cache with 14-day TTL and zero-config in-memory fallback."""

import asyncio
import json
import time
from typing import Any, Literal

from upstash_redis.asyncio import Redis

from app.config import get_settings
from app.schemas import ActionCardResponse

TTL_SECONDS = 14 * 24 * 60 * 60  # 1,209,600 seconds (14 days)
PHASH_MAX_HAMMING = 4
PHASH_INDEX_LIMIT = 200


class NoticeCache:
    """Async cache supporting Tier-1 SHA-256 and Tier-2 normalized-text/pHash lookups."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._mem_kv: dict[str, tuple[str, float]] = {}
        self._mem_audio: dict[str, tuple[bytes, float]] = {}
        self._redis: Redis | None = None
        self._redis_checked = False

    def _get_redis(self) -> Redis | None:
        if not self._redis_checked:
            settings = get_settings()
            if settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN:
                self._redis = Redis(
                    url=settings.UPSTASH_REDIS_REST_URL,
                    token=settings.UPSTASH_REDIS_REST_TOKEN,
                )
            self._redis_checked = True
        return self._redis

    @property
    def backend_status(self) -> str:
        return "connected" if self._get_redis() is not None else "memory_fallback"

    async def _get_str(self, key: str) -> str | None:
        redis = self._get_redis()
        if redis is not None:
            val = await redis.get(key)
            if val is None:
                return None
            return val if isinstance(val, str) else json.dumps(val)

        async with self._lock:
            entry = self._mem_kv.get(key)
            if entry is None:
                return None
            val, expires_at = entry
            if time.monotonic() >= expires_at:
                self._mem_kv.pop(key, None)
                return None
            return val

    async def _set_str(self, key: str, value: str, ex: int = TTL_SECONDS) -> None:
        redis = self._get_redis()
        if redis is not None:
            await redis.set(key, value, ex=ex)
            return

        async with self._lock:
            self._mem_kv[key] = (value, time.monotonic() + ex)

    async def get_by_sha256(
        self, raw_sha256: str
    ) -> tuple[ActionCardResponse | None, str]:
        """Look up Tier-1 SHA-256 notice entry and its source text."""
        raw = await self._get_str(f"notice:sha256:{raw_sha256}")
        if not raw:
            return None, ""
        payload: dict[str, Any] = json.loads(raw)
        card = ActionCardResponse.model_validate(payload["card"])
        card.cache_hit = True
        card.cache_tier = "tier1_sha256"
        return card, payload.get("source_text", "")

    async def get_by_text_hash(
        self, normalized_text_sha256: str
    ) -> tuple[ActionCardResponse | None, str]:
        """Look up Tier-2 normalized-text pointer for re-saved digital PDFs."""
        canonical_hash = await self._get_str(f"notice:text:{normalized_text_sha256}")
        if not canonical_hash:
            return None, ""
        card, source_text = await self.get_by_sha256(canonical_hash)
        if card is None:
            return None, ""
        card.cache_hit = True
        card.cache_tier = "tier2_text"
        return card, source_text

    async def get_by_phash(
        self, phash_hex: str
    ) -> tuple[ActionCardResponse | None, str]:
        """Look up Tier-2 perceptual image hash (exact or Hamming distance <= 4)."""
        exact_hash = await self._get_str(f"notice:phash:{phash_hex}")
        target_sha256 = exact_hash

        if not target_sha256:
            index_raw = await self._get_str("notice:phash:index")
            if index_raw:
                try:
                    entries: list[dict[str, str]] = json.loads(index_raw)
                    incoming_int = int(phash_hex, 16)
                    best_dist = PHASH_MAX_HAMMING + 1
                    for item in entries:
                        candidate_hex = item.get("phash", "")
                        if not candidate_hex:
                            continue
                        dist = (incoming_int ^ int(candidate_hex, 16)).bit_count()
                        if dist <= PHASH_MAX_HAMMING and dist < best_dist:
                            best_dist = dist
                            target_sha256 = item.get("sha256")
                except (ValueError, TypeError):
                    target_sha256 = None

        if not target_sha256:
            return None, ""

        card, source_text = await self.get_by_sha256(target_sha256)
        if card is None:
            return None, ""
        card.cache_hit = True
        card.cache_tier = "tier2_phash"
        return card, source_text

    async def save_notice(
        self,
        card: ActionCardResponse,
        source_text: str,
        normalized_text_sha256: str | None = None,
        phash_hex: str | None = None,
    ) -> None:
        """Persist ActionCardResponse and Tier-2 lookup indices for 14 days."""
        stored_card = card.model_copy(update={"cache_hit": False, "cache_tier": "miss"})
        envelope = json.dumps(
            {
                "card": stored_card.model_dump(mode="json"),
                "source_text": source_text,
            },
            ensure_ascii=False,
        )
        await self._set_str(f"notice:sha256:{card.notice_hash}", envelope, ex=TTL_SECONDS)
        await self._set_str(
            f"notice:prefix:{card.notice_hash[:16]}",
            card.notice_hash,
            ex=TTL_SECONDS,
        )

        if normalized_text_sha256:
            await self._set_str(
                f"notice:text:{normalized_text_sha256}",
                card.notice_hash,
                ex=TTL_SECONDS,
            )

        if phash_hex:
            await self._set_str(
                f"notice:phash:{phash_hex}",
                card.notice_hash,
                ex=TTL_SECONDS,
            )
            index_raw = await self._get_str("notice:phash:index")
            entries: list[dict[str, str]] = []
            if index_raw:
                try:
                    entries = json.loads(index_raw)
                except ValueError:
                    entries = []
            entries = [
                e for e in entries if e.get("phash") != phash_hex
            ][-(PHASH_INDEX_LIMIT - 1) :]
            entries.append({"phash": phash_hex, "sha256": card.notice_hash})
            await self._set_str(
                "notice:phash:index",
                json.dumps(entries),
                ex=TTL_SECONDS,
            )

    async def resolve_hash_prefix(self, prefix: str) -> str | None:
        """Resolve a 16-char hash prefix (from Telegram callback_data) to full SHA-256."""
        if len(prefix) == 64:
            return prefix
        return await self._get_str(f"notice:prefix:{prefix[:16]}")

    async def get_audio_ref(self, notice_hash: str, lang: str) -> str | None:
        return await self._get_str(f"audio:url:{notice_hash}:{lang}")

    async def save_audio_ref(self, notice_hash: str, lang: str, ref: str) -> None:
        await self._set_str(f"audio:url:{notice_hash}:{lang}", ref, ex=TTL_SECONDS)

    async def get_memory_audio(self, notice_hash: str, lang: str) -> bytes | None:
        key = f"{notice_hash}:{lang}"
        async with self._lock:
            entry = self._mem_audio.get(key)
            if entry is None:
                return None
            audio_bytes, expires_at = entry
            if time.monotonic() >= expires_at:
                self._mem_audio.pop(key, None)
                return None
            return audio_bytes

    async def save_memory_audio(self, notice_hash: str, lang: str, audio_bytes: bytes) -> None:
        key = f"{notice_hash}:{lang}"
        async with self._lock:
            self._mem_audio[key] = (audio_bytes, time.monotonic() + TTL_SECONDS)

    def clear_memory_for_tests(self) -> None:
        """Reset in-memory stores for isolated pytest runs."""
        self._mem_kv.clear()
        self._mem_audio.clear()


_cache_instance = NoticeCache()


def get_cache() -> NoticeCache:
    """Return shared NoticeCache singleton."""
    return _cache_instance

