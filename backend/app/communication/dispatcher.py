"""
Outbound communication dispatcher and orchestration engine.
Enforces compliance gating, phone resolution from internal records, idempotency,
and task generation via voice provider adapter.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

from app.communication.compliance import evaluate_compliance_gate, log_audit_trail
from app.communication.provider import GnaniWebVoiceProvider, VoiceProvider
from app.contracts.communication import (
    CommunicationResponse,
    SendCommunicationRequest,
)
from app.db import get_db


class CommunicationDispatcher:
    """Core communication dispatcher implementing the CommunicationPort protocol."""

    def __init__(self, provider: Optional[VoiceProvider] = None):
        self.provider = provider or GnaniWebVoiceProvider()

    async def dispatch(self, tenant_id: str, request: SendCommunicationRequest) -> CommunicationResponse:
        """Process an outbound communication request through compliance and task generation."""
        db = get_db()
        now = datetime.now(timezone.utc)

        # 1. Idempotency check: return existing record if key matches
        if request.idempotency_key:
            existing = await db["communications"].find_one({
                "tenant_id": tenant_id,
                "idempotency_key": request.idempotency_key,
            })
            if existing:
                return CommunicationResponse(
                    communication_id=existing["communication_id"],
                    status=existing["status"],
                    reason=existing.get("blocked_reason"),
                    task_token=existing.get("task_token"),
                )

        comm_id = f"comm_{uuid.uuid4().hex[:12]}"
        rec_id = request.recipient_ref.record_id
        rec_type = request.recipient_ref.record_type

        # 2. Look up customer/lead record INSIDE communication module (phone never travels in payload)
        coll_name = "customers" if rec_type == "customers" else "leads"
        record = await db[coll_name].find_one({"tenant_id": tenant_id, "record_id": rec_id})

        # 3. Evaluate compliance gate
        allowed, reason = await evaluate_compliance_gate(
            tenant_id=tenant_id,
            record=record,
            channel=request.channel,
            campaign_id=request.campaign_id,
            evaluation_time=now,
        )

        # 4. Immutable audit trail entry
        await log_audit_trail(
            tenant_id=tenant_id,
            communication_id=comm_id,
            record_id=rec_id,
            channel=request.channel,
            config_version=request.config_version,
            decision="ALLOWED" if allowed else "BLOCKED",
            campaign_id=request.campaign_id,
            reason_code=reason,
            timestamp=now,
        )

        # 5. Handle blocked outcome
        if not allowed:
            comm_doc = {
                "communication_id": comm_id,
                "tenant_id": tenant_id,
                "campaign_id": request.campaign_id,
                "record_id": rec_id,
                "record_type": rec_type,
                "channel": request.channel,
                "config_version": request.config_version,
                "status": "blocked",
                "blocked_reason": reason,
                "idempotency_key": request.idempotency_key,
                "recipient_first_name": request.rendered.first_name,
                "product_name": request.rendered.product_name,
                "bank_name": request.rendered.bank_name,
                "metadata": request.metadata,
                "created_at": now,
                "updated_at": now,
            }
            await db["communications"].insert_one(comm_doc)
            return CommunicationResponse(communication_id=comm_id, status="blocked", reason=reason)

        # 6. Passed compliance: create voice session task
        task_info = await self.provider.create_session_task(
            tenant_id=tenant_id,
            communication_id=comm_id,
            rendered=request.rendered,
            recipient_context={
                "record_id": rec_id,
                "record_type": rec_type,
                "phone": record.get("phone") if record else None,
            },
            config_version=request.config_version,
        )

        comm_doc = {
            "communication_id": comm_id,
            "tenant_id": tenant_id,
            "campaign_id": request.campaign_id,
            "record_id": rec_id,
            "record_type": rec_type,
            "channel": request.channel,
            "config_version": request.config_version,
            "status": "queued",
            "blocked_reason": None,
            "task_token": task_info["token"],
            "call_url": task_info["call_url"],
            "idempotency_key": request.idempotency_key,
            "recipient_first_name": request.rendered.first_name,
            "product_name": request.rendered.product_name,
            "bank_name": request.rendered.bank_name,
            "language": request.rendered.language,
            "metadata": request.metadata,
            "created_at": now,
            "updated_at": now,
        }
        await db["communications"].insert_one(comm_doc)

        return CommunicationResponse(
            communication_id=comm_id,
            status="queued",
            task_token=task_info["token"],
        )
