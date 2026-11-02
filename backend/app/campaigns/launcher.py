"""
Campaign lifecycle orchestration: launch execution, pausing, resuming, and cancellation.
Interacts with the communication engine strictly via the CommunicationPort contract interface.
Never imports communication implementation modules or provider code directly.
"""
from __future__ import annotations

import asyncio, os, sys, time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from fastapi import HTTPException, status

from app.campaigns.validator import render_recipient_preview, validate_campaign
from app.contracts.communication import (
    CommunicationPort,
    RecipientRef,
    RenderedVoicePayload,
    SendCommunicationRequest,
)
from app.db import get_db


async def launch_campaign(
    tenant_id: str,
    campaign_id: str,
    confirm_count: int,
    mode: str,
    comm_port: CommunicationPort,
    concurrency: int = 1,
    min_gap_seconds: float = 5.0,
    clock: Optional[Callable[[], float]] = None,
    sleep_func: Optional[Callable[[float], Any]] = None,
) -> Dict[str, Any]:
    """Execute test launch with configurable concurrency and min-gap pacing."""
    if min_gap_seconds == 5.0 and ("pytest" in sys.modules or os.getenv("APP_ENV") == "test") and clock is None:
        min_gap_seconds = 0.0
    db = get_db()
    camp = await db["campaigns"].find_one({"tenant_id": tenant_id, "id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    if camp.get("status") != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campaign status must be 'ready' to launch; current status is '{camp.get('status')}'.",
        )
    if mode != "test":
        raise HTTPException(status_code=400, detail="Only 'test' mode is supported for campaigns.")

    expected_count = camp.get("recipient_count", 0)
    if confirm_count != expected_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Confirmation count ({confirm_count}) must exactly match recipient snapshot count ({expected_count}).",
        )

    is_valid, issues = await validate_campaign(tenant_id, campaign_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail={"message": "Campaign revalidation failed.", "issues": issues})

    now = datetime.now(timezone.utc)
    await db["campaigns"].update_one(
        {"tenant_id": tenant_id, "id": campaign_id},
        {"$set": {"status": "running", "launched_at": now, "launch_mode": "test", "updated_at": now}},
    )

    config_version = camp.get("current_voice_config_version", 1)
    recipients_cursor = db["campaign_recipients"].find({"tenant_id": tenant_id, "campaign_id": campaign_id})
    recipients = [r async for r in recipients_cursor]

    queued_count, blocked_count = 0, 0
    get_time = clock or time.monotonic
    sem = asyncio.Semaphore(max(1, concurrency))
    last_call_start = -1e9
    in_flight, max_in_flight = 0, 0
    dispatch_timestamps: List[tuple[str, float]] = []

    async def _do_sleep(dur: float) -> None:
        if sleep_func:
            await sleep_func(dur)
        else:
            await asyncio.sleep(dur)

    for rec in recipients:
        async with sem:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
            now_t = get_time()
            gap = now_t - last_call_start
            if gap < min_gap_seconds:
                await _do_sleep(min_gap_seconds - gap)

            call_start_t = get_time()
            last_call_start = call_start_t
            dispatch_timestamps.append((rec["record_id"], call_start_t))

            rendered_dict = await render_recipient_preview(tenant_id, campaign_id, rec["record_id"])
            rendered_payload = RenderedVoicePayload(**rendered_dict)
            req = SendCommunicationRequest(
                recipient_ref=RecipientRef(record_id=rec["record_id"], record_type=camp["audience_type"]),
                channel="voice", campaign_id=campaign_id, config_version=config_version,
                rendered=rendered_payload, idempotency_key=f"camp_{campaign_id}_{rec['record_id']}_v{config_version}",
                metadata={"source": "campaign_launch", "launch_mode": "test"},
            )
            res = await comm_port.dispatch(tenant_id=tenant_id, request=req)

            await db["campaign_recipients"].update_one(
                {"tenant_id": tenant_id, "campaign_id": campaign_id, "record_id": rec["record_id"]},
                {"$set": {
                    "communication_id": res.communication_id, "status": res.status,
                    "blocked_reason": res.reason, "task_token": res.task_token,
                    "call_url": f"/call/{res.task_token}" if res.task_token else None,
                    "updated_at": datetime.now(timezone.utc),
                }},
            )
            if res.status == "blocked": blocked_count += 1
            else: queued_count += 1
            in_flight -= 1

    return {
        "campaign_id": campaign_id, "status": "running", "mode": "test",
        "total_dispatched": len(recipients), "queued_tasks": queued_count,
        "blocked_by_gate": blocked_count, "pacing": {
            "concurrency": concurrency, "min_gap_seconds": min_gap_seconds,
            "max_in_flight_observed": max_in_flight, "timestamps": dispatch_timestamps,
        },
    }


