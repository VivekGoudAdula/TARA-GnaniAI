"""
Campaign operational router: launch execution, lifecycle state controls,
live outcomes metrics aggregation, and interaction CSV export.
"""
from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel

from app.auth import TokenUser, get_current_user
from app.campaigns.launcher import cancel_campaign, launch_campaign, pause_campaign, resume_campaign
from app.communication.dispatcher import CommunicationDispatcher
from app.communication.provider import GnaniWebVoiceProvider
from app.db import get_db

router = APIRouter(prefix="/api/campaigns", tags=["campaign-ops"])
_dispatcher = CommunicationDispatcher(provider=GnaniWebVoiceProvider())


class LaunchRequest(BaseModel):
    confirm_count: int
    mode: str = "test"


@router.post("/{campaign_id}/launch")
async def launch_campaign_endpoint(
    campaign_id: str,
    req: LaunchRequest,
    current_user: TokenUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Execute test launch for campaign across all snapshot recipients."""
    return await launch_campaign(
        tenant_id=current_user.tenant_id,
        campaign_id=campaign_id,
        confirm_count=req.confirm_count,
        mode=req.mode,
        comm_port=_dispatcher,
    )


@router.post("/{campaign_id}/pause")
async def pause_campaign_endpoint(
    campaign_id: str, current_user: TokenUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Pause an active campaign."""
    return await pause_campaign(current_user.tenant_id, campaign_id)


@router.post("/{campaign_id}/resume")
async def resume_campaign_endpoint(
    campaign_id: str, current_user: TokenUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Resume a paused campaign."""
    return await resume_campaign(current_user.tenant_id, campaign_id)


@router.post("/{campaign_id}/cancel")
async def cancel_campaign_endpoint(
    campaign_id: str, current_user: TokenUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Cancel a campaign and halt further dispatches."""
    return await cancel_campaign(current_user.tenant_id, campaign_id)


@router.get("/{campaign_id}/outcomes")
async def get_campaign_outcomes(
    campaign_id: str, current_user: TokenUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Aggregate live outcome metrics, extraction statistics, and gate blocks."""
    db = get_db()
    camp = await db["campaigns"].find_one({"tenant_id": current_user.tenant_id, "id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    cursor = db["communications"].find({"tenant_id": current_user.tenant_id, "campaign_id": campaign_id})
    comms = [c async for c in cursor]

    status_counts = {"queued": 0, "in_progress": 0, "completed": 0, "failed": 0, "blocked": 0, "cancelled": 0}
    outcome_counts = {"interested": 0, "not_interested": 0, "callback": 0, "no_answer": 0, "unclear": 0}
    blocked_reasons: Dict[str, int] = {}
    total_duration = 0.0
    completed_count = 0

    for c in comms:
        st = c.get("status", "queued")
        status_counts[st] = status_counts.get(st, 0) + 1

        if st == "blocked" and c.get("blocked_reason"):
            r = c["blocked_reason"]
            blocked_reasons[r] = blocked_reasons.get(r, 0) + 1

        ext = c.get("extraction", {})
        oc = ext.get("outcome") or c.get("outcome")
        if oc in outcome_counts:
            outcome_counts[oc] += 1

        if c.get("duration_s"):
            total_duration += float(c["duration_s"])
            completed_count += 1

    avg_duration = round(total_duration / completed_count, 1) if completed_count > 0 else 0.0

    return {
        "campaign_id": campaign_id,
        "campaign_status": camp.get("status", "draft"),
        "total_dispatched": len(comms),
        "status_counts": status_counts,
        "outcome_counts": outcome_counts,
        "blocked_reasons": blocked_reasons,
        "avg_duration_s": avg_duration,
        "completed_count": completed_count,
    }


@router.get("/{campaign_id}/interactions/export")
async def export_interactions_csv(
    campaign_id: str, current_user: TokenUser = Depends(get_current_user)
) -> Response:
    """Export all communications/interactions for campaign as a tenant-isolated CSV."""
    db = get_db()
    camp = await db["campaigns"].find_one({"tenant_id": current_user.tenant_id, "id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    cursor = db["communications"].find(
        {"tenant_id": current_user.tenant_id, "campaign_id": campaign_id}
    ).sort("created_at", 1)
    comms = [c async for c in cursor]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "communication_id", "record_id", "first_name", "channel",
        "status", "blocked_reason", "outcome", "interest_level",
        "loan_amount_inr", "callback_time", "duration_s", "created_at"
    ])

    for c in comms:
        ext = c.get("extraction") or {}
        writer.writerow([
            c.get("communication_id", ""),
            c.get("record_id", ""),
            c.get("recipient_first_name", ""),
            c.get("channel", "voice"),
            c.get("status", ""),
            c.get("blocked_reason", ""),
            ext.get("outcome", c.get("outcome", "")),
            ext.get("interest_level", ""),
            ext.get("loan_amount_inr", ""),
            ext.get("callback_time", ""),
            c.get("duration_s", ""),
            str(c.get("created_at", "")),
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=campaign_{campaign_id}_interactions.csv"},
    )
