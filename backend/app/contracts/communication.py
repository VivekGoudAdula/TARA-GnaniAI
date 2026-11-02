"""
Communication Port Contract.
Defines abstract request structures and channel dispatcher interfaces.
Campaign code interacts with communication dispatchers exclusively through this contract.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional, Protocol
from pydantic import BaseModel, Field


class RecipientRef(BaseModel):
    """Reference to target customer or lead record."""

    record_id: str
    record_type: Literal["customers", "leads"]


class RenderedVoicePayload(BaseModel):
    """Voice stack execution payload strictly sanitized of sensitive financial data."""

    first_name: str
    bank_name: str
    product_name: str
    language: str = "en-IN"
    system_prompt: str
    opening_message: str
    info_to_collect: list[Dict[str, Any]] = Field(default_factory=list)
    success_condition: Optional[str] = ""
    max_turns: int = 8
    voice: Optional[str] = None


class SendCommunicationRequest(BaseModel):
    """Dispatched communication request from campaign or ad-hoc trigger."""

    recipient_ref: RecipientRef
    channel: Literal["voice"] = "voice"
    campaign_id: Optional[str] = None
    config_version: int = 1
    rendered: RenderedVoicePayload
    idempotency_key: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CommunicationResponse(BaseModel):
    """Normalized response from communication dispatch."""

    communication_id: str
    status: str
    reason: Optional[str] = None
    task_token: Optional[str] = None


class CommunicationPort(Protocol):
    """Abstract protocol for multi-channel communication dispatchers."""

    async def dispatch(self, tenant_id: str, request: SendCommunicationRequest) -> CommunicationResponse:
        """Dispatch communication task through configured channel gateway."""
        ...
