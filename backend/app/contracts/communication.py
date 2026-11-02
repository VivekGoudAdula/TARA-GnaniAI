"""
Communication Port Contract (Interface specification for Phase 5).
Defines abstract request structures and communication channel protocols.
This file contains contracts only; implementation is deferred to Phase 5.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional, Protocol
from pydantic import BaseModel, Field


class RenderedVoicePayload(BaseModel):
    """Voice stack execution payload strictly sanitized of sensitive financial data."""

    first_name: str
    bank_name: str
    product_name: str
    language: str
    system_prompt: str
    opening_message: str
    max_turns: int = 8
    info_to_collect: list[Dict[str, Any]] = Field(default_factory=list)


class CommunicationRequest(BaseModel):
    """Dispatched communication task targeting a specific audience recipient."""

    request_id: str
    tenant_id: str
    campaign_id: str
    config_version: int
    recipient_ref: str
    record_type: Literal["customers", "leads"]
    channel: Literal["voice", "whatsapp", "sms", "email"]
    rendered_payload: RenderedVoicePayload
    metadata: Dict[str, Any] = Field(default_factory=dict)
    scheduled_at: Optional[datetime] = None


class CommunicationPort(Protocol):
    """Abstract protocol for multi-channel communication dispatchers."""

    async def dispatch(self, request: CommunicationRequest) -> Dict[str, Any]:
        """Dispatch communication task through configured channel gateway."""
        ...
