"""
Campaign launch lifecycle, confirmation guard, lifecycle controls,
and interaction CSV export tests.
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
async def test_campaign_launch_refusal_and_successful_test_launch():
    """Verify launch refuses invalid conditions, and executes test launch when ready."""
    db = get_db()
    t_id = f"ten_lnch_{uuid.uuid4().hex[:6]}"
    other_t_id = f"ten_other_{uuid.uuid4().hex[:6]}"

    token = create_access_token("u_lnch", t_id, "lnch@bank.com")
    headers = {"Authorization": f"Bearer {token}"}
    other_token = create_access_token("u_oth", other_t_id, "oth@bank.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # 1. Seed product, customer, and ready campaign
    prod_id = f"prd_lnch_{uuid.uuid4().hex[:6]}"
    await db["products"].insert_one({"tenant_id": t_id, "product_id": prod_id, "name": "Auto Loan", "active": True})
    await db["tenants"].insert_one({"tenant_id": t_id, "name": "Launch Bank"})

    rec_id1 = f"r_pass_{uuid.uuid4().hex[:4]}"
    rec_id2 = f"r_dnd_{uuid.uuid4().hex[:4]}"
    now = datetime.now(timezone.utc)

    # rec1 is contactable synthetic phone; rec2 is DND flagged
    await db["customers"].insert_many([
        {"tenant_id": t_id, "record_id": rec_id1, "full_name": "Ajay Verma", "phone": "+919000066661", "consent": True, "dnd": False, "preferred_language": "hi-IN"},
        {"tenant_id": t_id, "record_id": rec_id2, "full_name": "Bina Shah", "phone": "+919000066662", "consent": True, "dnd": True, "preferred_language": "en-IN"},
    ])

    camp_id = f"camp_{uuid.uuid4().hex[:8]}"
    await db["campaigns"].insert_one({
        "id": camp_id, "tenant_id": t_id, "name": "Auto Q4", "product_id": prod_id,
        "product_name": "Auto Loan", "audience_type": "customers", "status": "draft",
        "recipient_count": 2, "current_voice_config_version": 1,
    })
    await db["campaign_recipients"].insert_many([
        {"campaign_id": camp_id, "tenant_id": t_id, "record_id": rec_id1, "first_name": "Ajay", "preferred_language": "hi-IN", "eligible": True, "contactable": True},
        {"campaign_id": camp_id, "tenant_id": t_id, "record_id": rec_id2, "first_name": "Bina", "preferred_language": "en-IN", "eligible": True, "contactable": False},
    ])
    await db["campaign_voice_configs"].insert_one({
        "campaign_id": camp_id, "tenant_id": t_id, "version": 1,
        "config": {
            "default_language": "hi-IN",
            "system_prompt": "Sell car loan to {{first_name}}",
            "opening_message": "Hello {{first_name}}, I am an automated AI assistant calling from {{bank_name}} regarding {{product_name}}.",
            "conversation_objective": "Sell", "success_condition": "Yes",
            "info_to_collect": [{"field": "interest", "question": "Interested?", "required": True}],
        }
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Refusal 1: Not in 'ready' status
        bad_status = await client.post(f"/api/campaigns/{camp_id}/launch", json={"confirm_count": 2, "mode": "test"}, headers=headers)
        assert bad_status.status_code == 400
        assert "must be 'ready'" in bad_status.json()["detail"]

        # Mark ready
        await db["campaigns"].update_one({"id": camp_id}, {"$set": {"status": "ready"}})

        # Refusal 2: Wrong confirm count
        bad_count = await client.post(f"/api/campaigns/{camp_id}/launch", json={"confirm_count": 99, "mode": "test"}, headers=headers)
        assert bad_count.status_code == 400

        # Cross-tenant launch refusal -> 404
        cross_res = await client.post(f"/api/campaigns/{camp_id}/launch", json={"confirm_count": 2, "mode": "test"}, headers=other_headers)
        assert cross_res.status_code == 404

        # Successful Launch
        ok_launch = await client.post(f"/api/campaigns/{camp_id}/launch", json={"confirm_count": 2, "mode": "test"}, headers=headers)
        assert ok_launch.status_code == 200
        data = ok_launch.json()
        assert data["status"] == "running"
        assert data["total_dispatched"] == 2

        # Verify recipient 2 was blocked by DND and audit log contains entries
        r2_doc = await db["campaign_recipients"].find_one({"campaign_id": camp_id, "record_id": rec_id2})
        assert r2_doc["status"] == "blocked"
        assert r2_doc["blocked_reason"] == "DND_FLAGGED"

        audit_count = await db["audit_log"].count_documents({"campaign_id": camp_id})
        assert audit_count >= 2

        # Test Lifecycle: Pause -> Resume -> Cancel
        pause_res = await client.post(f"/api/campaigns/{camp_id}/pause", headers=headers)
        assert pause_res.status_code == 200
        assert pause_res.json()["status"] == "paused"

        resume_res = await client.post(f"/api/campaigns/{camp_id}/resume", headers=headers)
        assert resume_res.status_code == 200
        assert resume_res.json()["status"] == "running"

        cancel_res = await client.post(f"/api/campaigns/{camp_id}/cancel", headers=headers)
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "cancelled"

        # Outcomes aggregate check
        outcomes_res = await client.get(f"/api/campaigns/{camp_id}/outcomes", headers=headers)
        assert outcomes_res.status_code == 200
        assert outcomes_res.json()["total_dispatched"] == 2

        # Export CSV check
        export_res = await client.get(f"/api/campaigns/{camp_id}/interactions/export", headers=headers)
        assert export_res.status_code == 200
        assert "text/csv" in export_res.headers["content-type"]
        assert "communication_id" in export_res.text

