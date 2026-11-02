"""
WebSocket voice session endpoint and REST routes for session history and inspection.
Handles bidirectional audio streaming, real-time events, and MongoDB queries.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.db import get_db
from app.voice.session import VoiceSession
from providers.gnani_client import GnaniClient

router = APIRouter(tags=["voice"])

SAMPLE_CONFIG_PATH = Path(__file__).parent.parent / "voice" / "sample_config.json"


def load_default_config() -> Dict[str, Any]:
    """Load default voice agent configuration from sample_config.json."""
    if SAMPLE_CONFIG_PATH.exists():
        with open(SAMPLE_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "first_name": "Valued Customer",
        "bank_name": "Apex Bank",
        "product_name": "Personal Loan",
        "language": "en-IN",
        "system_prompt": "You are Tara, an AI voice assistant.",
        "opening_message": "Hello! This is Tara, an AI assistant.",
        "info_to_collect": [],
        "success_condition": "Customer expresses interest",
        "max_turns": 8,
    }


@router.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket) -> None:
    """Bi-directional WebSocket for live voice interaction session."""
    await websocket.accept()

    async def send_ws(message: Dict[str, Any]) -> None:
        try:
            await websocket.send_json(message)
        except Exception:
            pass

    config = load_default_config()
    session = VoiceSession(config=config, send_ws=send_ws)
    stt_fallback = GnaniClient()

    try:
        # Greet user immediately upon connection
        await session.start()

        while True:
            raw_msg = await websocket.receive_text()
            try:
                data = json.loads(raw_msg)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")

            if msg_type == "user_text":
                text = data.get("text", "")
                dur = float(data.get("duration_ms", 0.0))
                stt_ms = float(data.get("stt_ms", 0.0))
                await session.handle_user_turn(text, dur, stt_ms)

            elif msg_type == "user_audio":
                audio_b64 = data.get("audio_b64", "")
                dur = float(data.get("duration_ms", 0.0))
                if audio_b64:
                    raw_audio = base64.b64decode(audio_b64)
                    res = await stt_fallback.stt_transcribe(
                        raw_audio, filename="turn.wav", language_code=session.language
                    )
                    await session.handle_user_turn(
                        res.transcript, dur, res.latency_ms
                    )

            elif msg_type == "barge_in":
                await session.barge_in()

            elif msg_type == "end":
                await session.end_session()
                break

    except WebSocketDisconnect:
        await session.end_session(error="client_disconnected")
    except Exception as exc:
        await session.end_session(error=str(exc))
        await send_ws({"type": "error", "message": str(exc)})


@router.get("/api/voice/sessions")
async def list_voice_sessions(limit: int = 20) -> List[Dict[str, Any]]:
    """List recent voice sessions from MongoDB."""
    db = get_db()
    cursor = db["voice_sessions"].find({}, {"_id": 0}).sort("started_at", -1).limit(limit)
    sessions = []
    async for doc in cursor:
        if "started_at" in doc and doc["started_at"]:
            doc["started_at"] = doc["started_at"].isoformat()
        if "ended_at" in doc and doc["ended_at"]:
            doc["ended_at"] = doc["ended_at"].isoformat()
        sessions.append(doc)
    return sessions


@router.get("/api/voice/sessions/{session_id}")
async def get_voice_session(session_id: str) -> Dict[str, Any]:
    """Retrieve full session detail including turns and post-call extraction."""
    db = get_db()
    doc = await db["voice_sessions"].find_one({"session_id": session_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    if "started_at" in doc and doc["started_at"]:
        doc["started_at"] = doc["started_at"].isoformat()
    if "ended_at" in doc and doc["ended_at"]:
        doc["ended_at"] = doc["ended_at"].isoformat()
    return doc
