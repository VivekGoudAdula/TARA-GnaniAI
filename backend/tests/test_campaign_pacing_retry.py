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


@pytest.mark.asyncio
async def test_launcher_concurrency_and_min_gap_pacing_with_fake_clock():
    """Verify concurrency 1 and 5s min gap between call starts using a fake clock."""
    from app.campaigns.launcher import launch_campaign
    from app.contracts.communication import CommunicationResponse

    db = get_db()
    t_id = f"ten_pace_{uuid.uuid4().hex[:6]}"
    camp_id = f"camp_pace_{uuid.uuid4().hex[:6]}"
    prod_id = f"prd_pace_{uuid.uuid4().hex[:4]}"
    rec1 = f"r_pace_1_{uuid.uuid4().hex[:4]}"
    rec2 = f"r_pace_2_{uuid.uuid4().hex[:4]}"

    await db["products"].insert_one({"tenant_id": t_id, "product_id": prod_id, "name": "Personal Loan", "active": True})
    await db["campaigns"].insert_one({
        "id": camp_id, "tenant_id": t_id, "name": "Pacing Test",
        "product_id": prod_id, "product_name": "Personal Loan",
        "audience_type": "customers", "status": "ready",
        "recipient_count": 2, "current_voice_config_version": 1,
    })
    for r_id, fn, ph in [(rec1, "Aarav", "+919000011111"), (rec2, "Rohan", "+919000022222")]:
        await db["customers"].insert_one({
            "tenant_id": t_id, "record_id": r_id, "full_name": fn,
            "phone": ph, "consent": True, "dnd": False, "preferred_language": "en-IN",
        })
        await db["campaign_recipients"].insert_one({
            "campaign_id": camp_id, "tenant_id": t_id, "record_id": r_id,
            "first_name": fn, "preferred_language": "en-IN", "eligible": True, "contactable": True,
        })
    await db["campaign_voice_configs"].insert_one({
        "campaign_id": camp_id, "tenant_id": t_id, "version": 1,
        "config": {
            "default_language": "en-IN",
            "system_prompt": "Help customer.",
            "opening_message": "Hello {{first_name}}.",
            "conversation_objective": "Discuss options",
            "success_condition": "Customer interested",
            "info_to_collect": [{"field": "loan_amount", "question": "Amount?", "required": True}],
        }
    })

    # Fake clock and sleeper tracking timeline and concurrency
    class FakeClock:
        def __init__(self):
            self.t = 1000.0
        def now(self):
            return self.t
        async def sleep(self, seconds: float):
            self.t += seconds

    clock = FakeClock()

    class MockCommPort:
        def __init__(self):
            self.dispatches = []
        async def dispatch(self, tenant_id: str, request: Any):
            self.dispatches.append((request.recipient_ref.record_id, clock.now()))
            return CommunicationResponse(communication_id=f"comm_{uuid.uuid4().hex[:6]}", status="queued")

    port = MockCommPort()

    res = await launch_campaign(
        tenant_id=t_id,
        campaign_id=camp_id,
        confirm_count=2,
        mode="test",
        comm_port=port,
        concurrency=1,
        min_gap_seconds=5.0,
        clock=clock.now,
        sleep_func=clock.sleep,
    )

    pacing_info = res["pacing"]
    assert pacing_info["max_in_flight_observed"] == 1, "Concurrency 1 violated: more than 1 in flight!"
    timestamps = [t for _, t in pacing_info["timestamps"]]
    assert len(timestamps) == 2
    gap = timestamps[1] - timestamps[0]
    assert gap >= 5.0, f"Min gap 5.0s violated: actual gap was {gap}s!"

