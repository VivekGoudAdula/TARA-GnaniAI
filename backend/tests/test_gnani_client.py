"""
Unit tests for the Gnani client with mocked HTTP.

Strategy: inject a mock `httpx.AsyncClient` by patching `httpx.AsyncClient`
directly in the gnani_client module. Each test builds a fake response and
configures the mock to return it, so no real network calls are made.

Tests cover:
  - STT success (transcript, detected language, request_id, latency)
  - TTS success (audio bytes, content_type, latency)
  - 401 → GnaniAuthError
  - 402 → GnaniPaymentError
  - 429 → GnaniRateLimitError
  - 503 transient → one retry → success
  - Malformed 200 response → empty fields, no crash
  - Missing API key → RuntimeError

Live tests (require real GNANI_API_KEY):
  - @pytest.mark.live – skipped by default
  - Run with: pytest -m live
"""
from __future__ import annotations

import importlib
import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


# ── Response builder ──────────────────────────────────────────────────────────

def _resp(status: int, body: dict | None = None, content: bytes | None = None) -> httpx.Response:
    """Build an httpx.Response with JSON body or raw binary content."""
    if content is not None:
        raw, ct = content, "audio/wav"
    else:
        raw, ct = json.dumps(body or {}).encode(), "application/json"
    return httpx.Response(status_code=status, headers={"content-type": ct}, content=raw)


# ── Patch helper ──────────────────────────────────────────────────────────────

def _patch_client(*responses: httpx.Response):
    """
    Patch `httpx.AsyncClient` in the gnani_client module so that
    `async with httpx.AsyncClient(...) as client: client.post(...)` returns
    the given responses in order.
    """
    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=list(responses))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    mock_class = MagicMock(return_value=mock_client)

    return patch("providers.gnani_client.httpx.AsyncClient", mock_class)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def set_api_key(request, monkeypatch):
    """Ensure GNANI_API_KEY is set for mocked tests, or loaded from .env for live tests."""
    if "live" in request.keywords:
        from dotenv import load_dotenv
        from pathlib import Path
        load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)
    else:
        monkeypatch.setenv("GNANI_API_KEY", "test-key-1234")


@pytest.fixture
def client():
    """Return a fresh GnaniClient."""
    from providers.gnani_client import GnaniClient
    return GnaniClient()


# ── STT success ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stt_success(client):
    """200 → transcript, detected_language_code, request_id, latency_ms."""
    ok = _resp(200, {
        "success": True,
        "transcript": "Hello world",
        "detected_language_code": "en-IN",
        "request_id": "req-abc123",
        "model": "prisma-v3.0",
    })
    with _patch_client(ok):
        result = await client.stt_transcribe(b"fake-audio", "test.wav")

    assert result["transcript"] == "Hello world"
    assert result["detected_language_code"] == "en-IN"
    assert result["request_id"] == "req-abc123"
    assert result["latency_ms"] >= 0


# ── STT auth error ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stt_auth_error(client):
    """401 raises GnaniAuthError."""
    from providers.gnani_client import GnaniAuthError

    resp = _resp(401, {"detail": {"error_code": "INVALID_API_KEY", "message": "Bad key"}})
    with _patch_client(resp):
        with pytest.raises(GnaniAuthError):
            await client.stt_transcribe(b"fake-audio", "test.wav")


# ── STT rate limit ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stt_rate_limit(client):
    """429 raises GnaniRateLimitError after retry fails with 429."""
    from providers.gnani_client import GnaniRateLimitError

    resp = _resp(429, {"detail": {"error_code": "RATE_LIMITED", "message": "Rate limited"}})
    with _patch_client(resp, resp):
        with pytest.raises(GnaniRateLimitError):
            await client.stt_transcribe(b"fake-audio", "test.wav")


# ── STT transient retry ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stt_transient_retries_once(client):
    """503 on first call → retried once → second 200 succeeds."""
    transient = _resp(503, {"detail": {"message": "Service unavailable"}})
    success = _resp(200, {
        "transcript": "retry worked",
        "detected_language_code": "en-IN",
        "request_id": "req-retry",
    })
    with _patch_client(transient, success):
        result = await client.stt_transcribe(b"fake-audio", "test.wav")

    assert result["transcript"] == "retry worked"


# ── STT malformed response ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stt_malformed_response_returns_empty_fields(client):
    """Empty 200 JSON → empty strings, no crash."""
    resp = _resp(200, {})
    with _patch_client(resp):
        result = await client.stt_transcribe(b"fake-audio", "test.wav")

    assert result["transcript"] == ""
    assert result["detected_language_code"] == "indic-auto"


# ── TTS success ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tts_success(client):
    """200 → raw audio bytes, content_type, latency_ms."""
    resp = _resp(200, content=b"RIFF....fake-wav-bytes")
    with _patch_client(resp):
        audio_bytes, content_type, latency_ms = await client.tts_synthesize(
            text="Hello", language_code="en-IN", voice="Nalini"
        )

    assert audio_bytes == b"RIFF....fake-wav-bytes"
    assert content_type == "audio/wav"
    assert latency_ms >= 0


# ── TTS payment error ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tts_payment_error(client):
    """402 raises GnaniPaymentError."""
    from providers.gnani_client import GnaniPaymentError

    resp = _resp(402, {"detail": {"message": "Insufficient credits"}})
    with _patch_client(resp):
        with pytest.raises(GnaniPaymentError):
            await client.tts_synthesize("Hello", "en-IN", "Nalini")


# ── Missing API key ───────────────────────────────────────────────────────────

def test_missing_api_key_raises(monkeypatch):
    """GnaniClient raises RuntimeError when GNANI_API_KEY is not set."""
    monkeypatch.delenv("GNANI_API_KEY", raising=False)
    with patch("dotenv.load_dotenv"):
        import providers.gnani_client as mod
        importlib.reload(mod)
        with pytest.raises(RuntimeError, match="GNANI_API_KEY"):
            mod.GnaniClient()


# ── Live tests (skipped by default) ──────────────────────────────────────────

@pytest.mark.live
@pytest.mark.asyncio
async def test_live_tts_english():
    """LIVE: TTS English – requires real GNANI_API_KEY in env."""
    from providers.gnani_client import GnaniClient
    c = GnaniClient()
    audio, ctype, latency = await c.tts_synthesize(
        "Hello, this is a live test.", "en-IN", "Nalini"
    )
    assert len(audio) > 1000
    assert "audio" in ctype
    print(f"\nLive TTS English latency: {latency} ms")


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_stt_english():
    """LIVE: STT round-trip – synthesise then transcribe English."""
    from providers.gnani_client import GnaniClient
    c = GnaniClient()
    audio, _, _ = await c.tts_synthesize(
        "Hello this is a live test", "en-IN", "Nalini"
    )
    result = await c.stt_transcribe(audio, "live_test.wav", "en-IN")
    assert len(result["transcript"]) > 0
    print(f"\nLive STT transcript: {result['transcript']}")
    print(f"Live STT latency: {result['latency_ms']} ms")
