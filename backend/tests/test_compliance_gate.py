"""
Unit and integration tests for the regulatory Compliance Gate.
Tests all machine reason codes, IST calling window edges, frequency caps, and audit logs.
"""
from __future__ import annotations

from datetime import datetime, timezone
import uuid
from zoneinfo import ZoneInfo
import pytest

from app.communication.compliance import (
    ComplianceReason,
    evaluate_compliance_gate,
    is_within_calling_window,
    log_audit_trail,
)
from app.db import get_db

IST = ZoneInfo("Asia/Kolkata")


def test_calling_window_edges_ist():
    """Verify exact calling window boundaries at 08:59, 09:00, 20:59, and 21:00 IST."""
    # 08:59:59 IST -> Outside window
    t_0859 = datetime(2026, 11, 2, 8, 59, 59, tzinfo=IST)
    assert is_within_calling_window(t_0859) is False

    # 09:00:00 IST -> Allowed
    t_0900 = datetime(2026, 11, 2, 9, 0, 0, tzinfo=IST)
    assert is_within_calling_window(t_0900) is True

    # 20:59:59 IST -> Allowed
    t_2059 = datetime(2026, 11, 2, 20, 59, 59, tzinfo=IST)
    assert is_within_calling_window(t_2059) is True

    # 21:00:00 IST -> Outside window
    t_2100 = datetime(2026, 11, 2, 21, 0, 0, tzinfo=IST)
    assert is_within_calling_window(t_2100) is False


@pytest.mark.asyncio
async def test_compliance_gate_consent_and_dnd():
    """Test machine reason codes CONSENT_MISSING and DND_FLAGGED."""
    t_id = f"ten_comp_{uuid.uuid4().hex[:6]}"
    valid_time = datetime(2026, 11, 2, 11, 0, 0, tzinfo=IST)

    # 1. Missing consent
    no_consent_rec = {
        "tenant_id": t_id, "record_id": "r_noconsent",
        "consent": False, "dnd": False, "phone": "+919000011111"
    }
    ok, reason = await evaluate_compliance_gate(t_id, no_consent_rec, "voice", evaluation_time=valid_time)
    assert ok is False
    assert reason == ComplianceReason.CONSENT_MISSING

    # 2. DND flagged
    dnd_rec = {
        "tenant_id": t_id, "record_id": "r_dnd",
        "consent": True, "dnd": True, "phone": "+919000022222"
    }
    ok, reason = await evaluate_compliance_gate(t_id, dnd_rec, "voice", evaluation_time=valid_time)
    assert ok is False
    assert reason == ComplianceReason.DND_FLAGGED


@pytest.mark.asyncio
async def test_compliance_gate_frequency_and_duplicate_in_flight():
    """Test machine reasons FREQUENCY_CAP and DUPLICATE_IN_FLIGHT."""
    db = get_db()
    t_id = f"ten_freq_{uuid.uuid4().hex[:6]}"
    valid_time = datetime(2026, 11, 2, 14, 0, 0, tzinfo=IST)
    rec = {
        "tenant_id": t_id, "record_id": "r_freq",
        "consent": True, "dnd": False, "phone": "+919000033333"
    }

    # Insert 2 prior completed communications within last 7 days
    await db["communications"].insert_many([
        {"tenant_id": t_id, "record_id": "r_freq", "status": "completed", "created_at": valid_time},
        {"tenant_id": t_id, "record_id": "r_freq", "status": "completed", "created_at": valid_time},
    ])

    # 3rd attempt must trigger FREQUENCY_CAP
    ok, reason = await evaluate_compliance_gate(t_id, rec, "voice", evaluation_time=valid_time)
    assert ok is False
    assert reason == ComplianceReason.FREQUENCY_CAP

    # Test DUPLICATE_IN_FLIGHT
    rec2 = {"tenant_id": t_id, "record_id": "r_inflight", "consent": True, "dnd": False, "phone": "+919000044444"}
    await db["communications"].insert_one({
        "tenant_id": t_id, "record_id": "r_inflight", "status": "in_progress", "created_at": valid_time
    })
    ok2, reason2 = await evaluate_compliance_gate(t_id, rec2, "voice", evaluation_time=valid_time)
    assert ok2 is False
    assert reason2 == ComplianceReason.DUPLICATE_IN_FLIGHT


@pytest.mark.asyncio
async def test_compliance_gate_tenant_mismatch_and_channel_and_audit_log():
    """Verify TENANT_MISMATCH, INVALID_CHANNEL_CONFIG, and immutable audit logging."""
    db = get_db()
    t_id = f"ten_aud_{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc)

    # Tenant mismatch
    wrong_rec = {"tenant_id": "other_tenant", "record_id": "r_other", "consent": True, "dnd": False}
    ok, reason = await evaluate_compliance_gate(t_id, wrong_rec, "voice")
    assert ok is False
    assert reason == ComplianceReason.TENANT_MISMATCH

    # Invalid channel
    ok2, reason2 = await evaluate_compliance_gate(t_id, {"tenant_id": t_id, "record_id": "r_chan", "consent": True}, "sms")
    assert ok2 is False
    assert reason2 == ComplianceReason.INVALID_CHANNEL_CONFIG

    # Write audit log and verify persistence
    audit = await log_audit_trail(
        tenant_id=t_id, communication_id="comm_aud_1", record_id="r_chan",
        channel="sms", config_version=1, decision="BLOCKED", reason_code=reason2
    )
    assert audit["decision"] == "BLOCKED"
    assert audit["reason_code"] == ComplianceReason.INVALID_CHANNEL_CONFIG

    persisted = await db["audit_log"].find_one({"tenant_id": t_id, "communication_id": "comm_aud_1"})
    assert persisted is not None
    assert persisted["decision"] == "BLOCKED"
