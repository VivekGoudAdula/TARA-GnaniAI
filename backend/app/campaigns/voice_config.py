"""
Voice configuration management and versioning service for campaigns.
Ensures append-only versioning and audit trails.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import HTTPException
from app.campaigns.models import VoiceConfigData
from app.db import get_db


def default_voice_config_dict() -> Dict[str, Any]:
    """Generate compliant initial voice configuration for a new campaign."""
    return {
        "default_language": "en-IN",
        "voice_by_language": {"en-IN": "Nalini", "hi-IN": "Nalini", "te-IN": "Suhana"},
        "tone": "polite, helpful, professional",
        "system_prompt": "You are an AI representative calling on behalf of {{bank_name}} regarding {{product_name}} for {{first_name}}.",
        "opening_message": "Hello {{first_name}}, I am an automated AI assistant calling from {{bank_name}} regarding {{product_name}}. Do you have a moment?",
        "conversation_objective": "Explain product value and determine if the customer is interested or requests a callback.",
        "info_to_collect": [{"field": "interest", "question": "Are you interested in exploring this?", "required": True}],
        "success_condition": "Customer expresses interest or agrees to a callback.",
        "fallback_behaviour": "Politely acknowledge and ask if executive can call later.",
        "retry_policy": {"max_attempts": 3, "retry_interval_minutes": 60},
        "max_turns": 8,
        "closing_message": "Thank you for your time, {{first_name}}. Have a wonderful day!",
    }


async def fetch_campaign_voice_config(tenant_id: str, campaign_id: str) -> Dict[str, Any]:
    """Fetch current active voice config for campaign."""
    db = get_db()
    camp = await db["campaigns"].find_one({"tenant_id": tenant_id, "id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    version = camp.get("current_voice_config_version", 1)
    cfg_doc = await db["campaign_voice_configs"].find_one(
        {"tenant_id": tenant_id, "campaign_id": campaign_id, "version": version}, {"_id": 0}
    )
    if not cfg_doc:
        raise HTTPException(status_code=404, detail="Voice config not found.")
    return cfg_doc


async def create_voice_config_version(
    tenant_id: str, campaign_id: str, config: VoiceConfigData
) -> Dict[str, Any]:
    """Create a new append-only version (n+1) for campaign voice configuration."""
    db = get_db()
    camp = await db["campaigns"].find_one({"tenant_id": tenant_id, "id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    next_version = camp.get("current_voice_config_version", 0) + 1
    now = datetime.now(timezone.utc)
    new_doc = {
        "campaign_id": campaign_id,
        "tenant_id": tenant_id,
        "version": next_version,
        "created_at": now,
        "config": config.model_dump(),
    }
    await db["campaign_voice_configs"].insert_one(new_doc)
    await db["campaigns"].update_one(
        {"tenant_id": tenant_id, "id": campaign_id},
        {"$set": {"current_voice_config_version": next_version, "updated_at": now}},
    )
    new_doc.pop("_id", None)
    return new_doc


async def fetch_voice_config_history(tenant_id: str, campaign_id: str) -> List[Dict[str, Any]]:
    """List historical voice configuration versions for auditability."""
    db = get_db()
    cursor = db["campaign_voice_configs"].find(
        {"tenant_id": tenant_id, "campaign_id": campaign_id}, {"_id": 0}
    ).sort("version", -1)
    return [v async for v in cursor]
