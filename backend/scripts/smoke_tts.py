"""
smoke_tts.py – Synthesise one sentence in English, Hindi and Telugu using
Gnani Timbre v2.5, save them to scripts/out/, and print latency per call.

Usage:
    python scripts/smoke_tts.py

Output files:
    scripts/out/en.wav   – English
    scripts/out/hi.wav   – Hindi
    scripts/out/te.wav   – Telugu

These files can then be fed to smoke_stt.py to complete the round-trip.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Configure utf-8 encoding for Windows terminal printing
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Allow running from the backend/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from providers.gnani_client import GnaniClient, GnaniAPIError

OUT_DIR = Path(__file__).parent / "out"

# (language_code, voice, text, output_filename)
SAMPLES = [
    (
        "en-IN",
        "Nalini",
        "Hello! This is a test message from TARA, your financial assistant.",
        "en.wav",
    ),
    (
        "hi-IN",
        "Nalini",
        "नमस्ते! यह TARA की ओर से एक परीक्षण संदेश है।",
        "hi.wav",
    ),
    (
        "te-IN",
        "Nalini",
        "నమస్కారం! ఇది TARA నుండి ఒక పరీక్షా సందేశం.",
        "te.wav",
    ),
]


async def main() -> None:
    """Run TTS smoke test for English, Hindi and Telugu."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = GnaniClient()

    print("=== Gnani TTS Smoke Test (Timbre v2.5) ===\n")

    for language_code, voice, text, filename in SAMPLES:
        print(f"Language : {language_code}  |  Voice : {voice}")
        print(f"Text     : {text}")
        try:
            audio_bytes, content_type, latency_ms = await client.tts_synthesize(
                text=text,
                language_code=language_code,
                voice=voice,
            )
        except GnaniAPIError as exc:
            print(f"FAILED – {type(exc).__name__}: {exc}\n")
            continue

        out_path = OUT_DIR / filename
        out_path.write_bytes(audio_bytes)
        print(f"Saved    : {out_path}  ({len(audio_bytes)} bytes)")
        print(f"Latency  : {latency_ms} ms")
        print(f"Type     : {content_type}")
        print()


if __name__ == "__main__":
    asyncio.run(main())

