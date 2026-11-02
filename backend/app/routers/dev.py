"""
Dev-only endpoints for smoke-testing Gnani STT and TTS.

Guarded by DEV_ENDPOINTS=true in .env.
These routes are included in the app only when that flag is set.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.auth import TokenUser, get_current_user
from providers.gnani_client import GnaniClient, GnaniAPIError

router = APIRouter(tags=["dev"])
_client = GnaniClient()


# ─── STT ──────────────────────────────────────────────────────────────────────

class STTResponse(BaseModel):
    transcript: str
    detected_language_code: str
    request_id: str
    latency_ms: float


@router.post("/stt", response_model=STTResponse)
async def dev_stt(
    audio: UploadFile = File(...),
    current_user: TokenUser = Depends(get_current_user),
) -> STTResponse:
    """Transcribe uploaded audio using Gnani Prisma v3.0 (dev endpoint, authenticated)."""
    audio_bytes = await audio.read()
    try:
        result = await _client.stt_transcribe(
            audio_bytes=audio_bytes,
            filename=audio.filename or "audio.wav",
        )
    except GnaniAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return STTResponse(**result)


# ─── TTS ──────────────────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str
    language_code: str = "en-IN"
    voice: str = "Nalini"


@router.post("/tts")
async def dev_tts(
    body: TTSRequest,
    current_user: TokenUser = Depends(get_current_user),
) -> Response:
    """Synthesise speech using Gnani Timbre v2.5 (dev endpoint, authenticated)."""
    try:
        audio_bytes, content_type, _ = await _client.tts_synthesize(
            text=body.text,
            language_code=body.language_code,
            voice=body.voice,
        )
    except GnaniAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return Response(content=audio_bytes, media_type=content_type)

