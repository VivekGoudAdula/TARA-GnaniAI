"""
SpeechProvider implementation wrapping Gnani Prisma v3.0 STT (WebSocket)
and Timbre v2.5 TTS (SSE Streaming).

Encapsulates all Gnani-specific protocol details, URLs, headers, and payload structures.
Exposes a provider-neutral interface so session and router code never leak Gnani details.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import time
from typing import AsyncIterator, Optional

import httpx
import websockets

from providers.gnani_client import (
    GnaniAPIError,
    GnaniAuthError,
    GnaniRateLimitError,
    GnaniTransientError,
)

WS_STT_URL = "wss://api.vachana.ai/stt/v3/stream"
SSE_TTS_URL = "https://api.vachana.ai/api/v1/tts/sse"

DEFAULT_VOICE_MAP = {
    "en-IN": "Nalini",
    "hi-IN": "Nalini",
    "te-IN": "Suhana",
}


class SpeechProvider:
    """Provider-neutral speech engine interface powered by Gnani."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize provider with API credentials from argument or environment."""
        self._api_key = api_key or os.getenv("GNANI_API_KEY", "")
        if not self._api_key:
            raise GnaniAuthError("GNANI_API_KEY is not set or empty")

    def get_default_voice(self, language_code: str) -> str:
        """Return the default verified voice for the specified language code."""
        return DEFAULT_VOICE_MAP.get(language_code, "Nalini")

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        language_code: str = "en-IN",
        sample_rate: int = 16000,
    ) -> AsyncIterator[dict]:
        """
        Stream 16-bit mono PCM audio chunks to realtime STT and yield transcript events.

        Yields dictionaries with keys:
            - text: str (recognized words)
            - is_final: bool (whether turn is complete)
            - detected_language: str
        """
        headers = {
            "x-api-key-id": self._api_key,
            "lang_code": language_code,
            "x-sample-rate": str(sample_rate),
            "x-model": "prisma-v3.0",
        }

        try:
            async with websockets.connect(
                WS_STT_URL, additional_headers=headers, open_timeout=15.0
            ) as ws:
                # 1. Await connected greeting event
                await asyncio.wait_for(ws.recv(), timeout=10.0)

                async def send_worker():
                    """Forward audio frames from input stream into WebSocket."""
                    try:
                        async for chunk in audio_stream:
                            if not chunk:
                                break
                            await ws.send(chunk)
                    except (asyncio.CancelledError, websockets.ConnectionClosed):
                        pass

                sender_task = asyncio.create_task(send_worker())

                try:
                    async for raw_msg in ws:
                        if isinstance(raw_msg, str):
                            try:
                                msg = json.loads(raw_msg)
                            except json.JSONDecodeError:
                                continue

                            msg_type = msg.get("type")
                            if msg_type == "transcript" and msg.get("text"):
                                yield {
                                    "text": msg["text"].strip(),
                                    "is_final": True,
                                    "detected_language": language_code,
                                }
                            elif msg_type == "partial_transcript" and msg.get("text"):
                                yield {
                                    "text": msg["text"].strip(),
                                    "is_final": False,
                                    "detected_language": language_code,
                                }
                finally:
                    sender_task.cancel()
                    await asyncio.gather(sender_task, return_exceptions=True)

        except websockets.InvalidStatusCode as err:
            if err.status_code == 401:
                raise GnaniAuthError("Gnani STT WebSocket authentication failed (401)") from err
            if err.status_code == 429:
                raise GnaniRateLimitError("Gnani STT WebSocket rate limited (429)") from err
            raise GnaniAPIError(f"Gnani STT WebSocket HTTP error: {err.status_code}") from err
        except Exception as exc:
            raise GnaniTransientError(f"Gnani STT WebSocket connection error: {exc}") from exc

    async def synthesize_stream(
        self,
        text: str,
        language_code: str = "en-IN",
        voice: Optional[str] = None,
        sample_rate: int = 24000,
    ) -> AsyncIterator[bytes]:
        """
        Synthesize text to speech using Timbre v2.5 SSE streaming.

        Yields decoded raw audio bytes as chunks arrive.
        """
        selected_voice = voice or self.get_default_voice(language_code)
        headers = {
            "X-API-Key-ID": self._api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "voice": selected_voice,
            "model": "timbre-v2.5",
            "language": language_code,
            "speed": 1.0,
            "audio_config": {
                "sample_rate": sample_rate,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                async with client.stream(
                    "POST", SSE_TTS_URL, headers=headers, json=payload
                ) as resp:
                    if resp.status_code == 401:
                        raise GnaniAuthError("Gnani TTS SSE authentication failed (401)")
                    if resp.status_code == 429:
                        raise GnaniRateLimitError("Gnani TTS SSE rate limited (429)")
                    if resp.status_code >= 500:
                        raise GnaniTransientError(f"Gnani TTS server error: {resp.status_code}")
                    if resp.status_code != 200:
                        body = await resp.aread()
                        raise GnaniAPIError(f"Gnani TTS error {resp.status_code}: {body.decode(errors='ignore')}")

                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        raw_data = line[5:].strip()
                        if not raw_data:
                            continue
                        try:
                            data = json.loads(raw_data)
                        except json.JSONDecodeError:
                            continue

                        chunk_b64 = data.get("audio", "")
                        if chunk_b64:
                            yield base64.b64decode(chunk_b64)
            except httpx.TimeoutException as exc:
                raise GnaniTransientError(f"Gnani TTS SSE request timed out: {exc}") from exc
            except (httpx.ConnectError, httpx.NetworkError) as exc:
                raise GnaniTransientError(f"Gnani TTS SSE network error: {exc}") from exc
