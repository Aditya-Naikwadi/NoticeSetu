"""SSRF-hardened URL fetching and strict magic-byte validation in io.BytesIO."""

import asyncio
from collections import defaultdict, deque
import hashlib
import ipaddress
import io
import socket
import time
from typing import Literal
from urllib.parse import urljoin, urlparse

import httpx

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_REDIRECTS = 3
FETCH_TIMEOUT_SECONDS = 15.0


class SlidingWindowRateLimiter:
    """In-memory per-client rate limiter keyed by ephemeral SHA-256 of client IP."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def check(self, client_ip: str, max_requests: int, window_seconds: int) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds
        key = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:24]

        async with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= max_requests:
                raise SecurityValidationError(
                    status_code=429,
                    code="RATE_LIMIT_EXCEEDED",
                    message="Too many requests. Please wait a minute and try again.",
                )
            bucket.append(now)

    def reset_for_tests(self) -> None:
        self._hits.clear()


_rate_limiter = SlidingWindowRateLimiter()


def get_rate_limiter() -> SlidingWindowRateLimiter:
    """Return shared rate limiter singleton."""
    return _rate_limiter


class SecurityValidationError(Exception):
    """Structured security or input validation failure mapped cleanly to HTTP status."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def validate_file_bytes(data: bytes) -> Literal["pdf", "jpeg", "png"]:
    """Validate payload size (<= 10 MB) and inspect magic bytes strictly."""
    if not data:
        raise SecurityValidationError(
            status_code=400,
            code="EMPTY_FILE",
            message="Uploaded file is empty. Please upload a valid PDF, JPEG, or PNG.",
        )
    if len(data) > MAX_FILE_BYTES:
        raise SecurityValidationError(
            status_code=413,
            code="FILE_TOO_LARGE",
            message="File exceeds the 10 MB limit. Please upload a smaller PDF or image.",
        )

    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"

    raise SecurityValidationError(
        status_code=400,
        code="INVALID_FILE_TYPE",
        message="Unsupported file format. Upload a PDF, JPEG, or PNG under 10 MB.",
    )


def _is_disallowed_ip(ip_str: str) -> bool:
    """Return True if IP falls in any non-public or special-purpose address range."""
    ip = ipaddress.ip_address(ip_str)
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


async def _validate_url_and_dns(url: str) -> str:
    """Validate URL scheme/port and ensure all resolved DNS IPs are globally routable."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise SecurityValidationError(
            status_code=400,
            code="INVALID_URL_SCHEME",
            message="Only http:// and https:// public notice URLs are allowed.",
        )
    if parsed.username or parsed.password:
        raise SecurityValidationError(
            status_code=400,
            code="INVALID_URL_CREDENTIALS",
            message="URLs containing embedded credentials are not allowed.",
        )
    hostname = parsed.hostname
    if not hostname:
        raise SecurityValidationError(
            status_code=400,
            code="INVALID_URL_HOST",
            message="URL must include a valid public domain name.",
        )

    port = parsed.port
    if port is not None and port not in {80, 443}:
        raise SecurityValidationError(
            status_code=400,
            code="INVALID_URL_PORT",
            message="Only standard ports 80 and 443 are permitted.",
        )
    effective_port = port or (443 if parsed.scheme == "https" else 80)

    # Check literal IP hostnames before DNS lookup
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if _is_disallowed_ip(hostname):
            raise SecurityValidationError(
                status_code=400,
                code="SSRF_BLOCKED",
                message="Private, loopback, or metadata IP addresses cannot be fetched.",
            )

    try:
        addr_info = await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            effective_port,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise SecurityValidationError(
            status_code=400,
            code="DNS_RESOLUTION_FAILED",
            message="Could not resolve the notice URL domain name.",
        ) from exc

    if not addr_info:
        raise SecurityValidationError(
            status_code=400,
            code="DNS_RESOLUTION_FAILED",
            message="No network addresses found for the notice URL.",
        )

    for entry in addr_info:
        resolved_ip = entry[4][0]
        if _is_disallowed_ip(resolved_ip):
            raise SecurityValidationError(
                status_code=400,
                code="SSRF_BLOCKED",
                message="Resolved network address is restricted and cannot be fetched.",
            )

    return url.strip()


async def safe_fetch_url(url: str) -> tuple[bytes, str]:
    """Fetch a public circular URL into io.BytesIO with strict SSRF and 10 MB guards."""
    current_url = await _validate_url_and_dns(url)

    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=httpx.Timeout(FETCH_TIMEOUT_SECONDS),
    ) as client:
        for hop in range(MAX_REDIRECTS + 1):
            try:
                async with client.stream(
                    "GET",
                    current_url,
                    headers={"User-Agent": "NoticeSetu/1.0 (+https://noticesetu.in)"},
                ) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        if hop >= MAX_REDIRECTS:
                            raise SecurityValidationError(
                                status_code=400,
                                code="TOO_MANY_REDIRECTS",
                                message="Notice URL exceeded maximum allowed redirects.",
                            )
                        location = response.headers.get("location")
                        if not location:
                            raise SecurityValidationError(
                                status_code=502,
                                code="UPSTREAM_REDIRECT_ERROR",
                                message="Remote server returned an empty redirect target.",
                            )
                        next_url = urljoin(current_url, location)
                        current_url = await _validate_url_and_dns(next_url)
                        continue

                    if response.status_code >= 400:
                        raise SecurityValidationError(
                            status_code=502,
                            code="UPSTREAM_FETCH_ERROR",
                            message=f"Remote notice server returned HTTP {response.status_code}.",
                        )

                    content_length_hdr = response.headers.get("content-length")
                    if content_length_hdr:
                        try:
                            if int(content_length_hdr) > MAX_FILE_BYTES:
                                raise SecurityValidationError(
                                    status_code=413,
                                    code="FILE_TOO_LARGE",
                                    message="Remote file exceeds the 10 MB size limit.",
                                )
                        except ValueError:
                            pass

                    buffer = io.BytesIO()
                    total_bytes = 0
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        total_bytes += len(chunk)
                        if total_bytes > MAX_FILE_BYTES:
                            raise SecurityValidationError(
                                status_code=413,
                                code="FILE_TOO_LARGE",
                                message="Remote file exceeded the 10 MB size limit while downloading.",
                            )
                        buffer.write(chunk)

                    content_type = response.headers.get("content-type", "")
                    return buffer.getvalue(), content_type

            except httpx.TimeoutException as exc:
                raise SecurityValidationError(
                    status_code=502,
                    code="UPSTREAM_TIMEOUT",
                    message="Timed out while downloading the circular URL.",
                ) from exc
            except httpx.RequestError as exc:
                raise SecurityValidationError(
                    status_code=502,
                    code="UPSTREAM_REQUEST_ERROR",
                    message="Network error while connecting to the circular URL.",
                ) from exc

    raise SecurityValidationError(
        status_code=400,
        code="TOO_MANY_REDIRECTS",
        message="Notice URL exceeded maximum allowed redirects.",
    )

