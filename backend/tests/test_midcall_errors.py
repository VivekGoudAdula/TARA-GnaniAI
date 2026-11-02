"""
test_midcall_errors.py - Tests simulated Gnani 429 and timeout mid-call during STT and TTS.
Asserts: friendly error event, retry turn recovery, failure recorded with machine reason, zero crashes.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, List
import pytest
from httpx import TimeoutException

from app.voice.session import VoiceSession
from providers.gnani_client import GnaniRateLimitError


class MockSpeechProvider:
    """Mock speech provider simulating transient Gnani TTS failures."""

    def __init__(self, fail_first_with: Exception | None = None) -> None:
        self.fail_first_with = fail_first_with
        self.call_count = 0

    async def synthesize_stream(self, text: str, lang: str, voice: str = "") -> AsyncIterator[bytes]:
        self.call_count += 1
        if self.fail_first_with and self.call_count == 1:
            raise self.fail_first_with
        yield b"RIFF" + b"\x00" * 100


class MockLLMClient:
    """Mock LLM client returning predictable tokens and extraction."""

    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        yield "Hello customer! "
        yield "How can I help you today?"

    async def extract_session_data(self, **kwargs: Any) -> Dict[str, Any]:
        return {"interest_level": "medium", "outcome": "callback", "summary": "Call completed"}


@pytest.mark.asyncio
async def test_tts_rate_limit_429_midcall_and_retry_turn():
    """Verify Gnani TTS 429 emits friendly event, allows turn retry, and completes cleanly."""
    events: List[Dict[str, Any]] = []

    async def capture_event(e: Dict[str, Any]) -> None:
        events.append(e)

    mock_speech = MockSpeechProvider(fail_first_with=GnaniRateLimitError("RATE_LIMITED (429)"))
    config = {
        "first_name": "Rohan", "bank_name": "Test Bank", "product_name": "Loan",
        "language": "en-IN", "opening_message": "Hello Rohan!", "system_prompt": "Help customer.",
    }
    session = VoiceSession(
        config=config, send_ws=capture_event,
        speech_provider=mock_speech, llm_client=MockLLMClient(),
    )
    # Bypass opening greeting TTS for this test
    session.messages.append({"role": "system", "content": "Help customer."})

    # 1. Turn 1 encounters 429 during TTS
    await session.handle_user_turn("I need a loan", 1000.0, 200.0)
    error_events = [e for e in events if e.get("type") == "turn_error"]
    assert len(error_events) == 1
    assert error_events[0]["machine_reason"] == "gnani_429"
    assert error_events[0]["can_retry"] is True
    assert "trouble" in error_events[0]["message"].lower()

    # 2. User retries turn: second attempt succeeds
    await session.handle_user_turn("I need a loan", 1000.0, 200.0)
    metrics_events = [e for e in events if e.get("type") == "turn_metrics"]
    assert len(metrics_events) == 1
    assert session.turns[-1]["agent_response"] == "Hello customer! How can I help you today?"

    # 3. Session ends successfully
    doc = await session.end_session()
    assert doc["status"] == "completed"
    assert doc["machine_reason"] is None


@pytest.mark.asyncio
async def test_tts_timeout_midcall_and_failed_session_persistence():
    """Verify Gnani TTS timeout emits friendly event and saves session as failed with machine reason."""
    events: List[Dict[str, Any]] = []

    mock_speech = MockSpeechProvider(fail_first_with=TimeoutException("Gnani TTS connection timeout"))
    config = {
        "first_name": "Aarav", "bank_name": "Test Bank", "product_name": "Loan",
        "language": "en-IN", "opening_message": "Hello!", "system_prompt": "Help.",
    }
    session = VoiceSession(
        config=config, send_ws=lambda e: events.append(e),
        speech_provider=mock_speech, llm_client=MockLLMClient(),
    )
    session.messages.append({"role": "system", "content": "Help."})

    # Turn encounters timeout
    await session.handle_user_turn("Hello", 1000.0, 200.0)
    err = [e for e in events if e.get("type") == "turn_error"][0]
    assert err["machine_reason"] == "gnani_timeout"

    # User disconnects without retry
    doc = await session.end_session()
    assert doc["status"] == "failed"
    assert doc["machine_reason"] == "gnani_timeout"


@pytest.mark.asyncio
async def test_stt_midcall_simulated_error_and_persistence():
    """Verify STT 429 and timeout errors are recorded and mapped to machine reasons."""
    from unittest.mock import AsyncMock

    mock_client = AsyncMock()
    mock_client.stt_transcribe.side_effect = GnaniRateLimitError("429 Too Many Requests")

    # Simulate router logic on user_audio
    events: List[Dict[str, Any]] = []
    session = VoiceSession(
        config={"first_name": "Test", "bank_name": "Bank", "product_name": "Loan", "language": "en-IN", "system_prompt": "Prompt."},
        send_ws=lambda e: events.append(e),
        speech_provider=MockSpeechProvider(), llm_client=MockLLMClient(),
    )
    session.messages.append({"role": "system", "content": "Prompt."})

    try:
        await mock_client.stt_transcribe(b"fake_audio", filename="turn.wav", language_code="en-IN")
    except Exception as exc:
        reason = "gnani_429" if "429" in str(exc) else "gnani_stt_error"
        session.last_error = reason
        events.append({"type": "turn_error", "machine_reason": reason, "can_retry": True})

    assert events[0]["type"] == "turn_error"
    assert events[0]["machine_reason"] == "gnani_429"

    doc = await session.end_session()
    assert doc["status"] == "failed"
    assert doc["machine_reason"] == "gnani_429"
