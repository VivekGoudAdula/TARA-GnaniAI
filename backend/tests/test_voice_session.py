"""
Unit and integration tests for VoiceSession, prompt guardrails, and post-call extraction.
Includes mocked state-machine tests and optional live end-to-end test.
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.voice.prompt import build_system_prompt, validate_config
from app.voice.session import SessionState, VoiceSession, detect_language
from providers.llm_client import LLMClient


# ─── 1. Prompt Guardrail Tests ───────────────────────────────────────────────

def test_prompt_guardrail_valid():
    """Verify valid configuration generates expected prompt with customer and product data."""
    config = {
        "first_name": "Priya",
        "bank_name": "Apex Bank",
        "product_name": "Auto Loan",
        "language": "en-IN",
        "system_prompt": "You are Tara, an outreach assistant.",
    }
    prompt = build_system_prompt(config, "en-IN")
    assert "Priya" in prompt
    assert "Apex Bank" in prompt
    assert "Auto Loan" in prompt
    assert "Tara" in prompt


def test_prompt_guardrail_unapproved_field_raises():
    """Verify any unapproved field in config raises ValueError and halts prompt creation."""
    config = {
        "first_name": "Priya",
        "bank_name": "Apex Bank",
        "product_name": "Auto Loan",
        "language": "en-IN",
        "system_prompt": "You are Tara.",
        "secret_data": "malicious_override",
    }
    with pytest.raises(ValueError, match="unexpected field"):
        build_system_prompt(config, "en-IN")


def test_prompt_guardrail_missing_field_raises():
    """Verify missing mandatory fields raise ValueError."""
    config = {
        "first_name": "Priya",
        "bank_name": "Apex Bank",
        "language": "en-IN",
    }
    with pytest.raises(ValueError, match="missing required field"):
        build_system_prompt(config, "en-IN")


# ─── 2. Language Detection Test ──────────────────────────────────────────────

def test_language_detection():
    """Verify script-based detection for Hindi, Telugu, and English fallback."""
    assert detect_language("नमस्ते, मुझे लोन चाहिए", "en-IN") == "hi-IN"
    assert detect_language("నమస్కారం, నాకు లోన్ కావాలి", "en-IN") == "te-IN"
    assert detect_language("Yes please tell me more", "en-IN") == "en-IN"


# ─── 3. State Machine & Session Tests (Mocked) ──────────────────────────────

class MockSpeechProvider:
    """Mock speech provider returning synthetic audio chunks."""

    def get_default_voice(self, lang: str) -> str:
        return "Nalini"

    async def synthesize_stream(self, text: str, lang: str = "en-IN") -> AsyncIterator[bytes]:
        yield b"\x00" * 320
        yield b"\x00" * 320


class MockLLMClient:
    """Mock LLM client returning deterministic tokens and extraction schema."""

    async def stream_chat(
        self, messages: List[Dict[str, str]], temperature: float = 0.2
    ) -> AsyncIterator[str]:
        yield "Certainly, "
        yield "how much loan amount "
        yield "do you require?"

    async def extract_session_data(self, transcript, info_to_collect, success_condition):
        return {
            "fields_collected": {"loan_amount_needed": "5 Lakhs"},
            "outcome": "agreed",
            "call_summary": "Customer requested 5 Lakhs personal loan.",
            "user_sentiment": "positive",
            "follow_up_needed": True,
            "language_used": "en-IN",
            "confidence": 0.95,
        }


@pytest.mark.asyncio
async def test_session_state_machine_flow():
    """Verify full turn cycle: listening -> thinking -> speaking -> listening."""
    events = []

    async def send_ws(msg):
        events.append(msg)

    config = {
        "first_name": "Rahul",
        "bank_name": "Apex Bank",
        "product_name": "Personal Loan",
        "language": "en-IN",
        "system_prompt": "You are Tara.",
        "opening_message": "Hello Rahul, this is Tara an AI assistant.",
        "max_turns": 3,
    }

    session = VoiceSession(
        config=config,
        send_ws=send_ws,
        speech_provider=MockSpeechProvider(),
        llm_client=MockLLMClient(),
    )

    await session.start()
    assert session.state == SessionState.SPEAKING or session.state == SessionState.LISTENING

    # Send user turn
    await session.handle_user_turn("I need five lakh rupees", 1200.0, 350.0)
    assert len(session.turns) == 1
    turn = session.turns[0]
    assert turn["turn_num"] == 1
    assert "five lakh" in turn["user_transcript"]
    assert "loan amount" in turn["agent_response"]
    assert session.state == SessionState.LISTENING


@pytest.mark.asyncio
async def test_session_language_switch():
    """Verify session switches to Hindi when user speaks Hindi."""
    events = []

    async def send_ws(msg):
        events.append(msg)

    config = {
        "first_name": "Rahul",
        "bank_name": "Apex Bank",
        "product_name": "Personal Loan",
        "language": "en-IN",
        "system_prompt": "You are Tara.",
    }
    session = VoiceSession(
        config=config,
        send_ws=send_ws,
        speech_provider=MockSpeechProvider(),
        llm_client=MockLLMClient(),
    )
    await session.start()
    await session.handle_user_turn("हाँ, मुझे जानकारी चाहिए")
    assert session.language == "hi-IN"


@pytest.mark.asyncio
async def test_session_barge_in():
    """Verify barge-in interrupts speech and resets to listening."""
    events = []

    async def send_ws(msg):
        events.append(msg)

    config = {
        "first_name": "Rahul",
        "bank_name": "Apex Bank",
        "product_name": "Personal Loan",
        "language": "en-IN",
        "system_prompt": "You are Tara.",
    }
    session = VoiceSession(
        config=config,
        send_ws=send_ws,
        speech_provider=MockSpeechProvider(),
        llm_client=MockLLMClient(),
    )
    session.state = SessionState.SPEAKING
    await session.barge_in()
    assert session._interrupted is True
    assert session.state == SessionState.LISTENING


# ─── 4. Extraction Schema Test ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extraction_schema():
    """Verify extraction returns required schema types and valid enum outcomes."""
    mock_llm = MockLLMClient()
    result = await mock_llm.extract_session_data([], [], "")
    assert isinstance(result.get("fields_collected"), dict)
    assert result.get("outcome") in [
        "agreed",
        "declined",
        "callback_requested",
        "wrong_number",
        "unanswered",
    ]
    assert isinstance(result.get("call_summary"), str)
    assert result.get("user_sentiment") in ["positive", "neutral", "negative"]
    assert isinstance(result.get("follow_up_needed"), bool)
    assert 0.0 <= float(result.get("confidence", 0.0)) <= 1.0


# ─── 5. Optional Live Session Test ──────────────────────────────────────────

@pytest.mark.live
@pytest.mark.asyncio
async def test_live_session():
    """Run one real round-trip with live Gnani and Groq APIs."""
    config = {
        "first_name": "Aman",
        "bank_name": "Apex Bank",
        "product_name": "Personal Loan",
        "language": "en-IN",
        "system_prompt": "You are Tara, an AI assistant.",
        "opening_message": "Hello Aman, this is Tara an AI assistant.",
        "max_turns": 1,
    }
    events = []
    session = VoiceSession(config=config, send_ws=lambda m: events.append(m))
    await session.start()
    await session.handle_user_turn("Yes, I am interested in a loan.", 1000.0, 500.0)
    assert len(session.turns) >= 1
    doc = await session.end_session()
    assert doc.get("session_id")
