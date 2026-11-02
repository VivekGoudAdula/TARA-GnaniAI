"""
Campaign management API router: creation, audience snapshotting, versioned voice configs,
regulatory validation, and communication preview payloads.
"""
from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import TokenUser, get_current_user
from app.campaigns.audience import create_recipient_snapshot, fetch_matching_records
from app.campaigns.models import (
    AudiencePreviewRequest,
    CampaignCreateRequest,
    CampaignUpdateRequest,
    SaveAudienceRequest,
    VoiceConfigData,
)
from app.campaigns.validator import render_recipient_preview, validate_campaign
from app.campaigns.voice_config import (
    create_voice_config_version,
    default_voice_config_dict,
    fetch_campaign_voice_config,
    fetch_voice_config_history,
)
from app.db import get_db

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.get("")
async def list_campaigns(current_user: TokenUser = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """List all campaigns belonging to the verified tenant."""
    db = get_db()
    cursor = db["campaigns"].find({"tenant_id": current_user.tenant_id}, {"_id": 0}).sort("created_at", -1)
    return [c async for c in cursor]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    req: CampaignCreateRequest, current_user: TokenUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a new draft campaign and initialize its version 1 voice configuration."""
    db = get_db()
    prod = await db["products"].find_one({"tenant_id": current_user.tenant_id, "product_id": req.product_id})
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found for this tenant.")

    campaign_id = f"camp_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    campaign_doc = {
        "id": campaign_id,
        "tenant_id": current_user.tenant_id,
        "name": req.name,
        "product_id": req.product_id,
        "product_name": prod.get("name", ""),
        "audience_type": req.audience_type,
        "objective": req.objective,
        "description": req.description,
        "status": "draft",
        "allow_ineligible_override": req.allow_ineligible_override,
        "recipient_count": 0,
        "current_voice_config_version": 1,
        "created_at": now,
        "updated_at": now,
    }
    await db["campaigns"].insert_one(campaign_doc)
    await db["campaign_voice_configs"].insert_one({
        "campaign_id": campaign_id, "tenant_id": current_user.tenant_id,
        "version": 1, "created_at": now, "config": default_voice_config_dict(),
    })
    campaign_doc.pop("_id", None)
    return campaign_doc


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str, current_user: TokenUser = Depends(get_current_user)) -> Dict[str, Any]:
    """Retrieve campaign details; returns 404 if absent or across tenants."""
    db = get_db()
    camp = await db["campaigns"].find_one({"tenant_id": current_user.tenant_id, "id": campaign_id}, {"_id": 0})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return camp


@router.put("/{campaign_id}")
async def update_campaign(
    campaign_id: str, req: CampaignUpdateRequest, current_user: TokenUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update metadata for an existing draft campaign."""
    db = get_db()
    camp = await db["campaigns"].find_one({"tenant_id": current_user.tenant_id, "id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    fields: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
    if req.name is not None:
        fields["name"] = req.name
    if req.objective is not None:
        fields["objective"] = req.objective
    if req.description is not None:
        fields["description"] = req.description
    if req.allow_ineligible_override is not None:
        fields["allow_ineligible_override"] = req.allow_ineligible_override

    await db["campaigns"].update_one({"tenant_id": current_user.tenant_id, "id": campaign_id}, {"$set": fields})
    return await get_campaign(campaign_id, current_user)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(campaign_id: str, current_user: TokenUser = Depends(get_current_user)) -> None:
    """Delete draft or cancelled campaign and purge its snapshots."""
    db = get_db()
    camp = await db["campaigns"].find_one({"tenant_id": current_user.tenant_id, "id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    if camp.get("status") not in ["draft", "cancelled"]:
        raise HTTPException(status_code=400, detail="Only draft or cancelled campaigns can be deleted.")

    await db["campaigns"].delete_one({"tenant_id": current_user.tenant_id, "id": campaign_id})
    await db["campaign_recipients"].delete_many({"tenant_id": current_user.tenant_id, "campaign_id": campaign_id})
    await db["campaign_voice_configs"].delete_many({"tenant_id": current_user.tenant_id, "campaign_id": campaign_id})


@router.post("/audience/preview")
async def preview_audience(
    req: AudiencePreviewRequest, current_user: TokenUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Calculate audience match counts and sample records for targeting filters."""
    matched_records, counts = await fetch_matching_records(
        tenant_id=current_user.tenant_id,
        audience_type=req.audience_type,
        product_id=req.product_id,
        filters=req.filters,
    )
    return {
        "summary": counts,
        "matched_count": len(matched_records),
        "sample": matched_records[:25],
    }


@router.put("/{campaign_id}/audience")
async def save_audience(
    campaign_id: str, req: SaveAudienceRequest, current_user: TokenUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Generate and store immutable recipient snapshot for the campaign."""
    db = get_db()
    camp = await db["campaigns"].find_one({"tenant_id": current_user.tenant_id, "id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    return await create_recipient_snapshot(
        tenant_id=current_user.tenant_id,
        campaign_id=campaign_id,
        product_id=camp["product_id"],
        audience_type=camp["audience_type"],
        req=req,
    )


@router.get("/{campaign_id}/recipients")
async def get_recipients(
    campaign_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: TokenUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve paginated recipients from immutable campaign snapshot."""
    db = get_db()
    camp = await db["campaigns"].find_one({"tenant_id": current_user.tenant_id, "id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    total = await db["campaign_recipients"].count_documents({"tenant_id": current_user.tenant_id, "campaign_id": campaign_id})
    cursor = db["campaign_recipients"].find(
        {"tenant_id": current_user.tenant_id, "campaign_id": campaign_id}, {"_id": 0}
    ).skip(skip).limit(limit)
    items = [r async for r in cursor]
    return {"total": total, "recipients": items}


@router.get("/{campaign_id}/voice-config")
async def get_voice_config_endpoint(campaign_id: str, current_user: TokenUser = Depends(get_current_user)) -> Dict[str, Any]:
    return await fetch_campaign_voice_config(current_user.tenant_id, campaign_id)


@router.put("/{campaign_id}/voice-config")
async def save_voice_config_endpoint(
    campaign_id: str, config: VoiceConfigData, current_user: TokenUser = Depends(get_current_user)
) -> Dict[str, Any]:
    return await create_voice_config_version(current_user.tenant_id, campaign_id, config)


@router.get("/{campaign_id}/voice-config/versions")
async def list_voice_config_versions_endpoint(campaign_id: str, current_user: TokenUser = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return await fetch_voice_config_history(current_user.tenant_id, campaign_id)


@router.post("/{campaign_id}/validate")
async def validate_campaign_endpoint(
    campaign_id: str, current_user: TokenUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Evaluate completeness and compliance checks for campaign."""
    is_valid, issues = await validate_campaign(current_user.tenant_id, campaign_id)
    return {"valid": is_valid, "issues": issues}


@router.post("/{campaign_id}/preview")
async def preview_rendered_voice(
    campaign_id: str,
    record_id: Optional[str] = None,
    current_user: TokenUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Render sanitized prompt & opening message preview using recipient variables."""
    try:
        return await render_recipient_preview(current_user.tenant_id, campaign_id, record_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{campaign_id}/mark-ready")
async def mark_campaign_ready(
    campaign_id: str, current_user: TokenUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Transition campaign status from draft to ready once validation passes."""
    is_valid, issues = await validate_campaign(current_user.tenant_id, campaign_id)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Campaign validation failed", "issues": issues},
        )
    db = get_db()
    await db["campaigns"].update_one(
        {"tenant_id": current_user.tenant_id, "id": campaign_id},
        {"$set": {"status": "ready", "updated_at": datetime.now(timezone.utc)}},
    )
    return {"status": "ready", "message": "Campaign validated and marked ready for launch."}
