"""
Mocked campaign dispatch integration test.
Launches a 2-recipient test campaign, simulates completed tester responses,
and verifies outcomes and extraction records without external API calls.
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
async def test_mocked_campaign_dispatch_and_interaction_recording():
    """Launch 2-recipient campaign, simulate completed session, verify interaction outcome record."""
    db = get_db()
    t_id = f"ten_live_{uuid.uuid4().hex[:6]}"
    token = create_access_token("u_live", t_id, "live@bank.com")
    headers = {"Authorization": f"Bearer {token}"}

    prod_id = f"prd_live_{uuid.uuid4().hex[:6]}"
    await db["products"].insert_one({"tenant_id": t_id, "product_id": prod_id, "name": "Live Personal Loan", "active": True})
    await db["tenants"].insert_one({"tenant_id": t_id, "name": "Live Test Bank"})

    # Seed 2 customer records
    r1 = f"r_live1_{uuid.uuid4().hex[:4]}"
    r2 = f"r_live2_{uuid.uuid4().hex[:4]}"
    now = datetime.now(timezone.utc)

    await db["customers"].insert_many([
        {"tenant_id": t_id, "record_id": r1, "full_name": "Deepak Joshi", "phone": "+919000077771", "consent": True, "dnd": False, "preferred_language": "hi-IN"},
        {"tenant_id": t_id, "record_id": r2, "full_name": "Sunita Rao", "phone": "+919000077772", "consent": True, "dnd": False, "preferred_language": "te-IN"},
    ])

    camp_id = f"camp_live_{uuid.uuid4().hex[:6]}"
    await db["campaigns"].insert_one({
        "id": camp_id, "tenant_id": t_id, "name": "Live Test Outreach",
        "product_id": prod_id, "product_name": "Live Personal Loan",
        "audience_type": "customers", "status": "ready",
        "recipient_count": 2, "current_voice_config_version": 1,
    })
    await db["campaign_recipients"].insert_many([
        {"campaign_id": camp_id, "tenant_id": t_id, "record_id": r1, "first_name": "Deepak", "preferred_language": "hi-IN", "eligible": True, "contactable": True},
        {"campaign_id": camp_id, "tenant_id": t_id, "record_id": r2, "first_name": "Sunita", "preferred_language": "te-IN", "eligible": True, "contactable": True},
    ])
    await db["campaign_voice_configs"].insert_one({
        "campaign_id": camp_id, "tenant_id": t_id, "version": 1,
        "config": {
            "default_language": "hi-IN",
            "system_prompt": "Help {{first_name}} with personal loan",
            "opening_message": "Hello {{first_name}}, I am an automated AI assistant calling from {{bank_name}}.",
            "conversation_objective": "Sell", "success_condition": "Yes",
            "info_to_collect": [{"field": "interest", "question": "Interested?", "required": True}],
        }
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Launch campaign in test mode
        launch_res = await client.post(
            f"/api/campaigns/{camp_id}/launch",
            json={"confirm_count": 2, "mode": "test"},
            headers=headers,
        )
        assert launch_res.status_code == 200
        assert launch_res.json()["status"] == "running"

        # Check recipients got task tokens
        r1_snap = await db["campaign_recipients"].find_one({"campaign_id": camp_id, "record_id": r1})
        assert r1_snap.get("task_token") is not None
        task_token = r1_snap["task_token"]

        # Simulate tester connecting and completing call
        start_res = await client.post(f"/api/call-task/{task_token}/start")
        assert start_res.status_code == 200

        complete_res = await client.post(f"/api/call-task/{task_token}/complete", json={
            "status": "completed",
            "duration_s": 28.4,
            "outcome": "interested",
            "extraction": {
                "interest_level": "high",
                "loan_amount_inr": 250000.0,
                "callback_time": "Tomorrow 3 PM",
                "language_used": ["hi-IN"],
                "outcome": "interested",
                "summary": "Customer interested in 2.5L Personal Loan",
            },
            "transcript": [
                {"speaker": "agent", "text": "Hello Deepak, I am an AI assistant.", "latency_ms": 1500},
                {"speaker": "user", "text": "Yes, I need a personal loan.", "latency_ms": 200},
            ],
            "voice_used": {"1": "Nalini"},
        })
        assert complete_res.status_code == 200

        # Verify outcome landed in communications record
        comm_doc = await db["communications"].find_one({
            "tenant_id": t_id,
            "campaign_id": camp_id,
            "record_id": r1,
        })
        assert comm_doc is not None
        assert comm_doc["status"] == "completed"
        assert comm_doc["extraction"]["loan_amount_inr"] == 250000.0
        assert comm_doc["extraction"]["interest_level"] == "high"

        # Verify outcomes aggregation
        outcomes_res = await client.get(f"/api/campaigns/{camp_id}/outcomes", headers=headers)
        assert outcomes_res.status_code == 200
        outcomes_data = outcomes_res.json()
        assert outcomes_data["outcome_counts"]["interested"] >= 1

