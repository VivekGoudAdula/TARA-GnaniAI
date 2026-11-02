"""
reset_demo.py - One-command demo reset for Test Bank (ten_testbank).
Resets Test Bank data, seeds compliant synthetic recipients, scores them,
and creates 1 ready campaign 'Personal Loan: High Intent' (~8 recipients across HI, TE, EN).
NEVER touches Other Bank (ten_otherbank). Prints login credentials and campaign link.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from motor.motor_asyncio import AsyncIOMotorClient
from app.auth import hash_password
from app.scoring.scorer import compute_fit_score, evaluate_eligibility
from scripts.generate_synthetic_data import generate_records

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "tara_gnani")
TENANT_ID = "ten_testbank"


async def reset_demo() -> None:
    print(f"[reset_demo] Connecting to {MONGO_URI} (db: {DB_NAME})...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    now = datetime.now(timezone.utc)

    # 1. Clean ONLY Test Bank collections (preserve ten_otherbank)
    target_collections = [
        "customers", "leads", "product_matches", "campaigns",
        "campaign_recipients", "communications", "call_tasks", "audit_log", "sessions"
    ]
    for coll in target_collections:
        res = await db[coll].delete_many({"tenant_id": TENANT_ID})
        print(f"  - Cleared {res.deleted_count} items from {coll}")

    # 2. Ensure Test Bank tenant & demo users exist
    await db["tenants"].update_one(
        {"tenant_id": TENANT_ID},
        {"$set": {"tenant_id": TENANT_ID, "name": "Test Bank", "calling_window_mode": "demo_override", "updated_at": now}},
        upsert=True,
    )
    await db["tenant_configs"].update_one(
        {"tenant_id": TENANT_ID},
        {"$set": {"tenant_id": TENANT_ID, "calling_window_mode": "demo_override"}},
        upsert=True,
    )

    demo_users = [
        {"user_id": "usr_testadmin", "tenant_id": TENANT_ID, "email": "admin@testbank.com", "full_name": "Test Bank Admin", "password_hash": hash_password("password123"), "role": "admin"},
        {"user_id": "usr_testanalyst", "tenant_id": TENANT_ID, "email": "analyst@testbank.com", "full_name": "Test Bank Analyst", "password_hash": hash_password("password123"), "role": "analyst"},
    ]
    for u in demo_users:
        await db["users"].update_one({"email": u["email"]}, {"$set": u}, upsert=True)

    # 3. Ensure Products exist for Test Bank
    prod = {
        "product_id": "prd_persloan",
        "tenant_id": TENANT_ID,
        "name": "Personal Loan",
        "category": "Lending",
        "description": "Instant personal financing up to ₹15 Lakhs.",
        "active": True,
        "eligibility_rules": {"min_income": 25000, "min_age": 21, "max_age": 60, "min_credit_score": 650, "employment_types": ["salaried", "self_employed"]},
        "default_prompt": "You are Tara, an AI assistant from Test Bank. Speak concisely, 1 question at a time. Disclose AI representation. Never promise guaranteed loan approvals or exact interest rates.",
        "default_opening_message": "Hello! This is Tara, an AI voice assistant calling from Test Bank regarding your pre-approved Personal Loan inquiry. Is this a good time to speak?",
        "created_at": now, "updated_at": now,
    }
    await db["products"].update_one({"tenant_id": TENANT_ID, "product_id": "prd_persloan"}, {"$set": prod}, upsert=True)

    # 4. Generate & insert synthetic customers
    raw_customers = generate_records(40, 2001, "TB_DEMO")
    for r in raw_customers:
        r["tenant_id"] = TENANT_ID
        r["record_type"] = "customers"
        r["consent"] = r.get("consent") == "true"
        r["dnd"] = r.get("dnd") == "true"
    # Guarantee 8 compliant recipients (consent=True, dnd=False, synthetic phone +9190000...)
    curated_recipients = [
        ("r_hi_1", "Aarav Sharma", "+919000010001", "hi-IN", "high", 55000, 740),
        ("r_hi_2", "Pooja Verma", "+919000010002", "hi-IN", "medium", 38000, 680),
        ("r_hi_3", "Vikram Malhotra", "+919000010003", "hi-IN", "high", 72000, 790),
        ("r_te_1", "Srinivas Rao", "+919000010004", "te-IN", "high", 65000, 760),
        ("r_te_2", "Kavitha Reddy", "+919000010005", "te-IN", "medium", 42000, 690),
        ("r_te_3", "Venkat Naidu", "+919000010006", "te-IN", "high", 58000, 735),
        ("r_en_1", "Rahul Deshmukh", "+919000010007", "en-IN", "high", 80000, 810),
        ("r_en_2", "Ananya Sen", "+919000010008", "en-IN", "medium", 45000, 710),
    ]

    for rid, name, phone, lang, tier, inc, score in curated_recipients:
        rec_doc = {
            "record_id": rid, "tenant_id": TENANT_ID, "full_name": name, "phone": phone,
            "preferred_language": lang, "consent": True, "dnd": False, "monthly_income": inc,
            "credit_score": score, "age": 32, "employment_type": "salaried", "created_at": now,
        }
        await db["customers"].insert_one(rec_doc)
        fit_score = 0.88 if tier == "high" else 0.65
        await db["product_matches"].insert_one({
            "tenant_id": TENANT_ID, "record_id": rid, "record_type": "customers",
            "product_id": "prd_persloan", "eligible": True, "fit_score": fit_score,
            "tier": tier, "feature_contributions": {"income": 0.4, "credit": 0.3},
        })

    for c in raw_customers:
        await db["customers"].insert_one(c)

    # 5. Create 1 ready campaign with the 8 recipients
    camp_id = f"camp_demo_{uuid.uuid4().hex[:6]}"
    campaign_doc = {
        "id": camp_id,
        "tenant_id": TENANT_ID,
        "name": "Personal Loan: High Intent",
        "product_id": "prd_persloan",
        "product_name": "Personal Loan",
        "audience_type": "customers",
        "status": "ready",
        "recipient_count": len(curated_recipients),
        "current_voice_config_version": 1,
        "pacing": {"concurrency": 1, "gap_seconds": 5},
        "retry_policy": {"max_attempts": 3, "retry_interval_minutes": 30},
        "created_at": now, "updated_at": now,
    }
    await db["campaigns"].insert_one(campaign_doc)

    snapshot_docs = []
    for rid, name, phone, lang, tier, _, _ in curated_recipients:
        fname = name.split()[0]
        snapshot_docs.append({
            "campaign_id": camp_id, "tenant_id": TENANT_ID, "record_id": rid,
            "first_name": fname, "preferred_language": lang, "eligible": True,
            "contactable": True, "tier": tier, "attempts": 0, "status": "pending",
        })
    await db["campaign_recipients"].insert_many(snapshot_docs)

    print("\n" + "=" * 60)
    print("DEMO RESET COMPLETE: TEST BANK IS DEMO-READY!")
    print("=" * 60)
    print("Credentials (Demo Login):")
    print("  Username: analyst@testbank.com (or admin@testbank.com)")
    print("  Password: password123")
    print("\nCampaign Ready for Launch:")
    print(f"  Name: Personal Loan: High Intent (ID: {camp_id})")
    print(f"  Recipients: 8 (Hindi, Telugu, English)")
    print("  Calling Window Mode: demo_override ON")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(reset_demo())
