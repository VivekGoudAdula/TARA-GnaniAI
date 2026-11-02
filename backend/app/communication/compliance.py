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
) -> Tuple[bool, Optional[str], bool]:
    """
    Evaluate compliance rules in strict priority order.
    Returns (is_allowed, failure_reason_code, window_override_applied).
    """
    db = get_db()
    now = evaluation_time or datetime.now(timezone.utc)

    # 1. Tenant mismatch
    if not record or record.get("tenant_id") != tenant_id:
        return False, ComplianceReason.TENANT_MISMATCH, False

    # 2. Channel validity
    if channel != "voice":
        return False, ComplianceReason.INVALID_CHANNEL_CONFIG, False

    # 3. Consent check
    if not record.get("consent", False):
        return False, ComplianceReason.CONSENT_MISSING, False

    # 4. Internal DND flag
    if record.get("dnd", False):
        return False, ComplianceReason.DND_FLAGGED, False

    # 5. Calling window check (09:00 to 21:00 IST)
    tenant_doc = await db["tenants"].find_one({"tenant_id": tenant_id}) or {}
    tenant_cfg = await db["tenant_configs"].find_one({"tenant_id": tenant_id}) or {}
    window_mode = tenant_cfg.get("calling_window_mode") or tenant_doc.get("calling_window_mode", "enforce")
    test_mode = os.getenv("TEST_MODE", "true").lower() == "true"
    window_override = bool(window_mode == "demo_override" and test_mode)

    if not window_override:
        start_h = tenant_doc.get("calling_window_start_hour", 9) if tenant_doc else 9
        end_h = tenant_doc.get("calling_window_end_hour", 21) if tenant_doc else 21
        if not is_within_calling_window(now, time(start_h, 0), time(end_h, 0)):
            return False, ComplianceReason.OUTSIDE_CALLING_WINDOW, False

    # 6. Frequency cap (default max 2 contacts per 7 days)
    cutoff = now - timedelta(days=frequency_days)
    contact_count = await db["communications"].count_documents({
        "tenant_id": tenant_id,
        "record_id": record["record_id"],
        "status": {"$in": ["queued", "in_progress", "completed"]},
        "created_at": {"$gte": cutoff},
    })
    if contact_count >= max_frequency:
        return False, ComplianceReason.FREQUENCY_CAP, window_override

    # 7. Duplicate in-flight check
    in_flight = await db["communications"].count_documents({
        "tenant_id": tenant_id,
        "record_id": record["record_id"],
        "status": {"$in": ["queued", "in_progress"]},
    })
    if in_flight > 0:
        return False, ComplianceReason.DUPLICATE_IN_FLIGHT, window_override

    # 8. Test mode allowlist check
    if test_mode:
        phone = record.get("phone", "")
        allowed_in_db = await db["tenant_allowlist"].find_one({"tenant_id": tenant_id, "phone": phone})
        has_allowlist = await db["tenant_allowlist"].count_documents({"tenant_id": tenant_id}) > 0
        if has_allowlist:
            if not allowed_in_db:
                return False, ComplianceReason.TEST_MODE_NOT_ALLOWLISTED, window_override
        else:
            if not (allowed_in_db or SYNTHETIC_PHONE_REGEX.match(phone)):
                return False, ComplianceReason.TEST_MODE_NOT_ALLOWLISTED, window_override

    return True, None, window_override


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
    window_override: bool = False,
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
        "window_override": window_override,
    }
    await db["audit_log"].insert_one(entry)
    entry.pop("_id", None)
    return entry

