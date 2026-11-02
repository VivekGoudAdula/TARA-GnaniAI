"""
Unit and integration tests for VoiceSession, prompt guardrails, and post-call extraction.
Includes mocked state-machine tests and optional live end-to-end test.
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, Dict, List
import pytest

from app.voice.prompt import build_system_prompt
from app.voice.session import SessionState, VoiceSession, detect_language
from providers.llm_client import SessionExtraction


def test_prompt_guardrail_valid():
    """Verify valid configuration generates expected prompt with customer and product data."""
    config = {
        "first_name": "Priya",
        "bank_name": "Apex Bank",
        "product_name": "Auto Loan",
        "language": "en-IN",
        "system_prompt": "You are Tara.",
    }
    prompt = build_system_prompt(config, "en-IN")
    assert "Priya" in prompt and "Apex Bank" in prompt and "Auto Loan" in prompt


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


def test_language_detection():
    """Verify script-based, STT-detected, and Romanised Hinglish detection."""
    assert detect_language("नमस्ते, मुझे लोन चाहिए", "en-IN") == "hi-IN"
    assert detect_language("నమస్కారం, నాకు లోన్ కావాలి", "en-IN") == "te-IN"
    assert detect_language("Yes please tell me more", "en-IN") == "en-IN"
    # STT detected code priority
    assert detect_language("anything", "en-IN", stt_detected="te-IN") == "te-IN"
    # Romanised Hinglish detection
    assert detect_language("haan mujhe personal loan chahiye", "en-IN") == "hi-IN"


class MockSpeechProvider:
    """Mock speech provider returning synthetic audio chunks."""

    def get_default_voice(self, lang: str) -> str:
        return "Nalini"

    async def synthesize_stream(self, text: str, lang: str = "en-IN", voice: str = "Nalini") -> AsyncIterator[bytes]:
        yield b"\x00" * 320


class MockLLMClient:
    """Mock LLM client returning deterministic tokens and extraction schema."""

    async def stream_chat(
        self, messages: List[Dict[str, str]], temperature: float = 0.2
    ) -> AsyncIterator[str]:
        yield "Certainly. "
        yield "How much loan amount do you need?"

    async def extract_session_data(self, transcript, info_to_collect=None, success_condition=None):
        return {
            "interest_level": "high",
            "loan_amount_inr": 100000.0,
            "callback_time": "tomorrow at 5pm",
            "language_used": ["hi-IN", "en-IN"],
            "outcome": "interested",
            "summary": "Customer requested 1 lakh loan with a callback.",
        }


@pytest.mark.asyncio
async def test_session_state_machine_flow():
    """Verify full turn cycle: listening -> thinking -> speaking -> listening."""
    events = []
    config = {
        "first_name": "Rahul",
        "bank_name": "Apex Bank",
        "product_name": "Personal Loan",
        "language": "en-IN",
        "system_prompt": "You are Tara.",
        "opening_message": "Hello Rahul, this is Tara.",
        "max_turns": 3,
    }
    session = VoiceSession(
        config=config,
        send_ws=lambda m: events.append(m),
        speech_provider=MockSpeechProvider(),
        llm_client=MockLLMClient(),
    )
    await session.start()
    await session.handle_user_turn("I need five lakh rupees", 1200.0, 350.0)
    assert len(session.turns) == 1
    assert "five lakh" in session.turns[0]["user_transcript"]
    assert session.state == SessionState.LISTENING


@pytest.mark.asyncio
async def test_session_language_switch():
    """Verify session switches to Hindi when user speaks Hindi."""
    events = []
    config = {
        "first_name": "Rahul",
        "bank_name": "Apex Bank",
        "product_name": "Personal Loan",
        "language": "en-IN",
        "system_prompt": "You are Tara.",
    }
    session = VoiceSession(
        config=config,
        send_ws=lambda m: events.append(m),
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
    config = {
        "first_name": "Rahul",
        "bank_name": "Apex Bank",
        "product_name": "Personal Loan",
        "language": "en-IN",
        "system_prompt": "You are Tara.",
    }
    session = VoiceSession(
        config=config,
        send_ws=lambda m: events.append(m),
        speech_provider=MockSpeechProvider(),
        llm_client=MockLLMClient(),
    )
    session.state = SessionState.SPEAKING
    await session.barge_in()
    assert session._interrupted is True
    assert session.state == SessionState.LISTENING


@pytest.mark.asyncio
async def test_extraction_schema_with_amount_and_callback():
    """Verify extraction schema correctly parses loan amount and callback time."""
    data = {
        "interest_level": "high",
        "loan_amount_inr": 100000.0,
        "callback_time": "tomorrow 4pm",
        "language_used": ["hi-IN"],
        "outcome": "interested",
        "summary": "Customer asked for ek lakh.",
    }
    validated = SessionExtraction.model_validate(data)
    assert validated.loan_amount_inr == 100000.0
    assert validated.callback_time == "tomorrow 4pm"
    assert validated.outcome == "interested"


@pytest.mark.asyncio
async def test_extraction_schema_all_null_when_not_spoken():
    """Verify extraction schema correctly allows nulls when values were not spoken."""
    data = {
        "interest_level": "none",
        "loan_amount_inr": None,
        "callback_time": None,
        "language_used": ["en-IN"],
        "outcome": "not_interested",
        "summary": "Customer declined politely.",
    }
    validated = SessionExtraction.model_validate(data)
    assert validated.loan_amount_inr is None
    assert validated.callback_time is None
    assert validated.outcome == "not_interested"


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_session():
    """Run one real round-trip with live Gnani and Groq APIs."""
    config = {
        "first_name": "Aman",
        "bank_name": "Apex Bank",
        "product_name": "Personal Loan",
        "language": "en-IN",
        "system_prompt": "You are Tara.",
        "opening_message": "Hello Aman, this is Tara.",
        "max_turns": 1,
    }
    session = VoiceSession(config=config, send_ws=lambda m: None)
    await session.start()
    await session.handle_user_turn("Yes, I am interested in a loan.", 1000.0, 500.0)
    assert len(session.turns) >= 1
    doc = await session.end_session()
    assert doc.get("session_id")
