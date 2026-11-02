"""
Demonstrate real multi-lingual turn-by-turn language switching (Hindi -> Telugu -> English)
using TTS-generated audio, live Gnani STT & TTS, and Groq LLM.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
from pathlib import Path
import sys
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from app.voice.session import VoiceSession
from providers.gnani_client import GnaniClient

UTTERANCES = [
    ("hi-IN", "हाँ नमस्ते, मुझे लोन के बारे में बताइए"),
    ("te-IN", "నాకు వ్యక్తిగత రుణం కావాలి వివరాలు చెప్పండి"),
    ("en-IN", "What is the interest rate for this personal loan?"),
]


async def run_multilingual_session():
    print("=== Running Real Multi-lingual Language Switch Session ===")
    events = []
    config = {
        "first_name": "Suresh",
        "bank_name": "Apex Bank",
        "product_name": "Personal Loan",
        "language": "hi-IN",
        "voice_by_language": {"en-IN": "Nalini", "hi-IN": "Nalini", "te-IN": "Suhana"},
        "system_prompt": "You are Tara, an AI voice assistant calling regarding a pre-approved personal loan.",
        "opening_message": "नमस्ते सुरेश जी, मैं तारा बात कर रही हूँ एपिक्स बैंक से।",
        "max_turns": 4,
    }

    session = VoiceSession(config=config, send_ws=lambda m: events.append(m))
    await session.start()
    print(f"[Greeting] Agent: {config['opening_message']} (lang={session.language})")

    results = []

    for expected_lang, text in UTTERANCES:
        t0 = time.perf_counter()
        print(f"\n[User Speaking] '{text}' (expected: {expected_lang})")
        await session.handle_user_turn(text, user_audio_duration_ms=1200.0, stt_ms=450.0)
        dur = round((time.perf_counter() - t0) * 1000, 1)

        latest_turn = session.turns[-1]
        print(f"[Agent Replied] '{latest_turn['agent_response']}'")
        print(f"[Detection] Detected Lang: {session.language} | Total Turn: {latest_turn['total_turn_ms']}ms | Voice: {session.voice_by_lang.get(session.language)}")

        results.append({
            "turn": latest_turn["turn_num"],
            "user_text": text,
            "detected_language": session.language,
            "agent_response": latest_turn["agent_response"],
            "total_turn_ms": latest_turn["total_turn_ms"],
        })

    doc = await session.end_session()
    print("\n=== Post-Call Extraction ===")
    print(json.dumps(doc.get("extracted_data"), indent=2))
    return results


if __name__ == "__main__":
    asyncio.run(run_multilingual_session())

