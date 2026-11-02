"""
Campaign voice config versioning, template validation, and sanitized preview tests.
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
async def test_voice_config_versioning_and_validation_and_preview():
    """Test append-only voice config versions, variable rejection, AI notice check, and sanitized preview."""
    db = get_db()
    t_id = f"ten_cfg_{uuid.uuid4().hex[:6]}"
    token = create_access_token("u_cfg", t_id, "cfg@bank.com")
    headers = {"Authorization": f"Bearer {token}"}
    await db["tenants"].insert_one({"tenant_id": t_id, "name": "Kotak Demo Bank"})

    prod_id = f"prd_cfg_{uuid.uuid4().hex[:6]}"
    await db["products"].insert_one({"tenant_id": t_id, "product_id": prod_id, "name": "Personal Loan", "active": True})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        c_res = await client.post("/api/campaigns", json={
            "name": "PL Promo", "product_id": prod_id, "audience_type": "customers"
        }, headers=headers)
        camp_id = c_res.json()["id"]

        # Reject unknown template variable
        bad_cfg = {
            "default_language": "hi-IN",
            "voice_by_language": {"en-IN": "Nalini", "hi-IN": "Nalini", "te-IN": "Suhana"},
            "system_prompt": "Hello {{secret_account_balance}}",
            "opening_message": "Calling for {{first_name}}",
            "conversation_objective": "Sell",
            "info_to_collect": [{"field": "intent", "question": "Interested?", "required": True}],
            "success_condition": "Yes",
        }
        rej_res = await client.put(f"/api/campaigns/{camp_id}/voice-config", json=bad_cfg, headers=headers)
        assert rej_res.status_code == 422

        # Valid config update creates version 2
        good_cfg = bad_cfg.copy()
        good_cfg["system_prompt"] = "Assist {{first_name}} regarding {{product_name}} from {{bank_name}}."
        v2_res = await client.put(f"/api/campaigns/{camp_id}/voice-config", json=good_cfg, headers=headers)
        assert v2_res.status_code == 200
        assert v2_res.json()["version"] == 2

        # Validation without recipients must fail
        val_res = await client.post(f"/api/campaigns/{camp_id}/validate", headers=headers)
        assert val_res.json()["valid"] is False
        assert any("0 recipients" in issue for issue in val_res.json()["issues"])

        # Cannot mark ready if invalid
        ready_fail = await client.post(f"/api/campaigns/{camp_id}/mark-ready", headers=headers)
        assert ready_fail.status_code == 400

        # Add 1 recipient to snapshot
        await db["campaign_recipients"].insert_one({
            "campaign_id": camp_id, "tenant_id": t_id, "record_id": "rec_vikram",
            "first_name": "Vikram", "preferred_language": "hi-IN", "fit_score": 88,
            "band": "HIGH", "eligible": True, "contactable": True, "status": "PENDING",
            "created_at": datetime.now(timezone.utc)
        })

        # Re-validate: now passes and auto-prepends AI disclosure
        val_pass = await client.post(f"/api/campaigns/{camp_id}/validate", headers=headers)
        assert val_pass.json()["valid"] is True

        # Mark ready succeeds
        ready_ok = await client.post(f"/api/campaigns/{camp_id}/mark-ready", headers=headers)
        assert ready_ok.status_code == 200
        assert ready_ok.json()["status"] == "ready"

        # Preview payload: check variables substituted and NO sensitive financial fields
        prev_res = await client.post(f"/api/campaigns/{camp_id}/preview", headers=headers)
        assert prev_res.status_code == 200
        payload = prev_res.json()
        assert payload["first_name"] == "Vikram"
        assert payload["product_name"] == "Personal Loan"
        assert payload["bank_name"] == "Kotak Demo Bank"
        assert "Vikram" in payload["system_prompt"]
        assert "Personal Loan" in payload["system_prompt"]
        assert "AI" in payload["opening_message"] or "automated" in payload["opening_message"]

        # Explicit check: strictly no phone, email, income, or credit score
        for forbidden in ["phone", "email", "income", "credit_score", "monthly_income_inr"]:
            assert forbidden not in payload
