"""
Voice provider interface and Gnani web-voice session adapter.
Binds outbound communication dispatches to interactive web tester sessions.
Sole module in communication with access to app.voice and providers.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
from typing import Any, Dict, List, Optional, Protocol
import uuid

from app.contracts.communication import RenderedVoicePayload
from app.db import get_db


class VoiceProvider(Protocol):
    """Abstract interface for voice interaction adapters."""

    async def create_session_task(
        self,
        tenant_id: str,
        communication_id: str,
        rendered: RenderedVoicePayload,
        recipient_context: Dict[str, Any],
        config_version: int,
        expiry_minutes: int = 30,
    ) -> Dict[str, Any]:
        """Create a dispatch task and generate tester session token."""
        ...

    async def complete_session_outcome(
        self,
        communication_id: str,
        outcome_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Store normalized session outcome into communication record."""
        ...


class GnaniWebVoiceProvider:
    """Outbound web-voice provider adapter for browser-based test interactions."""

    async def create_session_task(
        self,
        tenant_id: str,
        communication_id: str,
        rendered: RenderedVoicePayload,
        recipient_context: Dict[str, Any],
        config_version: int,
        expiry_minutes: int = 30,
    ) -> Dict[str, Any]:
        """Generate single-use token and store task metadata for web tester."""
        db = get_db()
        now = datetime.now(timezone.utc)
        token = f"tok_{secrets.token_urlsafe(16)}"
        expires_at = now + timedelta(minutes=expiry_minutes)

        task_doc = {
            "token": token,
            "tenant_id": tenant_id,
            "communication_id": communication_id,
            "config_version": config_version,
            "rendered": rendered.model_dump(),
            "recipient_first_name": rendered.first_name,
            "product_name": rendered.product_name,
            "bank_name": rendered.bank_name,
            "language": rendered.language,
            "status": "queued",
            "single_use": True,
            "used": False,
            "created_at": now,
            "expires_at": expires_at,
        }
        await db["call_tasks"].insert_one(task_doc)

        return {
            "token": token,
            "call_url": f"/call/{token}",
            "expires_at": expires_at,
        }

    async def complete_session_outcome(
        self,
        communication_id: str,
        outcome_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Normalize and persist call outcome directly to communication record."""
        db = get_db()
        now = datetime.now(timezone.utc)

        update_fields = {
            "status": outcome_data.get("status", "completed"),
            "completed_at": now,
            "duration_s": outcome_data.get("duration_s", 0.0),
            "transcript": outcome_data.get("transcript", []),
            "extraction": outcome_data.get("extraction", {}),
            "voice_used": outcome_data.get("voice_used", {}),
            "outcome": outcome_data.get("outcome", "unclear"),
            "updated_at": now,
        }

        await db["communications"].update_one(
            {"communication_id": communication_id},
            {"$set": update_fields}
        )
        return update_fields
