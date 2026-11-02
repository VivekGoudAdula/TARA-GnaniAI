"""
Latency benchmark for Gnani Realtime WebSocket STT, SSE TTS, and WebSocket TTS.
Measures time to first audio chunk, total synthesis time, and STT latency.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
from pathlib import Path
import sys
import time
import wave

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent.parent))
import httpx
import websockets
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")
API_KEY = os.getenv("GNANI_API_KEY", "")
BASE_URL = "https://api.vachana.ai"
WS_STT_URL = "wss://api.vachana.ai/stt/v3/stream"
WS_TTS_URL = "wss://api.vachana.ai/api/v1/tts"
SSE_TTS_URL = "https://api.vachana.ai/api/v1/tts/sse"

TEXTS = {
    "en-IN": "Hello! I am calling from Tara to inform you about your loan offer.",
    "hi-IN": "नमस्ते! मैं तारा से आपके लोन ऑफर के बारे में बात कर रहा हूँ।",
    "te-IN": "నమస్కారం! నేను తారా నుండి మీ లోన్ ఆఫర్ గురించి మాట్లాడుతున్నాను.",
}
HINDI_VOICES = ["Nalini", "Bhavna", "Deepak", "Roopesh", "Vikrant"]
TELUGU_VOICES = ["Suhana", "Lehara", "Lavanya", "Yukti", "Varuni", "Nalini"]


async def get_16k_pcm(text: str, lang: str, voice: str) -> bytes:
    """Synthesize 16kHz 16-bit mono PCM via Timbre v2.5 REST."""
    headers = {"X-API-Key-ID": API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "voice": voice,
        "model": "timbre-v2.5",
        "language": lang,
        "speed": 1.0,
        "audio_config": {"sample_rate": 16000, "encoding": "linear_pcm", "container": "wav"},
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(f"{BASE_URL}/api/v1/tts/inference", headers=headers, json=payload)
        resp.raise_for_status()
        with wave.open(io.BytesIO(resp.content), "rb") as wf:
            return wf.readframes(wf.getnframes())


async def bench_tts_sse(text: str, lang: str, voice: str) -> tuple[float, float, int]:
    """Measure TTS SSE streaming latency and byte count."""
    headers = {"X-API-Key-ID": API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "voice": voice,
        "model": "timbre-v2.5",
        "language": lang,
        "speed": 1.0,
        "audio_config": {"sample_rate": 48000, "encoding": "linear_pcm", "container": "wav"},
    }
    t0, first_chunk_ms, total_bytes = time.perf_counter(), 0.0, 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("POST", SSE_TTS_URL, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    raw = line[5:].strip()
                    if not raw:
                        continue
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    b64 = data.get("audio", "")
                    if b64:
                        if first_chunk_ms == 0.0:
                            first_chunk_ms = (time.perf_counter() - t0) * 1000
                        total_bytes += len(base64.b64decode(b64))
    total_ms = (time.perf_counter() - t0) * 1000
    return round(first_chunk_ms, 1), round(total_ms, 1), total_bytes


async def bench_tts_ws(text: str, lang: str, voice: str) -> tuple[float, float, int]:
    """Measure TTS WebSocket streaming latency and byte count."""
    headers = {"X-API-Key-ID": API_KEY}
    payload = {
        "text": text,
        "voice": voice,
        "model": "timbre-v2.5",
        "language": lang,
        "speed": 1.0,
        "audio_config": {"sample_rate": 48000, "encoding": "linear_pcm", "container": "wav"},
    }
    t0, first_chunk_ms, total_bytes = time.perf_counter(), 0.0, 0
    async with websockets.connect(WS_TTS_URL, additional_headers=headers, open_timeout=15) as ws:
        await ws.send(json.dumps(payload))
        async for msg in ws:
            if isinstance(msg, bytes):
                if first_chunk_ms == 0.0:
                    first_chunk_ms = (time.perf_counter() - t0) * 1000
                total_bytes += len(msg)
            elif isinstance(msg, str):
                try:
                    parsed = json.loads(msg)
                except json.JSONDecodeError:
                    continue
                if parsed.get("type") == "audio":
                    b64 = parsed.get("data", {}).get("audio", "")
                    if b64:
                        if first_chunk_ms == 0.0:
                            first_chunk_ms = (time.perf_counter() - t0) * 1000
                        total_bytes += len(base64.b64decode(b64))
                elif parsed.get("type") == "complete":
                    break
    total_ms = (time.perf_counter() - t0) * 1000
    return round(first_chunk_ms, 1), round(total_ms, 1), total_bytes


async def bench_stt_ws(pcm_bytes: bytes, sample_rate: int, lang_code: str) -> tuple[float, str]:
    """Measure STT Realtime WS latency from end of audio stream to final transcript."""
    headers = {
        "x-api-key-id": API_KEY,
        "lang_code": lang_code,
        "x-sample-rate": str(sample_rate),
        "x-model": "prisma-v3.0",
    }
    async with websockets.connect(WS_STT_URL, additional_headers=headers, open_timeout=15) as ws:
        await ws.recv()
        chunk_size = 1024
        sec_per_chunk = chunk_size / (sample_rate * 2)
        for i in range(0, len(pcm_bytes), chunk_size):
            await ws.send(pcm_bytes[i : i + chunk_size])
            await asyncio.sleep(sec_per_chunk)
        t_audio_end = time.perf_counter()
        silence = b"\x00" * chunk_size
        for _ in range(25):
            await ws.send(silence)
            await asyncio.sleep(sec_per_chunk)
        transcript = ""
        while True:
            resp = await asyncio.wait_for(ws.recv(), timeout=10.0)
            if isinstance(resp, str):
                data = json.loads(resp)
                if data.get("type") == "transcript" and data.get("text"):
                    transcript = data["text"]
                    break
        lat = (time.perf_counter() - t_audio_end) * 1000
        return round(lat, 1), transcript


async def test_voices():
    """Verify supported voice catalog for Hindi and Telugu."""
    headers = {"X-API-Key-ID": API_KEY, "Content-Type": "application/json"}
    for lang, voices in [("hi-IN", HINDI_VOICES), ("te-IN", TELUGU_VOICES)]:
        for v in voices:
            payload = {
                "text": "नमस्ते" if lang == "hi-IN" else "నమస్కారం",
                "voice": v,
                "model": "timbre-v2.5",
                "language": lang,
                "speed": 1.0,
                "audio_config": {"sample_rate": 48000, "encoding": "linear_pcm", "container": "wav"},
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(f"{BASE_URL}/api/v1/tts/inference", headers=headers, json=payload)
                print(f"[{lang}] voice '{v}': {'OK' if r.status_code == 200 else f'HTTP {r.status_code}'}")


async def main():
    print("=== Gnani Realtime & Streaming Latency Benchmark ===")
    await test_voices()
    for lang in ["en-IN", "hi-IN", "te-IN"]:
        text, voice = TEXTS[lang], "Nalini"
        pcm_16k = await get_16k_pcm(text, lang, voice)
        for i in range(5):
            f_sse, t_sse, _ = await bench_tts_sse(text, lang, voice)
            f_ws, t_ws, _ = await bench_tts_ws(text, lang, voice)
            stt_lat, _ = await bench_stt_ws(pcm_16k, 16000, lang)
            print(f"[{lang} #{i+1}] SSE 1st: {f_sse}ms | WS 1st: {f_ws}ms | STT WS: {stt_lat}ms")


if __name__ == "__main__":
    asyncio.run(main())
