"""
Integration tests for Communication API: idempotency, tenant isolation,
and public single-use tester tokens with sanitized voice payloads.
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
async def test_communication_idempotency_and_tenant_isolation():
    """Verify that identical idempotency_key yields same communication and cross-tenant lookups 404."""
    db = get_db()
    t_id = f"ten_comm_{uuid.uuid4().hex[:6]}"
    other_t_id = f"ten_other_{uuid.uuid4().hex[:6]}"

    token = create_access_token("u_comm", t_id, "comm@bank.com")
    other_token = create_access_token("u_oth", other_t_id, "oth@bank.com")
    headers = {"Authorization": f"Bearer {token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Seed customer record
    rec_id = f"rec_{uuid.uuid4().hex[:6]}"
    await db["customers"].insert_one({
        "tenant_id": t_id, "record_id": rec_id, "full_name": "Kavita Rao",
        "phone": "+919000055555", "consent": True, "dnd": False, "preferred_language": "en-IN"
    })

    send_payload = {
        "recipient_ref": {"record_id": rec_id, "record_type": "customers"},
        "channel": "voice",
        "config_version": 1,
        "idempotency_key": f"idem_{uuid.uuid4().hex[:8]}",
        "rendered": {
            "first_name": "Kavita", "bank_name": "Axis Demo", "product_name": "Home Loan",
            "language": "en-IN", "system_prompt": "Hello Kavita",
            "opening_message": "Hello Kavita, I am an AI assistant.", "max_turns": 8
        }
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First send
        res1 = await client.post("/api/communication/send", json=send_payload, headers=headers)
        assert res1.status_code == 200
        data1 = res1.json()
        comm_id = data1["communication_id"]
        assert data1["status"] in ["queued", "blocked"]

        # Second send with same idempotency_key -> returns exact same communication_id
        res2 = await client.post("/api/communication/send", json=send_payload, headers=headers)
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["communication_id"] == comm_id

        # Cross-tenant read -> 404
        cross_res = await client.get(f"/api/communication/{comm_id}", headers=other_headers)
        assert cross_res.status_code == 404

        # Verified tenant read -> 200
        auth_res = await client.get(f"/api/communication/{comm_id}", headers=headers)
        assert auth_res.status_code == 200
        assert auth_res.json()["communication_id"] == comm_id


@pytest.mark.asyncio
async def test_public_call_task_token_sanitization_and_single_use():
    """Verify tester token returns only permitted fields and enforces single-use expiry."""
    db = get_db()
    t_id = f"ten_tok_{uuid.uuid4().hex[:6]}"
    token_str = f"tok_test_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    # Seed call task with rendered voice config
    await db["call_tasks"].insert_one({
        "token": token_str,
        "tenant_id": t_id,
        "recipient_first_name": "Siddharth",
        "product_name": "Two Wheeler Loan",
        "bank_name": "HDFC Demo",
        "language": "hi-IN",
        "rendered": {
            "system_prompt": "Help Siddharth with bike loan",
            "opening_message": "Hello Siddharth, I am an automated AI assistant calling from HDFC Demo.",
            "max_turns": 8,
            "info_to_collect": [{"field": "interest", "question": "Interested?", "required": True}],
        },
        "used": False,
        "status": "queued",
        "expires_at": now + timedelta(minutes=30),
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Public lookup without JWT
        res = await client.get(f"/api/call-task/{token_str}")
        assert res.status_code == 200
        payload = res.json()
        assert payload["first_name"] == "Siddharth"
        assert payload["product_name"] == "Two Wheeler Loan"
        assert payload["bank_name"] == "HDFC Demo"
        assert "AI assistant" in payload["opening_message"]

        # Verify strict field sanitization: no sensitive fields
        for forbidden in ["phone", "email", "income", "credit_score", "monthly_income_inr"]:
            assert forbidden not in payload

        # Complete task
        comp_res = await client.post(f"/api/call-task/{token_str}/complete", json={
            "status": "completed", "duration_s": 42.5, "outcome": "interested"
        })
        assert comp_res.status_code == 200

        # Attempting second use returns 410 Gone
        re_res = await client.get(f"/api/call-task/{token_str}")
        assert re_res.status_code == 410

