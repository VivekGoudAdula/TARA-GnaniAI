"""
Communication API router: outbound dispatch, communication queries,
and public tester session tokens.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import TokenUser, get_current_user
from app.communication.dispatcher import CommunicationDispatcher
from app.communication.provider import GnaniWebVoiceProvider
from app.contracts.communication import CommunicationResponse, SendCommunicationRequest
from app.db import get_db

router = APIRouter(tags=["communication"])
dispatcher = CommunicationDispatcher(provider=GnaniWebVoiceProvider())


@router.post("/api/communication/send", response_model=CommunicationResponse)
async def send_communication(
    req: SendCommunicationRequest,
    current_user: TokenUser = Depends(get_current_user),
) -> CommunicationResponse:
    """Dispatch an outbound communication task governed by compliance rules."""
    return await dispatcher.dispatch(tenant_id=current_user.tenant_id, request=req)


@router.get("/api/communication/{communication_id}")
async def get_communication(
    communication_id: str,
    current_user: TokenUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve communication record with tenant isolation; returns 404 if absent."""
    db = get_db()
    comm = await db["communications"].find_one(
        {"tenant_id": current_user.tenant_id, "communication_id": communication_id},
        {"_id": 0},
    )
    if not comm:
        raise HTTPException(status_code=404, detail="Communication record not found.")
    return comm


@router.get("/api/communication")
async def list_communications(
    campaign_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: TokenUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """List paginated communications for verified tenant with optional filters."""
    db = get_db()
    query: Dict[str, Any] = {"tenant_id": current_user.tenant_id}
    if campaign_id:
        query["campaign_id"] = campaign_id
    if status_filter:
        query["status"] = status_filter

    total = await db["communications"].count_documents(query)
    cursor = db["communications"].find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    items = [c async for c in cursor]
    return {"total": total, "items": items}


# ─── Public Tester Session Endpoints (No JWT Required) ───────────────────────

@router.get("/api/call-task/{token}")
async def get_call_task(token: str) -> Dict[str, Any]:
    """Retrieve public rendered voice payload for a single-use tester token."""
    db = get_db()
    task = await db["call_tasks"].find_one({"token": token}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Call task not found.")

    now = datetime.now(timezone.utc)
    # Check expiry
    expires_at = task.get("expires_at")
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and now > expires_at:
        raise HTTPException(status_code=410, detail="Call token has expired.")

    # Check if already used
    if task.get("used", False):
        raise HTTPException(status_code=410, detail="Call token has already been used.")

    # Sanitize: Return ONLY safe rendered voice parameters (no phone, income, score)
    rendered = task.get("rendered", {})
    return {
        "token": task["token"],
        "first_name": task.get("recipient_first_name", "Customer"),
        "bank_name": task.get("bank_name", "Bank"),
        "product_name": task.get("product_name", "Product"),
        "language": task.get("language", "en-IN"),
        "system_prompt": rendered.get("system_prompt", ""),
        "opening_message": rendered.get("opening_message", ""),
        "info_to_collect": rendered.get("info_to_collect", []),
        "max_turns": rendered.get("max_turns", 8),
        "voice": rendered.get("voice"),
        "status": task.get("status", "queued"),
    }


@router.post("/api/call-task/{token}/start")
async def start_call_task(token: str) -> Dict[str, Any]:
    """Mark call task as in-progress upon session connection."""
    db = get_db()
    task = await db["call_tasks"].find_one({"token": token})
    if not task:
        raise HTTPException(status_code=404, detail="Call task not found.")
    if task.get("used", False):
        raise HTTPException(status_code=410, detail="Call token already used.")

    now = datetime.now(timezone.utc)
    await db["call_tasks"].update_one(
        {"token": token},
        {"$set": {"status": "in_progress", "started_at": now}}
    )
    if task.get("communication_id"):
        await db["communications"].update_one(
            {"communication_id": task["communication_id"]},
            {"$set": {"status": "in_progress", "started_at": now}}
        )
    return {"status": "in_progress"}


@router.post("/api/call-task/{token}/complete")
async def complete_call_task(token: str, outcome_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Record call outcome, transcript, and extraction from web voice session."""
    db = get_db()
    task = await db["call_tasks"].find_one({"token": token})
    if not task:
        raise HTTPException(status_code=404, detail="Call task not found.")

    now = datetime.now(timezone.utc)
    await db["call_tasks"].update_one(
        {"token": token},
        {"$set": {"status": "completed", "used": True, "completed_at": now}}
    )

    comm_id = task.get("communication_id")
    if comm_id:
        provider = GnaniWebVoiceProvider()
        await provider.complete_session_outcome(comm_id, outcome_payload)

    return {"status": "completed"}
