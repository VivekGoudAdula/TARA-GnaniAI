"""
Scoring router: executes batch scoring, retrieves customer/lead records with ranked product matches,
and enforces tenant isolation and explainability.
"""
from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import TokenUser, get_current_user
from app.db import get_db
from app.scoring.scorer import compute_fit_score, evaluate_eligibility

router = APIRouter(tags=["scoring"])


@router.post("/api/scoring/run")
async def run_scoring(current_user: TokenUser = Depends(get_current_user)) -> Dict[str, Any]:
    """Execute product fit scoring for all customers and leads of current tenant."""
    db = get_db()
    products_cursor = db["products"].find({"tenant_id": current_user.tenant_id, "active": True})
    products = [p async for p in products_cursor]

    if not products:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active products found for this tenant. Create or activate a product first.",
        )

    # Clean old product matches for this tenant only (never touches customers or leads)
    await db["product_matches"].delete_many({"tenant_id": current_user.tenant_id})

    now = datetime.now(timezone.utc)
    new_matches: List[Dict[str, Any]] = []
    records_scored = 0

    for rec_type, coll_name in [("customers", "customers"), ("leads", "leads")]:
        cursor = db[coll_name].find({"tenant_id": current_user.tenant_id})
        async for record in cursor:
            records_scored += 1
            for prod in products:
                eligible, failed_rules = evaluate_eligibility(record, prod)
                fit_score, band, explanations = compute_fit_score(record, prod)

                new_matches.append({
                    "match_id": f"mch_{uuid.uuid4().hex[:10]}",
                    "tenant_id": current_user.tenant_id,
                    "record_type": rec_type,
                    "record_id": record["record_id"],
                    "product_id": prod["product_id"],
                    "product_name": prod["name"],
                    "fit_score": fit_score,
                    "band": band,
                    "eligible": eligible,
                    "failed_rules": failed_rules,
                    "explanation": explanations,
                    "scored_at": now,
                    "model_version": "1.0.0",
                })

    if new_matches:
        await db["product_matches"].insert_many(new_matches)

    return {
        "status": "success",
        "records_scored": records_scored,
        "matches_generated": len(new_matches),
        "products_evaluated": len(products),
    }


async def _fetch_records_with_matches(
    coll_name: str,
    tenant_id: str,
    band: Optional[str] = None,
    product_id: Optional[str] = None,
    eligible: Optional[bool] = None,
    language: Optional[str] = None,
    consent: Optional[bool] = None,
) -> Dict[str, Any]:
    """Helper to fetch and filter records and attach their top product match."""
    db = get_db()
    query: Dict[str, Any] = {"tenant_id": tenant_id}
    if language:
        query["preferred_language"] = language
    if consent is not None:
        query["consent"] = consent

    records = [r async for r in db[coll_name].find(query, {"_id": 0})]

    # Fetch top matches for each record
    enriched = []
    high_count, med_count, low_count = 0, 0, 0

    for rec in records:
        match_query = {"tenant_id": tenant_id, "record_id": rec["record_id"]}
        if product_id:
            match_query["product_id"] = product_id
        if eligible is not None:
            match_query["eligible"] = eligible
        if band:
            match_query["band"] = band

        top_match = await db["product_matches"].find_one(
            match_query, {"_id": 0}, sort=[("fit_score", -1)]
        )

        # Count bands based on un-filtered top match
        overall_top = await db["product_matches"].find_one(
            {"tenant_id": tenant_id, "record_id": rec["record_id"]},
            {"_id": 0},
            sort=[("fit_score", -1)],
        )
        if overall_top:
            b = overall_top.get("band", "Low")
            if b == "High":
                high_count += 1
            elif b == "Medium":
                med_count += 1
            else:
                low_count += 1

        if (band or product_id or eligible is not None) and not top_match:
            continue

        rec["top_match"] = top_match
        enriched.append(rec)

    return {
        "items": enriched,
        "total": len(records),
        "high_count": high_count,
        "medium_count": med_count,
        "low_count": low_count,
    }


@router.get("/api/customers")
async def list_customers(
    band: Optional[str] = None,
    product_id: Optional[str] = None,
    eligible: Optional[bool] = None,
    language: Optional[str] = None,
    consent: Optional[bool] = None,
    current_user: TokenUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """List customer records with best fit scores and filter summary."""
    return await _fetch_records_with_matches(
        "customers", current_user.tenant_id, band, product_id, eligible, language, consent
    )


@router.get("/api/leads")
async def list_leads(
    band: Optional[str] = None,
    product_id: Optional[str] = None,
    eligible: Optional[bool] = None,
    language: Optional[str] = None,
    consent: Optional[bool] = None,
    current_user: TokenUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """List lead records with best fit scores and filter summary."""
    return await _fetch_records_with_matches(
        "leads", current_user.tenant_id, band, product_id, eligible, language, consent
    )


@router.get("/api/customers/{record_id}")
async def get_customer_detail(
    record_id: str,
    current_user: TokenUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get single customer record with all ranked product matches."""
    db = get_db()
    customer = await db["customers"].find_one(
        {"record_id": record_id, "tenant_id": current_user.tenant_id}, {"_id": 0}
    )
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    matches = [
        m async for m in db["product_matches"].find(
            {"record_id": record_id, "tenant_id": current_user.tenant_id}, {"_id": 0}
        ).sort("fit_score", -1)
    ]
    customer["product_matches"] = matches
    return customer


@router.get("/api/leads/{record_id}")
async def get_lead_detail(
    record_id: str,
    current_user: TokenUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get single lead record with all ranked product matches."""
    db = get_db()
    lead = await db["leads"].find_one(
        {"record_id": record_id, "tenant_id": current_user.tenant_id}, {"_id": 0}
    )
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    matches = [
        m async for m in db["product_matches"].find(
            {"record_id": record_id, "tenant_id": current_user.tenant_id}, {"_id": 0}
        ).sort("fit_score", -1)
    ]
    lead["product_matches"] = matches
    return lead

