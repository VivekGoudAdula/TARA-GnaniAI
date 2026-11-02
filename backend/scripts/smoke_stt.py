"""
smoke_stt.py – Send an audio file to Gnani Prisma v3.0 STT and print the result.

Usage:
    python scripts/smoke_stt.py <path_to_audio_file> [language_code]

    language_code defaults to 'indic-auto' (auto-detection).

Example:
    python scripts/smoke_stt.py scripts/out/hi.wav indic-auto
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


async def main(audio_path: str, language_code: str = "indic-auto") -> None:
    """Run STT smoke test on the given audio file."""
    p = Path(audio_path)
    if not p.exists():
        print(f"ERROR: File not found: {p}")
        sys.exit(1)

    print(f"=== Gnani STT Smoke Test ===")
    print(f"File          : {p}")
    print(f"Language code : {language_code}")
    print(f"Size          : {p.stat().st_size} bytes")
    print()

    client = GnaniClient()
    try:
        result = await client.stt_transcribe(
            audio_bytes=p.read_bytes(),
            filename=p.name,
            language_code=language_code,
        )
    except GnaniAPIError as exc:
        print(f"FAILED – {type(exc).__name__}: {exc}")
        sys.exit(1)

    print(f"Transcript              : {result['transcript']}")
    print(f"Detected language code  : {result['detected_language_code']}")
    print(f"Request ID              : {result['request_id']}")
    print(f"Latency                 : {result['latency_ms']} ms")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    audio_arg = sys.argv[1]
    lang_arg = sys.argv[2] if len(sys.argv) > 2 else "indic-auto"
    asyncio.run(main(audio_arg, lang_arg))

