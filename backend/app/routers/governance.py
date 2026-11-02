"""
Governance and compliance audit router.
Provides filterable regulatory audit logs, policy transparency cards,
and dashboard compliance metrics.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query

from app.auth import TokenUser, get_current_user
from app.db import get_db

router = APIRouter(prefix="/api/governance", tags=["governance"])


@router.get("/audit-log")
async def get_audit_log(
    campaign_id: Optional[str] = Query(None),
    decision: Optional[str] = Query(None),
    reason_code: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: TokenUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve immutable audit log records for verified tenant."""
    db = get_db()
    query: Dict[str, Any] = {"tenant_id": current_user.tenant_id}
    if campaign_id:
        query["campaign_id"] = campaign_id
    if decision:
        query["decision"] = decision
    if reason_code:
        query["reason_code"] = reason_code

    total = await db["audit_log"].count_documents(query)
    cursor = db["audit_log"].find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit)
    items = [a async for a in cursor]
    return {"total": total, "items": items}


@router.get("/compliance-info")
async def get_compliance_info(current_user: TokenUser = Depends(get_current_user)) -> Dict[str, Any]:
    """Return explicit transparency declaration of active compliance controls and limitations."""
    return {
        "active_controls": [
            {"id": "CONSENT", "name": "Explicit Consent Attestation", "description": "Records without consent=true are blocked."},
            {"id": "DND", "name": "Internal DND Flag", "description": "Records with dnd=true are blocked from outreach."},
            {"id": "WINDOW", "name": "Calling Window (09:00 - 21:00 IST)", "description": "Automated dispatch blocked outside permitted hours."},
            {"id": "FREQ_CAP", "name": "Frequency Capping", "description": "Maximum 2 contacts per customer per 7 days across channels."},
            {"id": "DEDUP", "name": "In-Flight Deduplication", "description": "Blocks multiple active dispatches to the same person."},
            {"id": "TEST_MODE", "name": "Test Mode Restriction", "description": "Web tester calls only to verified synthetic test profiles."},
        ],
        "unsupported_controls": [
            {"name": "National NDNC Registry API", "reason": "No live TRAI/DoT National Do Not Call registry lookup integrated."},
            {"name": "PSTN / Carrier Gateway", "reason": "Demonstration platform uses Web RTC/WebSocket test links only, no telephony."},
            {"name": "Regulatory Certification", "reason": "Experimental academic/hackathon showcase; not RBI/TRAI certified."},
        ],
    }


@router.get("/dashboard-summary")
async def get_dashboard_governance_summary(current_user: TokenUser = Depends(get_current_user)) -> Dict[str, Any]:
    """Provide dashboard KPI metrics for recent campaign run and gate compliance blocks."""
    db = get_db()
    # Total blocked attempts
    blocked_count = await db["audit_log"].count_documents({"tenant_id": current_user.tenant_id, "decision": "BLOCKED"})
    allowed_count = await db["audit_log"].count_documents({"tenant_id": current_user.tenant_id, "decision": "ALLOWED"})

    # Reason breakdown
    pipeline = [
        {"$match": {"tenant_id": current_user.tenant_id, "decision": "BLOCKED"}},
        {"$group": {"_id": "$reason_code", "count": {"$sum": 1}}},
    ]
    reasons_cursor = db["audit_log"].aggregate(pipeline)
    blocked_by_reason = {doc["_id"]: doc["count"] async for doc in reasons_cursor if doc["_id"]}

    # Last active or completed campaign
    last_camp = await db["campaigns"].find_one(
        {"tenant_id": current_user.tenant_id, "status": {"$in": ["running", "completed", "ready"]}},
        {"_id": 0},
        sort=[("updated_at", -1)],
    )

    return {
        "blocked_by_gate": blocked_count,
        "allowed_dispatches": allowed_count,
        "blocked_by_reason": blocked_by_reason,
        "last_campaign": last_camp,
    }
