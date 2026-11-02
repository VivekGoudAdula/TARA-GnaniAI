"""
Database seeder for multi-tenant banking data, product catalogues, and scored leads.
Creates 'Test Bank' and 'Other Bank' workspaces with synthetic customers, leads, and products.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from motor.motor_asyncio import AsyncIOMotorClient
from app.auth import hash_password
from app.scoring.scorer import compute_fit_score, evaluate_eligibility
from scripts.generate_synthetic_data import generate_records

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "tara_gnani")


async def seed():
    print(f"Connecting to MongoDB at {MONGO_URI}...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    now = datetime.now(timezone.utc)

    # 1. Clear existing collections
    for c in ["tenants", "users", "products", "customers", "leads", "product_matches"]:
        await db[c].delete_many({})

    print("Cleared existing tenant collections.")

    # 2. Create Tenants
    t_test = {"tenant_id": "ten_testbank", "name": "Test Bank", "created_at": now}
    t_other = {"tenant_id": "ten_otherbank", "name": "Other Bank", "created_at": now}
    await db["tenants"].insert_many([t_test, t_other])

    # 3. Create Users
    u_test = {
        "user_id": "usr_testadmin",
        "tenant_id": "ten_testbank",
        "email": "admin@testbank.com",
        "full_name": "Test Bank Admin",
        "password_hash": hash_password("password123"),
        "role": "admin",
        "created_at": now,
    }
    u_other = {
        "user_id": "usr_otheradmin",
        "tenant_id": "ten_otherbank",
        "email": "admin@otherbank.com",
        "full_name": "Other Bank Admin",
        "password_hash": hash_password("password123"),
        "role": "admin",
        "created_at": now,
    }
    await db["users"].insert_many([u_test, u_other])
    print("Created tenants 'Test Bank' and 'Other Bank' with admin credentials.")

    # 4. Create 4 Products for Test Bank
    test_products = [
        {
            "product_id": "prd_persloan",
            "tenant_id": "ten_testbank",
            "name": "Personal Loan",
            "category": "Lending",
            "description": "Instant collateral-free personal financing up to ₹15 Lakhs.",
            "active": True,
            "eligibility_rules": {
                "min_income": 25000, "min_age": 21, "max_age": 60,
                "min_credit_score": 650, "employment_types": ["salaried", "self_employed"]
            },
            "default_prompt": "You are Tara, calling regarding an instant personal loan.",
            "default_opening_message": "Hello, I am calling from Test Bank regarding your pre-approved Personal Loan.",
            "created_at": now, "updated_at": now
        },
        {
            "product_id": "prd_creditcard",
            "tenant_id": "ten_testbank",
            "name": "Platinum Credit Card",
            "category": "Cards",
            "description": "Zero annual fee credit card with 5% rewards on all retail spends.",
            "active": True,
            "eligibility_rules": {
                "min_income": 35000, "min_age": 21, "max_age": 65,
                "min_credit_score": 700, "employment_types": ["salaried", "self_employed"]
            },
            "default_prompt": "You are Tara, sharing Platinum Credit Card benefits.",
            "default_opening_message": "Hello, Test Bank has pre-approved you for our Platinum Credit Card.",
            "created_at": now, "updated_at": now
        },
        {
            "product_id": "prd_homeloan",
            "tenant_id": "ten_testbank",
            "name": "Home Loan",
            "category": "Mortgage",
            "description": "Attractive home financing starting at 8.4% per annum with 30-year tenure.",
            "active": True,
            "eligibility_rules": {
                "min_income": 50000, "min_age": 25, "max_age": 65,
                "min_credit_score": 720, "employment_types": ["salaried"]
            },
            "default_prompt": "You are Tara, speaking about low-interest home loans.",
            "default_opening_message": "Hello, Test Bank offers special subsidized rates for home loan applicants.",
            "created_at": now, "updated_at": now
        },
        {
            "product_id": "prd_savings",
            "tenant_id": "ten_testbank",
            "name": "High-Yield Savings Account",
            "category": "Deposits",
            "description": "Digital savings account yielding up to 7% annual interest on daily balance.",
            "active": True,
            "eligibility_rules": {
                "min_income": 10000, "min_age": 18, "max_age": 75,
                "min_credit_score": 300, "employment_types": ["salaried", "self_employed"]
            },
            "default_prompt": "You are Tara, introducing Test Bank High-Yield Savings.",
            "default_opening_message": "Hello, I am Tara from Test Bank with an update on premium savings interest rates.",
            "created_at": now, "updated_at": now
        },
    ]

    # Products for Other Bank
    other_products = [
        {
            "product_id": "prd_other_veh",
            "tenant_id": "ten_otherbank",
            "name": "Vehicle Loan",
            "category": "Auto",
            "description": "Commercial and personal car loans.",
            "active": True,
            "eligibility_rules": {"min_income": 30000, "min_age": 21, "max_age": 65, "min_credit_score": 600, "employment_types": ["salaried"]},
            "default_prompt": "You are Tara.",
            "default_opening_message": "Hello from Other Bank.",
            "created_at": now, "updated_at": now
        }
    ]

    await db["products"].insert_many(test_products + other_products)
    print("Created 4 products for Test Bank and 1 product for Other Bank.")

    # 5. Populate synthetic records for Test Bank (200 customers, 200 leads)
    cust_raw = generate_records(200, 1001, "TB_CUST")
    cust_docs = [
        {
            "record_id": f"rec_c_{i}",
            "tenant_id": "ten_testbank",
            "record_type": "customers",
            **r,
            "consent": r["consent"] == "true",
            "dnd": r["dnd"] == "true",
            "contactable": r["consent"] == "true" and r["dnd"] != "true",
            "created_at": now,
        }
        for i, r in enumerate(cust_raw)
    ]
    await db["customers"].insert_many(cust_docs)

    lead_raw = generate_records(200, 1201, "TB_LEAD")
    lead_docs = [
        {
            "record_id": f"rec_l_{i}",
            "tenant_id": "ten_testbank",
            "record_type": "leads",
            **r,
            "consent": r["consent"] == "true",
            "dnd": r["dnd"] == "true",
            "contactable": r["consent"] == "true" and r["dnd"] != "true",
            "created_at": now,
        }
        for i, r in enumerate(lead_raw)
    ]
    await db["leads"].insert_many(lead_docs)

    # Populate 10 customers for Other Bank to test tenant isolation
    other_raw = generate_records(10, 1501, "OB_CUST")
    other_docs = [
        {
            "record_id": f"rec_ob_{i}",
            "tenant_id": "ten_otherbank",
            "record_type": "customers",
            **r,
            "consent": True, "dnd": False, "contactable": True, "created_at": now
        }
        for i, r in enumerate(other_raw)
    ]
    await db["customers"].insert_many(other_docs)

    # 6. Score all records for Test Bank across all 4 products
    matches = []
    for rec in cust_docs + lead_docs:
        for p in test_products:
            eligible, failed = evaluate_eligibility(rec, p)
            fit_score, band, explanations = compute_fit_score(rec, p)
            matches.append({
                "match_id": f"mch_{uuid.uuid4().hex[:10]}",
                "tenant_id": "ten_testbank",
                "record_type": rec["record_type"],
                "record_id": rec["record_id"],
                "product_id": p["product_id"],
                "product_name": p["name"],
                "fit_score": fit_score,
                "band": band,
                "eligible": eligible,
                "failed_rules": failed,
                "explanation": explanations,
                "scored_at": now,
                "model_version": "1.0.0",
            })

    await db["product_matches"].insert_many(matches)
    print(f"Generated and scored {len(matches)} product matches for Test Bank.")
    client.close()
    print("Seed complete successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
