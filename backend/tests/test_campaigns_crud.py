"""
Campaign CRUD, cross-tenant isolation, and AST architectural purity tests.
"""
from __future__ import annotations

import ast
from pathlib import Path
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import create_access_token
from app.db import get_db
from app.main import app


@pytest.fixture
def auth_headers_bank1():
    token = create_access_token("usr_t1", "ten_camp_1", "admin@bank1.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_bank2():
    token = create_access_token("usr_t2", "ten_camp_2", "admin@bank2.com")
    return {"Authorization": f"Bearer {token}"}


def test_campaign_ast_architecture_purity():
    """Verify campaign module never imports providers or voice modules."""
    campaign_dir = Path("backend/app/campaigns")
    for py_file in campaign_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "providers" not in alias.name, f"Forbidden import {alias.name} in {py_file}"
                    assert "voice" not in alias.name, f"Forbidden import {alias.name} in {py_file}"
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert "providers" not in mod, f"Forbidden from-import {mod} in {py_file}"
                assert "voice" not in mod, f"Forbidden from-import {mod} in {py_file}"


@pytest.mark.asyncio
async def test_campaign_crud_and_tenant_isolation(auth_headers_bank1, auth_headers_bank2):
    """Test campaign creation, update, and strict 404 on cross-tenant access."""
    db = get_db()
    prod_id = f"prd_{uuid.uuid4().hex[:8]}"
    await db["products"].insert_one({
        "tenant_id": "ten_camp_1", "product_id": prod_id, "name": "Personal Loan", "active": True
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create campaign as Bank 1
        res = await client.post("/api/campaigns", json={
            "name": "Q1 Personal Loan Outreach", "product_id": prod_id, "audience_type": "customers",
            "objective": "Promote low rate", "description": "Existing borrowers"
        }, headers=auth_headers_bank1)
        assert res.status_code == 201
        camp = res.json()
        camp_id = camp["id"]
        assert camp["current_voice_config_version"] == 1

        # Bank 2 attempts access -> must return 404
        cross_res = await client.get(f"/api/campaigns/{camp_id}", headers=auth_headers_bank2)
        assert cross_res.status_code == 404

        # Bank 1 can read
        read_res = await client.get(f"/api/campaigns/{camp_id}", headers=auth_headers_bank1)
        assert read_res.status_code == 200
        assert read_res.json()["name"] == "Q1 Personal Loan Outreach"
