"""
Campaign audience preview, exclusion rules, and snapshot immutability tests.
"""
from __future__ import annotations

from datetime import datetime, timezone
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import create_access_token
from app.db import get_db
from app.main import app


@pytest.mark.asyncio
async def test_audience_preview_100_fixture():
    """Test audience preview with 100 records (60 High, 25 Medium, 15 Low) and filter combinations."""
    db = get_db()
    t_id = f"ten_camp_prev_{uuid.uuid4().hex[:6]}"
    prod_id = f"prd_prev_{uuid.uuid4().hex[:6]}"
    token = create_access_token("u_prev", t_id, "prev@bank.com")
    headers = {"Authorization": f"Bearer {token}"}

    await db["products"].insert_one({"tenant_id": t_id, "product_id": prod_id, "name": "Auto Loan", "active": True})

    cust_docs, match_docs = [], []
    now = datetime.now(timezone.utc)
    for i in range(100):
        rid = f"rec_prv_{i}"
        band = "HIGH" if i < 60 else ("MEDIUM" if i < 85 else "LOW")
        score = 85 if band == "HIGH" else (65 if band == "MEDIUM" else 40)
        cust_docs.append({
            "record_id": rid, "tenant_id": t_id, "full_name": f"User {i}",
            "preferred_language": "en-IN", "city": "Mumbai", "phone": f"+9190000{i:05d}",
            "consent": True, "dnd": False
        })
        match_docs.append({
            "tenant_id": t_id, "product_id": prod_id, "record_id": rid,
            "fit_score": score, "band": band, "eligible": True, "scored_at": now
        })
    await db["customers"].insert_many(cust_docs)
    await db["product_matches"].insert_many(match_docs)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # All records
        r_all = await client.post("/api/campaigns/audience/preview", json={
            "audience_type": "customers", "product_id": prod_id, "filters": {}
        }, headers=headers)
        assert r_all.json()["matched_count"] == 100
        assert r_all.json()["summary"]["high"] == 60
        assert r_all.json()["summary"]["medium"] == 25
        assert r_all.json()["summary"]["low"] == 15

        # Filter High only
        r_high = await client.post("/api/campaigns/audience/preview", json={
            "audience_type": "customers", "product_id": prod_id, "filters": {"bands": ["HIGH"]}
        }, headers=headers)
        assert r_high.json()["matched_count"] == 60

        # Filter High + Medium
        r_hm = await client.post("/api/campaigns/audience/preview", json={
            "audience_type": "customers", "product_id": prod_id, "filters": {"bands": ["HIGH", "MEDIUM"]}
        }, headers=headers)
        assert r_hm.json()["matched_count"] == 85

        # Verify DB still has 100 records
        count_in_db = await db["customers"].count_documents({"tenant_id": t_id})
        assert count_in_db == 100


@pytest.mark.asyncio
async def test_snapshot_immutability_and_exclusion_rules():
    """Verify non-contactable excluded, ineligible override handling, and immutability across rescores."""
    db = get_db()
    t_id = f"ten_snap_{uuid.uuid4().hex[:6]}"
    token = create_access_token("u_snap", t_id, "snap@bank.com")
    headers = {"Authorization": f"Bearer {token}"}

    prod_id = f"prd_snap_{uuid.uuid4().hex[:6]}"
    await db["products"].insert_one({"tenant_id": t_id, "product_id": prod_id, "name": "Credit Card", "active": True})

    records = [
        {"record_id": "r1", "tenant_id": t_id, "full_name": "Ramesh Gupta", "phone": "+919000088881", "consent": True, "dnd": False, "preferred_language": "hi-IN"},
        {"record_id": "r2", "tenant_id": t_id, "full_name": "Suresh Patel", "phone": "+919000088882", "consent": True, "dnd": True, "preferred_language": "en-IN"},
        {"record_id": "r3", "tenant_id": t_id, "full_name": "Amit Sharma", "phone": "+919000088883", "consent": True, "dnd": False, "preferred_language": "hi-IN"},
        {"record_id": "r4", "tenant_id": t_id, "full_name": "Priya Das", "phone": "+919000088884", "consent": True, "dnd": False, "preferred_language": "en-IN"},
    ]
    matches = [
        {"tenant_id": t_id, "product_id": prod_id, "record_id": "r1", "fit_score": 90, "band": "HIGH", "eligible": True},
        {"tenant_id": t_id, "product_id": prod_id, "record_id": "r2", "fit_score": 85, "band": "HIGH", "eligible": True},
        {"tenant_id": t_id, "product_id": prod_id, "record_id": "r3", "fit_score": 60, "band": "MEDIUM", "eligible": False},
        {"tenant_id": t_id, "product_id": prod_id, "record_id": "r4", "fit_score": 30, "band": "LOW", "eligible": True},
    ]
    await db["customers"].insert_many(records)
    await db["product_matches"].insert_many(matches)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        c_res = await client.post("/api/campaigns", json={
            "name": "CC Campaign", "product_id": prod_id, "audience_type": "customers"
        }, headers=headers)
        camp_id = c_res.json()["id"]

        # Without override: r2 (dnd) and r3 (ineligible) excluded -> 2
        save1 = await client.put(f"/api/campaigns/{camp_id}/audience", json={
            "selection_mode": "filter", "filters": {}, "allow_ineligible_override": False
        }, headers=headers)
        assert save1.json()["recipient_count"] == 2
        assert save1.json()["excluded_non_contactable"] == 1
        assert save1.json()["excluded_ineligible"] == 1

        # With override: r2 (dnd) still excluded, r3 included -> 3
        save2 = await client.put(f"/api/campaigns/{camp_id}/audience", json={
            "selection_mode": "filter", "filters": {}, "allow_ineligible_override": True
        }, headers=headers)
        assert save2.json()["recipient_count"] == 3
        assert save2.json()["excluded_non_contactable"] == 1

        r3_doc = await db["campaign_recipients"].find_one({"campaign_id": camp_id, "record_id": "r3"})
        assert r3_doc["eligible"] is False
        assert "monthly_income_inr" not in r3_doc
        assert "phone" not in r3_doc

        # IMMUTABILITY TEST: Re-score or modify underlying customer match
        await db["product_matches"].update_one(
            {"tenant_id": t_id, "record_id": "r1", "product_id": prod_id},
            {"$set": {"fit_score": 20, "band": "LOW"}}
        )
        r1_snap = await db["campaign_recipients"].find_one({"campaign_id": camp_id, "record_id": "r1"})
        assert r1_snap["fit_score"] == 90
        assert r1_snap["band"] == "HIGH"
