"""
Authentication router: workspace signup, user login, and profile retrieval.
Enforces tenant association on all newly registered accounts.
"""
from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any, Dict, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from app.auth import (
    TokenUser,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

_login_rate_limits: Dict[str, List[float]] = {}


def check_login_rate_limit(key: str, max_attempts: int = 10, window_sec: float = 60.0) -> None:
    now = time.time()
    attempts = [t for t in _login_rate_limits.get(key, []) if now - t < window_sec]
    if len(attempts) >= max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please wait before retrying.",
        )
    attempts.append(now)
    _login_rate_limits[key] = attempts


class SignupRequest(BaseModel):
    workspace_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    tenant: Dict[str, Any]


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest) -> AuthResponse:
    """Register a new institution tenant and create its initial administrator account."""
    db = get_db()
    existing_user = await db["users"].find_one({"email": payload.email.lower()})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    tenant_id = f"ten_{uuid.uuid4().hex[:10]}"
    user_id = f"usr_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)

    tenant_doc = {
        "tenant_id": tenant_id,
        "name": payload.workspace_name.strip(),
        "created_at": now,
    }
    user_doc = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "email": payload.email.lower(),
        "full_name": payload.full_name.strip(),
        "password_hash": hash_password(payload.password),
        "role": "admin",
        "created_at": now,
    }

    await db["tenants"].insert_one(tenant_doc)
    await db["users"].insert_one(user_doc)

    token = create_access_token(user_id=user_id, tenant_id=tenant_id, email=payload.email.lower())
    return AuthResponse(
        access_token=token,
        user={"user_id": user_id, "email": payload.email.lower(), "full_name": payload.full_name},
        tenant={"tenant_id": tenant_id, "name": payload.workspace_name},
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest) -> AuthResponse:
    """Authenticate existing user credentials and return scoped JWT token."""
    check_login_rate_limit(payload.email.lower())
    db = get_db()
    user = await db["users"].find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    tenant = await db["tenants"].find_one({"tenant_id": user["tenant_id"]}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated workspace not found")

    token = create_access_token(
        user_id=user["user_id"],
        tenant_id=user["tenant_id"],
        email=user["email"],
        role=user.get("role", "admin"),
    )
    return AuthResponse(
        access_token=token,
        user={"user_id": user["user_id"], "email": user["email"], "full_name": user.get("full_name", "")},
        tenant=tenant,
    )


@router.get("/me")
async def get_current_profile(current_user: TokenUser = Depends(get_current_user)) -> Dict[str, Any]:
    """Return currently active authenticated profile and workspace."""
    db = get_db()
    tenant = await db["tenants"].find_one({"tenant_id": current_user.tenant_id}, {"_id": 0})
    user = await db["users"].find_one({"user_id": current_user.user_id}, {"_id": 0, "password_hash": 0})
    if not tenant or not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return {"user": user, "tenant": tenant}

