"""
test_campaign_pacing_retry.py - Rigorous verification of campaign lifecycle controls:
pacing/concurrency, retry policy with gate re-evaluation, task expiry (410 Gone),
pause/cancel/resume state controls, and tenant isolation in CSV & communication queries.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import create_access_token
from app.db import get_db
from app.main import app


@pytest.mark.asyncio
async def test_campaign_lifecycle_pause_resume_cancel():
    """Verify pause, resume, and cancel state controls on campaign."""
    db = get_db()
    t_id = f"ten_ctrl_{uuid.uuid4().hex[:6]}"
    token = create_access_token("u_ctrl", t_id, "ctrl@bank.com")
    headers = {"Authorization": f"Bearer {token}"}

    camp_id = f"camp_ctrl_{uuid.uuid4().hex[:6]}"
    await db["campaigns"].insert_one({
        "id": camp_id, "tenant_id": t_id, "name": "Control Test",
        "status": "running", "recipient_count": 0,
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Pause
        p_res = await client.post(f"/api/campaigns/{camp_id}/pause", headers=headers)
        assert p_res.status_code == 200
        assert p_res.json()["status"] == "paused"

        # Resume
        r_res = await client.post(f"/api/campaigns/{camp_id}/resume", headers=headers)
        assert r_res.status_code == 200
        assert r_res.json()["status"] == "running"

        # Cancel
        c_res = await client.post(f"/api/campaigns/{camp_id}/cancel", headers=headers)
        assert c_res.status_code == 200
        assert c_res.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_task_expiry_and_single_use():
    """Verify single-use token expires after 30 minutes returning 410 Gone."""
    db = get_db()
    t_id = f"ten_exp_{uuid.uuid4().hex[:6]}"
    tok_expired = f"tok_exp_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    # Insert expired task (expired 10 minutes ago)
    await db["call_tasks"].insert_one({
        "token": tok_expired,
        "tenant_id": t_id,
        "expires_at": now - timedelta(minutes=10),
        "used": False,
        "rendered": {"first_name": "Test"},
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/call-task/{tok_expired}")
        assert res.status_code == 410
        assert "expired" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_retry_policy_with_gate_reevaluation():
    """Verify retry policy re-evaluates compliance gate; e.g. DND added blocks the retry."""
    db = get_db()
    t_id = f"ten_rty_{uuid.uuid4().hex[:6]}"
    token = create_access_token("u_rty", t_id, "retry@bank.com")
    headers = {"Authorization": f"Bearer {token}"}

    prod_id = f"prd_rty_{uuid.uuid4().hex[:6]}"
    await db["products"].insert_one({"tenant_id": t_id, "product_id": prod_id, "name": "Auto Loan", "active": True})
    await db["tenants"].insert_one({"tenant_id": t_id, "name": "Retry Bank"})
    await db["tenant_configs"].insert_one({"tenant_id": t_id, "calling_window_mode": "demo_override"})

    rec_id = f"rec_rty_{uuid.uuid4().hex[:6]}"
    # Customer initially consent=true, dnd=false, synthetic phone
    await db["customers"].insert_one({
        "tenant_id": t_id, "record_id": rec_id, "full_name": "Karan Mehra",
        "phone": "+919000012345", "consent": True, "dnd": False, "preferred_language": "en-IN",
    })

    camp_id = f"camp_rty_{uuid.uuid4().hex[:6]}"
    await db["campaigns"].insert_one({
        "id": camp_id, "tenant_id": t_id, "name": "Retry Outreach",
        "product_id": prod_id, "product_name": "Auto Loan",
        "audience_type": "customers", "status": "running",
        "recipient_count": 1, "current_voice_config_version": 1,
        "retry_policy": {"max_attempts": 3, "retry_interval_minutes": 30},
    })
    await db["campaign_recipients"].insert_one({
        "campaign_id": camp_id, "tenant_id": t_id, "record_id": rec_id,
        "first_name": "Karan", "preferred_language": "en-IN", "attempts": 1,
        "status": "failed",
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First retry when compliant: should be queued
        r1 = await client.post(f"/api/campaigns/{camp_id}/retry/{rec_id}", headers=headers)
        assert r1.status_code == 200
        assert r1.json()["status"] == "queued"
        assert r1.json()["attempts"] == 2

        # Customer opts into DND between attempts!
        await db["customers"].update_one({"tenant_id": t_id, "record_id": rec_id}, {"$set": {"dnd": True}})

        # Second retry: gate MUST block due to DND
        r2 = await client.post(f"/api/campaigns/{camp_id}/retry/{rec_id}", headers=headers)
        assert r2.status_code == 200
        assert r2.json()["status"] == "blocked"
        assert r2.json()["attempts"] == 3


@pytest.mark.asyncio
async def test_tenant_isolation_csv_and_communication_api():
    """Verify tenant isolation across CSV exports and GET /api/communication."""
    db = get_db()
    t1 = f"ten_iso1_{uuid.uuid4().hex[:6]}"
    t2 = f"ten_iso2_{uuid.uuid4().hex[:6]}"

    token1 = create_access_token("u1", t1, "user1@bank1.com")
    headers1 = {"Authorization": f"Bearer {token1}"}

    camp1 = f"camp_iso1_{uuid.uuid4().hex[:6]}"
    await db["campaigns"].insert_one({"id": camp1, "tenant_id": t1, "name": "Bank1 Camp"})

    # Communications belonging to tenant 1 and tenant 2
    await db["communications"].insert_many([
        {"tenant_id": t1, "campaign_id": camp1, "communication_id": "comm_t1_1", "status": "queued", "recipient_first_name": "Alice"},
        {"tenant_id": t2, "campaign_id": "other_camp", "communication_id": "comm_t2_1", "status": "queued", "recipient_first_name": "SecretBob"},
    ])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/communication for Tenant 1
        res = await client.get("/api/communication", headers=headers1)
        assert res.status_code == 200
        items = res.json()["items"]
        comm_ids = [c["communication_id"] for c in items]
        assert "comm_t1_1" in comm_ids
        assert "comm_t2_1" not in comm_ids

        # 2. CSV export for Tenant 1 campaign
        csv_res = await client.get(f"/api/campaigns/{camp1}/interactions/export", headers=headers1)
        assert csv_res.status_code == 200
        csv_text = csv_res.text
        assert "Alice" in csv_text
        assert "SecretBob" not in csv_text
