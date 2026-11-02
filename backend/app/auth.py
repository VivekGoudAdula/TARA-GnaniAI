"""
Authentication, password hashing, and tenant-scoped JWT token handling.
Derives tenant_id strictly from JWT token claims to enforce tenant isolation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from pydantic import BaseModel

security = HTTPBearer(auto_error=False)


def get_jwt_secret() -> str:
    """Return JWT secret key from environment; requires explicit env var in production."""
    secret = os.getenv("JWT_SECRET")
    is_dev = os.getenv("DEV_ENDPOINTS", "true").lower() == "true"
    if not is_dev and (not secret or secret.startswith("tara_jwt_secret_key")):
        raise RuntimeError("Production mode requires an explicit JWT_SECRET set in environment.")
    return secret or "tara_jwt_secret_key_gnani_internship_challenge_2026_super_secure"


def get_jwt_algorithm() -> str:
    """Return JWT signing algorithm from environment."""
    return os.getenv("JWT_ALGORITHM", "HS256")


class TokenUser(BaseModel):
    """Authenticated user context derived solely from verified JWT."""

    user_id: str
    tenant_id: str
    email: str
    role: str = "admin"


def hash_password(password: str) -> str:
    """Hash plaintext password with bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(
    user_id: str, tenant_id: str, email: str, role: str = "admin", expires_delta: Optional[timedelta] = None
) -> str:
    """Create signed JWT containing user identity and tenant scope."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "email": email,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=get_jwt_algorithm())


def decode_access_token(token: str) -> TokenUser:
    """Decode and validate access token, returning authenticated TokenUser."""
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[get_jwt_algorithm()])
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        email = payload.get("email", "")
        role = payload.get("role", "admin")
        if not user_id or not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims: missing sub or tenant_id",
            )
        return TokenUser(user_id=user_id, tenant_id=tenant_id, email=email, role=role)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired credentials: {str(exc)}",
        ) from exc


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> TokenUser:
    """FastAPI dependency: extracts and verifies JWT bearer token."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer header",
        )
    return decode_access_token(credentials.credentials)
