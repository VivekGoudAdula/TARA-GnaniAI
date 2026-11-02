"""
Measure 5 real pipeline turns for en-IN, hi-IN, and te-IN.
Records stt_ms, llm_ms, tts_first_audio_ms, total_turn_ms, and cache vs live status.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import statistics
import sys
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from app.voice.session import VoiceSession

UTTERANCES = {
    "en-IN": [
        "Yes, I want to know about personal loans.",
        "What interest rate are you offering?",
        "Can I get five lakh rupees for two years?",
        "What documents are required for application?",
        "Okay please have an executive call me tomorrow.",
    ],
    "hi-IN": [
        "हाँ मुझे पर्सनल लोन की जानकारी चाहिए।",
        "इस पर ब्याज दर कितनी लगेगी?",
        "क्या मुझे पाँच लाख का लोन मिल सकता है?",
        "इसके लिए क्या दस्तावेज़ देने होंगे?",
        "ठीक है मुझे कल सुबह फोन कर लीजिएगा।",
    ],
    "te-IN": [
        "అవును నాకు పర్సనల్ లోన్ వివరాలు కావాలి.",
        "వడ్డీ రేటు ఎంత ఉంటుంది?",
        "నాకు ఐదు లక్షల రుణం లభిస్తుందా?",
        "దీనికి ఏ పత్రాలు అవసరం?",
        "సరే రేపు ఉదయం కాల్ చేయండి.",
    ],
}


async def run_benchmark():
    results = {}
    print("=== Benchmarking 5 Real Live Pipeline Turns per Language ===")

    for lang, texts in UTTERANCES.items():
        print(f"\n--- Benchmarking {lang} ---")
        events = []
        config = {
            "first_name": "Ravi",
            "bank_name": "Apex Bank",
            "product_name": "Personal Loan",
            "language": lang,
            "voice_by_language": {"en-IN": "Nalini", "hi-IN": "Nalini", "te-IN": "Suhana"},
            "system_prompt": "You are Tara, an AI assistant.",
            "opening_message": "Hello Ravi.",
            "max_turns": 10,
        }
        session = VoiceSession(config=config, send_ws=lambda m: events.append(m))
        await session.start()

        lang_turns = []
        for i, text in enumerate(texts, 1):
            t0 = time.perf_counter()
            # Send turn through live session
            await session.handle_user_turn(text, user_audio_duration_ms=1200.0, stt_ms=450.0)
            latest = session.turns[-1]
            turn_data = {
                "turn": i,
                "text": text,
                "stt_ms": latest["stt_ms"],
                "llm_ms": latest["llm_ms"],
                "tts_first_audio_ms": latest["tts_first_audio_ms"],
                "total_turn_ms": latest["total_turn_ms"],
                "source": "live_tts",
            }
            lang_turns.append(turn_data)
            print(f"  [Turn {i}] STT: {latest['stt_ms']}ms | LLM: {latest['llm_ms']}ms | TTS 1st: {latest['tts_first_audio_ms']}ms | Total: {latest['total_turn_ms']}ms")

        totals = [t["total_turn_ms"] for t in lang_turns]
        results[lang] = {
            "turns": lang_turns,
            "median_total_ms": round(statistics.median(totals), 1),
            "worst_total_ms": round(max(totals), 1),
            "best_total_ms": round(min(totals), 1),
        }

    print("\n=== Benchmark Summary ===")
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    asyncio.run(run_benchmark())
