"""
Gnani AI API client – the ONLY place in the codebase that knows
Gnani-specific field names, URLs, and response shapes.

Covers:
  - STT  via Prisma v3.0  (POST /stt/v3)
  - TTS  via Timbre v2.5  (POST /api/v1/tts/inference)

All field names come from docs.gnani.ai (verified 2026-11-02).
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Constants (from docs) ────────────────────────────────────────────────────
_BASE_URL = "https://api.vachana.ai"
_STT_PATH = "/stt/v3"
_TTS_PATH = "/api/v1/tts/inference"

_DEFAULT_STT_MODEL = "prisma-v3.0"
_DEFAULT_TTS_MODEL = "timbre-v2.5"
_DEFAULT_LANGUAGE = "indic-auto"
_DEFAULT_VOICE = "Nalini"

_TIMEOUT_SECONDS = 30.0
_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


# ── Custom exceptions ─────────────────────────────────────────────────────────

class GnaniAPIError(Exception):
    """Base exception for all Gnani API errors."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class GnaniAuthError(GnaniAPIError):
    """Raised on 401 (MISSING_API_KEY / INVALID_API_KEY)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=401)


class GnaniScopeError(GnaniAPIError):
    """Raised on 403 (SCOPE_NOT_ALLOWED)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=403)


class GnaniPaymentError(GnaniAPIError):
    """Raised on 402 (insufficient credits)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=402)


class GnaniRateLimitError(GnaniAPIError):
    """Raised on 429 (RATE_LIMITED)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=429)


class GnaniTransientError(GnaniAPIError):
    """Raised on 5xx – safe to retry once."""


# ── Helper ────────────────────────────────────────────────────────────────────

def _raise_for_gnani_status(response: httpx.Response) -> None:
    """Map Gnani HTTP error codes to typed exceptions (from docs Error Reference)."""
    code = response.status_code
    if code == 200:
        return
    try:
        detail = response.json().get("detail", {})
        msg = detail.get("message", response.text) if isinstance(detail, dict) else str(detail)
    except Exception:
        msg = response.text

    if code == 401:
        raise GnaniAuthError(msg)
    if code == 402:
        raise GnaniPaymentError(msg)
    if code == 403:
        raise GnaniScopeError(msg)
    if code == 429:
        raise GnaniRateLimitError(msg)
    if code in _TRANSIENT_STATUS_CODES:
        raise GnaniTransientError(msg, status_code=code)
    raise GnaniAPIError(f"HTTP {code}: {msg}", status_code=code)


# ── Client ────────────────────────────────────────────────────────────────────

class GnaniClient:
    """
    Thin async wrapper around the Gnani REST APIs.

    The API key is read from the GNANI_API_KEY environment variable
    and is never logged.
    """

    def __init__(self) -> None:
        api_key = os.getenv("GNANI_API_KEY", "")
        if not api_key:
            raise RuntimeError("GNANI_API_KEY environment variable is not set.")
        # Store key privately; never expose in __repr__ or logs
        self._headers = {"X-API-Key-ID": api_key}

    def _make_client(self) -> httpx.AsyncClient:
        """Return a configured async HTTP client."""
        return httpx.AsyncClient(
            base_url=_BASE_URL,
            headers=self._headers,
            timeout=_TIMEOUT_SECONDS,
        )

    async def stt_transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language_code: str = _DEFAULT_LANGUAGE,
    ) -> dict[str, Any]:
        """
        Transcribe audio using Gnani Prisma v3.0.

        Args:
            audio_bytes: Raw audio file content.
            filename: Original filename (used to infer MIME type).
            language_code: BCP-47 code or 'indic-auto' for auto-detection.

        Returns:
            Dict with keys: transcript, detected_language_code, request_id, latency_ms.
        """
        files = {"audio_file": (filename, audio_bytes)}
        data = {"model": _DEFAULT_STT_MODEL, "language_code": language_code}

        async def _call(client: httpx.AsyncClient) -> httpx.Response:
            return await client.post(_STT_PATH, files=files, data=data)

        t0 = time.perf_counter()
        async with self._make_client() as client:
            response = await _call(client)
            # One retry on transient errors
            if response.status_code in _TRANSIENT_STATUS_CODES:
                logger.warning("Gnani STT transient error %s – retrying once", response.status_code)
                response = await _call(client)

        latency_ms = (time.perf_counter() - t0) * 1000
        _raise_for_gnani_status(response)

        payload = response.json()
        return {
            "transcript": payload.get("transcript", ""),
            "detected_language_code": payload.get("detected_language_code", language_code),
            "request_id": payload.get("request_id", ""),
            "latency_ms": round(latency_ms, 1),
        }

    async def tts_synthesize(
        self,
        text: str,
        language_code: str,
        voice: str = _DEFAULT_VOICE,
    ) -> tuple[bytes, str, float]:
        """
        Synthesise speech using Gnani Timbre v2.5.

        Args:
            text: Text to synthesise.
            language_code: BCP-47 language code (e.g. 'en-IN', 'hi-IN', 'te-IN').
            voice: Voice name from the Timbre v2.5 catalog (e.g. 'Nalini').

        Returns:
            Tuple of (audio_bytes, content_type, latency_ms).
        """
        payload = {
            "text": text,
            "model": _DEFAULT_TTS_MODEL,
            "voice": voice,
            "language": language_code,
            "speed": 1.0,
            "audio_config": {
                "sample_rate": 48000,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        }

        async def _call(client: httpx.AsyncClient) -> httpx.Response:
            return await client.post(_TTS_PATH, json=payload)

        t0 = time.perf_counter()
        async with self._make_client() as client:
            response = await _call(client)
            if response.status_code in _TRANSIENT_STATUS_CODES:
                logger.warning("Gnani TTS transient error %s – retrying once", response.status_code)
                response = await _call(client)

        latency_ms = (time.perf_counter() - t0) * 1000
        _raise_for_gnani_status(response)

        content_type = response.headers.get("content-type", "audio/wav")
        return response.content, content_type, round(latency_ms, 1)

