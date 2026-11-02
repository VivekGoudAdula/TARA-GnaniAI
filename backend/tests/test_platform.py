"""
Unit and integration tests for Auth, Tenant Isolation, CSV Ingestion, and Product Fit Scoring.
Uses isolated database context and verified JWT assertions.
"""
from __future__ import annotations

import io
import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import create_access_token, decode_access_token, hash_password, verify_password
from app.main import app
from app.scoring.scorer import compute_fit_score, evaluate_eligibility


# ─── 1. Auth & Password Tests ───────────────────────────────────────────────

def test_password_hashing():
    """Verify bcrypt hashes securely and validates accurately."""
    pwd = "secret_password_123"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_jwt_generation_and_decoding():
    """Verify JWT encodes claims and decodes user context properly."""
    token = create_access_token("u_123", "ten_abc", "user@test.com")
    decoded = decode_access_token(token)
    assert decoded.user_id == "u_123"
    assert decoded.tenant_id == "ten_abc"
    assert decoded.email == "user@test.com"


# ─── 2. Tenant Isolation & API Security Tests ────────────────────────────────

@pytest.mark.asyncio
async def test_tenant_isolation_cross_tenant_access_returns_404():
    """Verify user from Tenant A receives 404 accessing Tenant B resources."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token_a = create_access_token("usr_a", "ten_a", "a@test.com")
        headers_a = {"Authorization": f"Bearer {token_a}"}

        token_b = create_access_token("usr_b", "ten_b", "b@test.com")
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Tenant A creates product
        prod_payload = {
            "name": "Tenant A Exclusive Loan",
            "category": "Lending",
            "active": True,
            "eligibility_rules": {"min_income": 20000, "min_age": 21, "max_age": 60, "min_credit_score": 600, "employment_types": ["salaried"]},
        }
        res_create = await ac.post("/api/products", json=prod_payload, headers=headers_a)
        assert res_create.status_code == 201
        prod_id = res_create.json()["product_id"]

        # Tenant A can read it
        res_get_a = await ac.get(f"/api/products/{prod_id}", headers=headers_a)
        assert res_get_a.status_code == 200

        # Tenant B receives 404 (NOT 403 or 200)
        res_get_b = await ac.get(f"/api/products/{prod_id}", headers=headers_b)
        assert res_get_b.status_code == 404

        # Tenant B cannot delete it (returns 404)
        res_del_b = await ac.delete(f"/api/products/{prod_id}", headers=headers_b)
        assert res_del_b.status_code == 404


@pytest.mark.asyncio
async def test_auth_signup_and_login_flow():
    """Verify signup creates workspace and login issues valid bearer token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        email = f"lead_admin_{id(ac)}@newbank.com"
        signup_res = await ac.post("/api/auth/signup", json={
            "workspace_name": "New Horizons Bank",
            "email": email,
            "password": "PasswordSecure99",
            "full_name": "Chief Risk Officer",
        })
        assert signup_res.status_code == 201
        data = signup_res.json()
        assert "access_token" in data
        assert data["tenant"]["name"] == "New Horizons Bank"

        # Login with correct credentials
        login_res = await ac.post("/api/auth/login", json={
            "email": email,
            "password": "PasswordSecure99",
        })
        assert login_res.status_code == 200

        # Login with bad password fails with 401
        bad_login = await ac.post("/api/auth/login", json={
            "email": email,
            "password": "wrong_password",
        })
        assert bad_login.status_code == 401


# ─── 3. CSV Import & Synthetic Data Validation Tests ────────────────────────

@pytest.mark.asyncio
async def test_csv_import_safety_rejects_non_synthetic_phone():
    """Verify non-synthetic phone numbers (+91 98765...) are rejected by safety filter."""
    import uuid
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unique_ten = f"ten_imp_{uuid.uuid4().hex[:8]}"
        token = create_access_token("usr_imp", unique_ten, "imp@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        # CSV containing 1 synthetic and 1 real phone number
        csv_content = (
            "external_ref,full_name,phone,email,age,monthly_income_inr,employment_type,credit_score,city,preferred_language,consent,dnd\n"
            "REF1,Good Synthetic,+919000012345,good@test.com,30,45000,salaried,720,Mumbai,en-IN,true,false\n"
            "REF2,Real Phone,+919820123456,bad@test.com,35,60000,salaried,750,Delhi,hi-IN,true,false\n"
        )
        files = {"file": ("leads.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        data = {"attestation": "true"}

        res = await ac.post("/api/import/leads", files=files, data=data, headers=headers)
        assert res.status_code == 200
        report = res.json()
        assert report["rows_accepted"] == 1
        assert report["rows_rejected"] == 1
        assert "Rejected non-synthetic phone" in report["rejections"][0]["reason"]


@pytest.mark.asyncio
async def test_csv_import_requires_consent_attestation():
    """Verify uploading without consent attestation returns 400 Bad Request."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_access_token("usr_imp", "ten_imp", "imp@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": ("test.csv", io.BytesIO(b"phone\n+919000011111"), "text/csv")}
        data = {"attestation": "false"}

        res = await ac.post("/api/import/leads", files=files, data=data, headers=headers)
        assert res.status_code == 400


# ─── 4. Scoring & Explainability Engine Tests ────────────────────────────────

def test_eligibility_evaluation_rules():
    """Verify deterministic product rule verification."""
    product = {
        "eligibility_rules": {
            "min_income": 30000,
            "min_age": 21,
            "max_age": 60,
            "min_credit_score": 650,
            "employment_types": ["salaried"],
        }
    }
    # Pass
    ok_record = {"monthly_income_inr": 40000, "age": 30, "credit_score": 700, "employment_type": "salaried"}
    is_ok, failed = evaluate_eligibility(ok_record, product)
    assert is_ok is True
    assert len(failed) == 0

    # Fail multiple criteria
    bad_record = {"monthly_income_inr": 20000, "age": 19, "credit_score": 600, "employment_type": "self_employed"}
    is_bad, failed_bad = evaluate_eligibility(bad_record, product)
    assert is_bad is False
    assert len(failed_bad) >= 3


def test_scoring_bands_and_explanations():
    """Verify fit score calculation, band assignment, and exact plain-English explanations."""
    product = {}
    high_rec = {"monthly_income_inr": 120000, "credit_score": 790, "age": 34, "employment_type": "salaried", "consent": True}
    score, band, explanations = compute_fit_score(high_rec, product)
    assert score >= 70
    assert band == "High"
    assert len(explanations) == 3
    assert any("income" in exp.lower() for exp in explanations)

    low_rec = {"monthly_income_inr": 18000, "credit_score": 500, "age": 62, "employment_type": "self_employed", "consent": False}
    low_score, low_band, low_exps = compute_fit_score(low_rec, product)
    assert low_score < 70
    assert len(low_exps) == 3
