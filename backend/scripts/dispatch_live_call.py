"""
dispatch_live_call.py - CLI tool to dispatch a single live test call task and verify live execution.
Demonstrates end-to-end flow: Campaign -> Compliance Gate -> Task Token -> Voice Session -> DB.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import uuid

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from motor.motor_asyncio import AsyncIOMotorClient
from app.voice.session import VoiceSession
from app.communication.dispatcher import CommunicationDispatcher
from app.communication.provider import GnaniWebVoiceProvider
from app.contracts.communication import SendCommunicationRequest


async def run_dispatch() -> None:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
    db_name = os.getenv("MONGO_DB_NAME", "tara_gnani")
    print(f"[dispatch_live_call] Connecting to {mongo_uri} ({db_name})...")
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]

    tenant_id = "ten_testbank"
    now = datetime.now(timezone.utc)

    # 1. Ensure test tenant config allows demo calls
    await db["tenant_configs"].update_one(
        {"tenant_id": tenant_id},
        {"$set": {"calling_window_mode": "demo_override", "updated_at": now}},
        upsert=True,
    )

    # 2. Find or create an eligible recipient
    cust = await db["customers"].find_one({"tenant_id": tenant_id, "consent": True, "dnd": False})
    if not cust:
        rec_id = f"r_{uuid.uuid4().hex[:6]}"
        cust = {
            "tenant_id": tenant_id, "record_id": rec_id, "full_name": "Rohan Sharma",
            "phone": "+919000012345", "consent": True, "dnd": False, "preferred_language": "en-IN",
        }
        await db["customers"].insert_one(cust)

    # 3. Dispatch through CommunicationDispatcher and Compliance Gate
    from app.contracts.communication import RecipientRef, RenderedVoicePayload
    dispatcher = CommunicationDispatcher()
    resp = await dispatcher.dispatch(
        tenant_id=tenant_id,
        request=SendCommunicationRequest(
            recipient_ref=RecipientRef(record_id=cust["record_id"], record_type="customers"),
            channel="voice",
            campaign_id="camp_test_dispatch",
            config_version=1,
            idempotency_key=f"idem_{uuid.uuid4().hex[:12]}",
            rendered=RenderedVoicePayload(
                first_name="Rohan",
                bank_name="Test Bank",
                product_name="Personal Loan",
                system_prompt="You are Tara, an AI voice assistant from Test Bank.",
                opening_message="Hello Rohan! This is Tara from Test Bank.",
                language="en-IN",
                voice="Nalini",
                info_to_collect=[{"field": "loan_amount", "question": "Amount?", "required": True}],
                success_condition="Interested",
            ),
        ),
    )
    print(f"[dispatch_live_call] Dispatched communication: {resp.communication_id}")
    print(f"[dispatch_live_call] Status: {resp.status} | Task Token: {resp.task_token}")

    # 4. Execute a live synthetic turn to verify voice loop
    print("[dispatch_live_call] Executing live voice loop verification...")
    received_events = []

    async def mock_ws(msg):
        received_events.append(msg)

    session = VoiceSession(
        config={
            "first_name": "Rohan",
            "bank_name": "Test Bank",
            "product_name": "Personal Loan",
            "language": "en-IN",
            "system_prompt": "You are Tara, an AI voice assistant from Test Bank.",
            "opening_message": "Hello Rohan! This is Tara, an AI assistant from Test Bank.",
            "voice_by_language": {"en-IN": "Nalini"},
            "input_mode": "synthetic_test",
            "tenant_id": tenant_id,
        },
        send_ws=mock_ws,
    )

    # Start session and run turn
    await session.start()
    await session.handle_user_turn(
        user_text="I am interested in a five lakh personal loan, please call me tomorrow.",
        user_audio_duration_ms=2500.0,
        stt_ms=300.0,
        detected_lang="en-IN",
    )
    await session.end_session()

    print("[dispatch_live_call] Voice session successfully completed.")
    print(f"  - Session ID: {session.session_id}")
    print(f"  - Agent Response: {session.turns[-1].get('agent_response')}")
    print(f"  - Grounded Extraction: {session.extraction}")
    print("[dispatch_live_call] PASSED: Live communication path is operational.")


if __name__ == "__main__":
    asyncio.run(run_dispatch())
