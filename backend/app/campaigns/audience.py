"""
Audience targeting and recipient snapshot engine for campaigns.
Enforces non-contactable exclusion, eligibility rules, and tenant isolation.
Never stores sensitive contact or financial fields in recipient snapshots.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from app.campaigns.models import AudienceFilter, SaveAudienceRequest
from app.db import get_db


def extract_first_name(full_name: Optional[str]) -> str:
    """Extract clean first name from full name or default safely."""
    if not full_name or not full_name.strip():
        return "Customer"
    parts = full_name.strip().split()
    return parts[0] if parts else "Customer"


async def fetch_matching_records(
    tenant_id: str,
    audience_type: str,
    product_id: str,
    filters: AudienceFilter,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fetch customer or lead records joined with their product match score.
    Returns matched records and summary count distribution across all records.
    """
    db = get_db()
    coll_name = "customers" if audience_type == "customers" else "leads"

    # Fetch all records of the given audience type for this tenant
    records_cursor = db[coll_name].find({"tenant_id": tenant_id})
    records = [r async for r in records_cursor]

    # Fetch all product matches for this tenant and product
    matches_cursor = db["product_matches"].find({"tenant_id": tenant_id, "product_id": product_id})
    match_map = {m["record_id"]: m async for m in matches_cursor}

    # Summary distribution counters
    counts = {
        "total": len(records),
        "high": 0,
        "medium": 0,
        "low": 0,
        "eligible": 0,
        "not_eligible": 0,
        "contactable": 0,
        "not_contactable": 0,
    }

    matched_list: List[Dict[str, Any]] = []

    for rec in records:
        rec_id = rec["record_id"]
        match = match_map.get(rec_id, {})
        band = match.get("band", "LOW")
        score = match.get("fit_score", 0)
        eligible = match.get("eligible", False)
        contactable = bool(rec.get("consent", True) and not rec.get("dnd", False))

        # Update global distribution counters
        if band == "HIGH":
            counts["high"] += 1
        elif band == "MEDIUM":
            counts["medium"] += 1
        else:
            counts["low"] += 1

        if eligible:
            counts["eligible"] += 1
        else:
            counts["not_eligible"] += 1

        if contactable:
            counts["contactable"] += 1
        else:
            counts["not_contactable"] += 1

        # Check filters
        if filters.bands and band not in filters.bands:
            continue
        if filters.min_score is not None and score < filters.min_score:
            continue
        if filters.max_score is not None and score > filters.max_score:
            continue
        if filters.eligibility == "eligible" and not eligible:
            continue
        if filters.eligibility == "not_eligible" and eligible:
            continue
        if filters.language and rec.get("preferred_language") != filters.language:
            continue
        if filters.city and rec.get("city", "").lower() != filters.city.lower():
            continue

        matched_list.append({
            "record_id": rec_id,
            "first_name": extract_first_name(rec.get("full_name")),
            "preferred_language": rec.get("preferred_language", "en-IN"),
            "city": rec.get("city", ""),
            "fit_score": score,
            "band": band,
            "eligible": eligible,
            "contactable": contactable,
        })

    return matched_list, counts


async def create_recipient_snapshot(
    tenant_id: str,
    campaign_id: str,
    product_id: str,
    audience_type: str,
    req: SaveAudienceRequest,
) -> Dict[str, Any]:
    """
    Build immutable recipient snapshot for campaign. Non-contactable individuals
    are always excluded. Ineligible individuals are excluded unless override is enabled.
    """
    db = get_db()
    coll_name = "customers" if audience_type == "customers" else "leads"

    # Remove existing snapshot for this campaign
    await db["campaign_recipients"].delete_many({"tenant_id": tenant_id, "campaign_id": campaign_id})

    matched_list, _ = await fetch_matching_records(
        tenant_id=tenant_id,
        audience_type=audience_type,
        product_id=product_id,
        filters=req.filters,
    )
    rec_by_id = {r["record_id"]: r for r in matched_list}

    # Fetch extra records if manually selected
    if req.selected_record_ids:
        missing_ids = [rid for rid in req.selected_record_ids if rid not in rec_by_id]
        if missing_ids:
            cursor = db[coll_name].find({"tenant_id": tenant_id, "record_id": {"$in": missing_ids}})
            async for r in cursor:
                m = await db["product_matches"].find_one({
                    "tenant_id": tenant_id, "product_id": product_id, "record_id": r["record_id"]
                }) or {}
                rec_by_id[r["record_id"]] = {
                    "record_id": r["record_id"],
                    "first_name": extract_first_name(r.get("full_name")),
                    "preferred_language": r.get("preferred_language", "en-IN"),
                    "city": r.get("city", ""),
                    "fit_score": m.get("fit_score", 0),
                    "band": m.get("band", "LOW"),
                    "eligible": m.get("eligible", False),
                    "contactable": bool(r.get("consent", True) and not r.get("dnd", False)),
                }

    # Determine candidate IDs based on selection mode
    excluded = set(req.excluded_record_ids or [])
    if req.selection_mode == "manual":
        candidate_ids = [rid for rid in (req.selected_record_ids or []) if rid not in excluded]
    elif req.selection_mode == "combined":
        merged = set(rec_by_id.keys()) | set(req.selected_record_ids or [])
        candidate_ids = [rid for rid in merged if rid not in excluded]
    else:  # filter
        candidate_ids = [rid for rid in rec_by_id.keys() if rid not in excluded]

    now = datetime.now(timezone.utc)
    recipients_to_insert: List[Dict[str, Any]] = []
    excluded_non_contactable = 0
    excluded_ineligible = 0

    for rid in candidate_ids:
        rec = rec_by_id.get(rid)
        if not rec:
            continue

        # Rule 1: Non-contactable people (consent=false or dnd=true) are ALWAYS excluded
        if not rec["contactable"]:
            excluded_non_contactable += 1
            continue

        # Rule 2: Ineligible people excluded unless allow_ineligible_override is set
        if not rec["eligible"] and not req.allow_ineligible_override:
            excluded_ineligible += 1
            continue

        # Snapshot stores minimal safe fields: NO phone, email, income, or credit score
        recipients_to_insert.append({
            "campaign_id": campaign_id,
            "tenant_id": tenant_id,
            "record_id": rec["record_id"],
            "first_name": rec["first_name"],
            "preferred_language": rec["preferred_language"],
            "fit_score": rec["fit_score"],
            "band": rec["band"],
            "eligible": rec["eligible"],
            "contactable": True,
            "selection_source": req.selection_mode,
            "status": "PENDING",
            "created_at": now,
        })

    if recipients_to_insert:
        await db["campaign_recipients"].insert_many(recipients_to_insert)

    # Update campaign recipient count and override setting
    await db["campaigns"].update_one(
        {"tenant_id": tenant_id, "id": campaign_id},
        {"$set": {
            "recipient_count": len(recipients_to_insert),
            "allow_ineligible_override": req.allow_ineligible_override,
            "updated_at": now,
        }}
    )

    return {
        "recipient_count": len(recipients_to_insert),
        "excluded_non_contactable": excluded_non_contactable,
        "excluded_ineligible": excluded_ineligible,
    }
