"""
Deterministic compliance gate and immutable regulatory audit logger.
Evaluates consent, DND, calling window (IST), frequency capping, and in-flight deduplication.
Does NOT perform national NDNC checks; enforces internal DND flags and bank policy.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
import os
import re
from typing import Any, Dict, Optional, Tuple
from zoneinfo import ZoneInfo

from app.db import get_db

IST = ZoneInfo("Asia/Kolkata")
SYNTHETIC_PHONE_REGEX = re.compile(r"^(\+91[\s-]?)?90000\d{5}$")


class ComplianceReason:
    CONSENT_MISSING = "CONSENT_MISSING"
    DND_FLAGGED = "DND_FLAGGED"
    OUTSIDE_CALLING_WINDOW = "OUTSIDE_CALLING_WINDOW"
    FREQUENCY_CAP = "FREQUENCY_CAP"
    DUPLICATE_IN_FLIGHT = "DUPLICATE_IN_FLIGHT"
    TEST_MODE_NOT_ALLOWLISTED = "TEST_MODE_NOT_ALLOWLISTED"
    TENANT_MISMATCH = "TENANT_MISMATCH"
    INVALID_CHANNEL_CONFIG = "INVALID_CHANNEL_CONFIG"


def is_within_calling_window(
    dt: datetime,
    start_time: time = time(9, 0),
    end_time: time = time(21, 0),
) -> bool:
    """Verify time is within approved calling hours in IST (09:00 - 20:59:59 IST)."""
    ist_time = dt.astimezone(IST).time()
    # 09:00 inclusive up to 21:00 exclusive
    return start_time <= ist_time < end_time


async def evaluate_compliance_gate(
    tenant_id: str,
    record: Optional[Dict[str, Any]],
    channel: str,
    campaign_id: Optional[str] = None,
    evaluation_time: Optional[datetime] = None,
    frequency_days: int = 7,
    max_frequency: int = 2,
) -> Tuple[bool, Optional[str]]:
    """
    Evaluate compliance rules in strict priority order.
    Returns (is_allowed, failure_reason_code).
    """
    db = get_db()
    now = evaluation_time or datetime.now(timezone.utc)

    # 1. Tenant mismatch
    if not record or record.get("tenant_id") != tenant_id:
        return False, ComplianceReason.TENANT_MISMATCH

    # 2. Channel validity
    if channel != "voice":
        return False, ComplianceReason.INVALID_CHANNEL_CONFIG

    # 3. Consent check
    if not record.get("consent", False):
        return False, ComplianceReason.CONSENT_MISSING

    # 4. Internal DND flag
    if record.get("dnd", False):
        return False, ComplianceReason.DND_FLAGGED

    # 5. Calling window check (09:00 to 21:00 IST)
    tenant_doc = await db["tenants"].find_one({"tenant_id": tenant_id})
    start_h = tenant_doc.get("calling_window_start_hour", 9) if tenant_doc else 9
    end_h = tenant_doc.get("calling_window_end_hour", 21) if tenant_doc else 21
    if not is_within_calling_window(now, time(start_h, 0), time(end_h, 0)):
        return False, ComplianceReason.OUTSIDE_CALLING_WINDOW

    # 6. Frequency cap (default max 2 contacts per 7 days)
    cutoff = now - timedelta(days=frequency_days)
    contact_count = await db["communications"].count_documents({
        "tenant_id": tenant_id,
        "record_id": record["record_id"],
        "status": {"$in": ["queued", "in_progress", "completed"]},
        "created_at": {"$gte": cutoff},
    })
    if contact_count >= max_frequency:
        return False, ComplianceReason.FREQUENCY_CAP

    # 7. Duplicate in-flight check
    in_flight = await db["communications"].count_documents({
        "tenant_id": tenant_id,
        "record_id": record["record_id"],
        "status": {"$in": ["queued", "in_progress"]},
    })
    if in_flight > 0:
        return False, ComplianceReason.DUPLICATE_IN_FLIGHT

    # 8. Test mode allowlist check
    test_mode = os.getenv("TEST_MODE", "true").lower() == "true"
    if test_mode:
        phone = record.get("phone", "")
        # Check tenant allowlist collection
        allowed_in_db = await db["tenant_allowlist"].find_one({"tenant_id": tenant_id, "phone": phone})
        # If tenant has specific allowlist entries, must match; otherwise allow synthetic phones
        has_allowlist = await db["tenant_allowlist"].count_documents({"tenant_id": tenant_id}) > 0
        if has_allowlist:
            if not allowed_in_db:
                return False, ComplianceReason.TEST_MODE_NOT_ALLOWLISTED
        else:
            if not (allowed_in_db or SYNTHETIC_PHONE_REGEX.match(phone)):
                return False, ComplianceReason.TEST_MODE_NOT_ALLOWLISTED

    return True, None


async def log_audit_trail(
    tenant_id: str,
    communication_id: str,
    record_id: str,
    channel: str,
    config_version: int,
    decision: str,
    campaign_id: Optional[str] = None,
    reason_code: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Write immutable audit record for every dispatch attempt."""
    db = get_db()
    entry = {
        "timestamp": timestamp or datetime.now(timezone.utc),
        "tenant_id": tenant_id,
        "campaign_id": campaign_id,
        "communication_id": communication_id,
        "record_id": record_id,
        "channel": channel,
        "config_version": config_version,
        "decision": decision,
        "reason_code": reason_code,
    }
    await db["audit_log"].insert_one(entry)
    entry.pop("_id", None)
    return entry
