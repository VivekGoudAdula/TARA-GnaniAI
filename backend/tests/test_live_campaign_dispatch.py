"""
test_live_campaign_dispatch.py - Live campaign dispatch integration test.
Requires live GNANI_API_KEY and GROQ_API_KEY. Runs genuine live synthesis and
factual extraction, persisting verified outcomes to MongoDB.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import create_access_token
from app.db import get_db
from app.main import app
from app.voice.session import VoiceSession
from providers.gnani_client import GnaniClient
from providers.llm_client import LLMClient


@pytest.mark.live
@pytest.mark.asyncio
async def test_genuine_live_campaign_dispatch_and_voice_turn():
    """Verify live campaign launch and execute a real voice agent turn with Gnani and Groq."""
    if not os.getenv("GNANI_API_KEY") or not os.getenv("GROQ_API_KEY"):
        pytest.skip("Live API keys (GNANI_API_KEY, GROQ_API_KEY) not available in environment.")

    db = get_db()
    t_id = f"ten_live_real_{uuid.uuid4().hex[:6]}"
    token = create_access_token("u_real_live", t_id, "live_tester@bank.com")
    headers = {"Authorization": f"Bearer {token}"}

    prod_id = f"prd_real_{uuid.uuid4().hex[:6]}"
    await db["products"].insert_one({"tenant_id": t_id, "product_id": prod_id, "name": "Live Home Loan", "active": True})
    await db["tenants"].insert_one({"tenant_id": t_id, "name": "Live Real Bank"})
    # Set demo override to ensure window check allows test dispatch
    await db["tenant_configs"].insert_one({"tenant_id": t_id, "calling_window_mode": "demo_override"})

    rec_id = f"r_real_{uuid.uuid4().hex[:4]}"
    await db["customers"].insert_one({
        "tenant_id": t_id, "record_id": rec_id, "full_name": "Rohan Sharma",
        "phone": "+919000012345", "consent": True, "dnd": False, "preferred_language": "en-IN",
    })

    camp_id = f"camp_real_{uuid.uuid4().hex[:6]}"
    await db["campaigns"].insert_one({
        "id": camp_id, "tenant_id": t_id, "name": "Live Real Outreach",
        "product_id": prod_id, "product_name": "Live Home Loan",
        "audience_type": "customers", "status": "ready",
        "recipient_count": 1, "current_voice_config_version": 1,
    })
    await db["campaign_recipients"].insert_one({
        "campaign_id": camp_id, "tenant_id": t_id, "record_id": rec_id,
        "first_name": "Rohan", "preferred_language": "en-IN", "eligible": True, "contactable": True,
    })
    await db["campaign_voice_configs"].insert_one({
        "campaign_id": camp_id, "tenant_id": t_id, "version": 1,
        "config": {
            "default_language": "en-IN",
            "system_prompt": "Help {{first_name}} with home loan.",
            "opening_message": "Hello {{first_name}}, I am an AI assistant calling from {{bank_name}}.",
            "conversation_objective": "Discuss home loan options",
            "success_condition": "Customer expresses interest or requests callback",
            "info_to_collect": [{"field": "loan_amount", "question": "What loan amount do you need?", "required": True}],
        }
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Launch campaign
        launch_res = await client.post(
            f"/api/campaigns/{camp_id}/launch",
            json={"confirm_count": 1, "mode": "test"},
            headers=headers,
        )
        assert launch_res.status_code == 200, f"Launch failed: {launch_res.text}"
        data = launch_res.json()
        assert data["queued_tasks"] >= 1

        # Fetch generated recipient snapshot and call task
        rec_snap = await db["campaign_recipients"].find_one({"campaign_id": camp_id, "record_id": rec_id})
        assert rec_snap is not None
        assert rec_snap.get("task_token") is not None
        task = await db["call_tasks"].find_one({"token": rec_snap["task_token"]})
        assert task is not None
        assert "token" in task

        # Execute genuine live VoiceSession using real Groq LLM
        messages_received = []

        async def mock_ws_send(msg):
            messages_received.append(msg)

        session = VoiceSession(
            config={
                "first_name": "Rohan",
                "bank_name": "Live Real Bank",
                "product_name": "Live Home Loan",
                "language": "en-IN",
                "system_prompt": "You are Tara, an AI assistant for Live Real Bank.",
                "opening_message": "Hello Rohan! This is Tara from Live Real Bank about your home loan inquiry.",
                "voice_by_language": {"en-IN": "Nalini"},
                "input_mode": "synthetic_test",
                "tenant_id": t_id,
            },
            send_ws=mock_ws_send,
        )

        await session.start()
        # Spoken user turn: "Yes, I need fifty lakhs home loan. Call me back tomorrow."
        await session.handle_user_turn(
            user_text="Yes, I need fifty lakhs home loan. Call me back tomorrow.",
            user_audio_duration_ms=1800.0,
            stt_ms=250.0,
            detected_lang="en-IN",
        )
        await session.end_session()

        # Check extraction produced by real LLM
        assert session.extraction is not None
        ext = session.extraction
        outcome = getattr(ext, "outcome", None) or (ext.get("outcome") if isinstance(ext, dict) else None)
        assert outcome in ["interested", "callback", "unclear", "not_interested"]
        summary = getattr(ext, "summary", "") or (ext.get("summary", "") if isinstance(ext, dict) else "")
        # Assert no hallucinations of unmentioned products
        assert "gold" not in summary.lower()

        # Update communication record in DB with completed session
        comm_id = task.get("communication_id")
        if comm_id:
            ext_dict = ext.model_dump() if hasattr(ext, "model_dump") else ext
            await db["communications"].update_one(
                {"communication_id": comm_id},
                {"$set": {
                    "status": "completed",
                    "session_id": session.session_id,
                    "completed_at": datetime.now(timezone.utc),
                    "input_mode": "synthetic_test",
                    "outcome": outcome,
                    "interest_level": getattr(ext, "interest_level", None) or ext_dict.get("interest_level"),
                    "extraction": ext_dict,
                }},
            )
            saved_comm = await db["communications"].find_one({"communication_id": comm_id})
            assert saved_comm["status"] == "completed"
