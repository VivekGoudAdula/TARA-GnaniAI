"""
Conversation state machine and session orchestrator for real-time voice agent interactions.
Tracks turn-by-turn latencies, manages barge-in, coordinates LLM and TTS, and persists to MongoDB.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import re
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from app.db import get_db
from app.voice.prompt import build_system_prompt
from providers.gnani_speech import SpeechProvider
from providers.llm_client import LLMClient


class SessionState:
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ENDED = "ended"


def detect_language(text: str, current_lang: str) -> str:
    """Detect spoken language by Unicode script with fallback to current session language."""
    if any("\u0900" <= c <= "\u097f" for c in text):
        return "hi-IN"
    if any("\u0c00" <= c <= "\u0c7f" for c in text):
        return "te-IN"
    return current_lang


class VoiceSession:
    """Manages state, dialog turns, timing metrics, and persistence for one voice session."""

    def __init__(
        self,
        config: Dict[str, Any],
        send_ws: Callable[[Dict[str, Any]], Any],
        speech_provider: Optional[SpeechProvider] = None,
        llm_client: Optional[LLMClient] = None,
    ) -> None:
        """Initialize voice session with configuration, websocket callback, and providers."""
        self.session_id = f"sess_{uuid.uuid4().hex[:12]}"
        self.config = config
        self.send_ws = send_ws
        self.speech = speech_provider or SpeechProvider()
        self.llm = llm_client or LLMClient()

        self.state = SessionState.LISTENING
        self.language = config.get("language", "en-IN")
        self.max_turns = config.get("max_turns", 8)
        self.started_at = datetime.now(timezone.utc)
        self.ended_at: Optional[datetime] = None

        self.turns: List[Dict[str, Any]] = []
        self.messages: List[Dict[str, str]] = []
        self.speaking_task: Optional[asyncio.Task] = None
        self._interrupted = False
        self._session_doc: Optional[Dict[str, Any]] = None

    async def _send_event(self, msg: Dict[str, Any]) -> None:
        """Deliver event to websocket listener, supporting both sync and async callbacks."""
        res = self.send_ws(msg)
        if asyncio.iscoroutine(res):
            await res

    async def start(self) -> None:
        """Initialize session prompt, notify client, and speak greeting message."""
        sys_prompt = build_system_prompt(self.config, self.language)
        self.messages.append({"role": "system", "content": sys_prompt})
        await self._set_state(SessionState.LISTENING)

        opening_msg = self.config.get("opening_message", "")
        if opening_msg:
            self.messages.append({"role": "assistant", "content": opening_msg})
            await self._synthesize_and_stream(opening_msg, turn_num=0, is_greeting=True)

    async def handle_user_turn(
        self, user_text: str, user_audio_duration_ms: float = 0.0, stt_ms: float = 0.0
    ) -> None:
        """Execute one complete conversation turn: language detection -> LLM -> TTS."""
        if self.state == SessionState.ENDED or not user_text.strip():
            return

        self._interrupted = False
        self.language = detect_language(user_text, self.language)
        turn_num = len(self.turns) + 1
        t_user_speech_end = time.perf_counter()

        await self._set_state(SessionState.THINKING)
        self.messages[0]["content"] = build_system_prompt(self.config, self.language)
        self.messages.append({"role": "user", "content": user_text})
        await self._send_event({
            "type": "transcript",
            "role": "user",
            "text": user_text,
            "language": self.language,
        })

        t_llm_start = time.perf_counter()
        agent_reply_parts: List[str] = []
        first_sentence = ""
        llm_ms = 0.0

        try:
            async for token in self.llm.stream_chat(self.messages, temperature=0.2):
                if self._interrupted:
                    break
                agent_reply_parts.append(token)
                accumulated = "".join(agent_reply_parts)
                if not first_sentence and any(p in accumulated for p in [".", "?", "!", "\n", "।"]):
                    first_sentence = accumulated.strip()
                    llm_ms = round((time.perf_counter() - t_llm_start) * 1000, 1)

            agent_response = "".join(agent_reply_parts).strip()
            if not llm_ms:
                llm_ms = round((time.perf_counter() - t_llm_start) * 1000, 1)

            if not self._interrupted and agent_response:
                self.messages.append({"role": "assistant", "content": agent_response})
                tts_first_ms, total_turn_ms = await self._synthesize_and_stream(
                    agent_response, turn_num=turn_num, t_turn_start=t_user_speech_end
                )

                self.turns.append({
                    "turn_num": turn_num,
                    "user_audio_duration_ms": user_audio_duration_ms,
                    "stt_ms": stt_ms,
                    "llm_ms": llm_ms,
                    "tts_first_audio_ms": tts_first_ms,
                    "total_turn_ms": total_turn_ms,
                    "user_transcript": user_text,
                    "agent_response": agent_response,
                    "language": self.language,
                    "barge_in": self._interrupted,
                })

                await self._send_event({
                    "type": "turn_metrics",
                    "metrics": self.turns[-1],
                })

            if len(self.turns) >= self.max_turns:
                await self.end_session()
            else:
                await self._set_state(SessionState.LISTENING)

        except Exception as exc:
            await self._send_event({"type": "error", "message": f"Turn error: {str(exc)}"})
            await self._set_state(SessionState.LISTENING)

    async def barge_in(self) -> None:
        """Interrupt active agent speech immediately and transition back to listening."""
        self._interrupted = True
        if self.speaking_task and not self.speaking_task.done():
            self.speaking_task.cancel()
        await self._set_state(SessionState.LISTENING)
        await self._send_event({"type": "barge_in_acknowledged"})

    async def _synthesize_and_stream(
        self, text: str, turn_num: int, is_greeting: bool = False, t_turn_start: Optional[float] = None
    ) -> tuple[float, float]:
        """Stream TTS audio chunks over websocket and record latency metrics."""
        await self._set_state(SessionState.SPEAKING)
        await self._send_event({
            "type": "transcript",
            "role": "assistant",
            "text": text,
            "language": self.language,
            "turn": turn_num,
        })

        t_tts_req = time.perf_counter()
        first_audio_ms = 0.0
        total_turn_ms = 0.0

        try:
            async for audio_chunk in self.speech.synthesize_stream(text, self.language):
                if self._interrupted:
                    break
                if first_audio_ms == 0.0:
                    first_audio_ms = round((time.perf_counter() - t_tts_req) * 1000, 1)
                    if t_turn_start:
                        total_turn_ms = round((time.perf_counter() - t_turn_start) * 1000, 1)
                import base64
                await self._send_event({
                    "type": "audio",
                    "data": base64.b64encode(audio_chunk).decode("ascii"),
                    "turn": turn_num,
                })
        except asyncio.CancelledError:
            self._interrupted = True
        finally:
            await self._send_event({"type": "agent_speech_end", "turn": turn_num})
        return first_audio_ms, total_turn_ms

    async def end_session(self, error: Optional[str] = None) -> Dict[str, Any]:
        """Perform post-session extraction, persist document to MongoDB, and notify client."""
        if self.state == SessionState.ENDED:
            return self._session_doc or {}
        await self._set_state(SessionState.ENDED)
        self.ended_at = datetime.now(timezone.utc)
        duration_sec = round((self.ended_at - self.started_at).total_seconds(), 2)

        # Run extraction prompt
        extracted = await self.llm.extract_session_data(
            transcript=self.messages[1:],
            info_to_collect=self.config.get("info_to_collect", []),
            success_condition=self.config.get("success_condition", ""),
        )

        doc = {
            "session_id": self.session_id,
            "lead_id": self.config.get("lead_id"),
            "campaign_id": self.config.get("campaign_id"),
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": duration_sec,
            "turns": self.turns,
            "extracted_data": extracted,
            "error": error,
        }
        self._session_doc = doc

        try:
            db = get_db()
            await db["voice_sessions"].insert_one(doc)
        except Exception:
            pass

        await self._send_event({"type": "session_ended", "data": extracted, "duration_seconds": duration_sec})
        return doc

    async def _set_state(self, new_state: str) -> None:
        """Transition session state and notify WebSocket listener."""
        self.state = new_state
        await self._send_event({"type": "state", "state": self.state})