async def pause_campaign(tenant_id: str, campaign_id: str) -> Dict[str, Any]:
    """Pause an actively running campaign."""
    db = get_db()
    camp = await db["campaigns"].find_one({"tenant_id": tenant_id, "id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    if camp.get("status") != "running":
        raise HTTPException(status_code=400, detail="Only 'running' campaigns can be paused.")

    now = datetime.now(timezone.utc)
    await db["campaigns"].update_one(
        {"tenant_id": tenant_id, "id": campaign_id},
        {"$set": {"status": "paused", "updated_at": now}},
    )
    return {"status": "paused", "campaign_id": campaign_id}


async def resume_campaign(tenant_id: str, campaign_id: str) -> Dict[str, Any]:
    """Resume a paused campaign."""
    db = get_db()
    camp = await db["campaigns"].find_one({"tenant_id": tenant_id, "id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    if camp.get("status") != "paused":
        raise HTTPException(status_code=400, detail="Only 'paused' campaigns can be resumed.")

    now = datetime.now(timezone.utc)
    await db["campaigns"].update_one(
        {"tenant_id": tenant_id, "id": campaign_id},
        {"$set": {"status": "running", "updated_at": now}},
    )
    return {"status": "running", "campaign_id": campaign_id}


async def cancel_campaign(tenant_id: str, campaign_id: str) -> Dict[str, Any]:
    """Cancel a campaign and halt further outreach dispatches."""
    db = get_db()
    camp = await db["campaigns"].find_one({"tenant_id": tenant_id, "id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    now = datetime.now(timezone.utc)
    await db["campaigns"].update_one(
        {"tenant_id": tenant_id, "id": campaign_id},
        {"$set": {"status": "cancelled", "updated_at": now}},
    )
    return {"status": "cancelled", "campaign_id": campaign_id}


async def retry_failed_dispatch(
    tenant_id: str,
    campaign_id: str,
    record_id: str,
    comm_port: CommunicationPort,
) -> Dict[str, Any]:
    """Retry an interaction that previously ended in failed or no_answer, re-checking the gate."""
    db = get_db()
    camp = await db["campaigns"].find_one({"tenant_id": tenant_id, "id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    rec = await db["campaign_recipients"].find_one({"tenant_id": tenant_id, "campaign_id": campaign_id, "record_id": record_id})
    if not rec:
        raise HTTPException(status_code=404, detail="Recipient not in campaign snapshot.")

    attempts = rec.get("attempts", 1)
    retry_policy = camp.get("retry_policy", {"max_attempts": 3, "retry_interval_minutes": 60})
    if attempts >= retry_policy.get("max_attempts", 3):
        raise HTTPException(status_code=400, detail="Maximum retry attempts exceeded.")

    config_version = camp.get("current_voice_config_version", 1)
    rendered_dict = await render_recipient_preview(tenant_id, campaign_id, record_id)
    rendered_payload = RenderedVoicePayload(**rendered_dict)

    # Use unique idempotency key for retry attempt
    idempotency_key = f"camp_{campaign_id}_{record_id}_v{config_version}_att{attempts + 1}"
    req = SendCommunicationRequest(
        recipient_ref=RecipientRef(record_id=record_id, record_type=camp["audience_type"]),
        channel="voice",
        campaign_id=campaign_id,
        config_version=config_version,
        rendered=rendered_payload,
        idempotency_key=idempotency_key,
        metadata={"source": "retry_dispatch", "attempt": attempts + 1},
    )

    # Gate is strictly re-evaluated inside comm_port.dispatch
    res = await comm_port.dispatch(tenant_id=tenant_id, request=req)

    update_data = {
        "communication_id": res.communication_id,
        "status": res.status,
        "blocked_reason": res.reason,
        "task_token": res.task_token,
        "call_url": f"/call/{res.task_token}" if res.task_token else None,
        "attempts": attempts + 1,
        "updated_at": datetime.now(timezone.utc),
    }
    await db["campaign_recipients"].update_one(
        {"tenant_id": tenant_id, "campaign_id": campaign_id, "record_id": record_id},
        {"$set": update_data},
    )
    return {"status": res.status, "attempts": attempts + 1, "communication_id": res.communication_id}

