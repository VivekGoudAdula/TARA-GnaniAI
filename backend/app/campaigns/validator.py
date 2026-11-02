"""
Validation and preview rendering engine for campaigns.
Ensures campaign completeness, regulatory AI disclosures, template variable safety,
and produces sanitized rendered voice payloads.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from app.campaigns.models import ALLOWED_TEMPLATE_VARS, TEMPLATE_VAR_REGEX
from app.contracts.communication import RenderedVoicePayload
from app.db import get_db

AI_DISCLOSURE_PATTERNS = [
    re.compile(r"\b(ai|artificial intelligence|automated|virtual assistant|automated assistant)\b", re.IGNORECASE),
]

COMPLIANT_DISCLOSURE_PREFIX = (
    "Hello {{first_name}}, I am an automated AI assistant calling from {{bank_name}}. "
)


def has_ai_disclosure(text: str) -> bool:
    """Check if text contains explicit automated/AI assistant disclosure."""
    return any(p.search(text) for p in AI_DISCLOSURE_PATTERNS)


def render_template(text: str, context: Dict[str, str]) -> str:
    """Replace allowed variables with actual context values."""
    rendered = text
    for key, val in context.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", val)
    return rendered


async def validate_campaign(tenant_id: str, campaign_id: str) -> Tuple[bool, List[str]]:
    """
    Validate whether a campaign meets all prerequisites to transition to 'ready' status.
    Returns (is_valid, list_of_issues).
    """
    db = get_db()
    issues: List[str] = []

    # 1. Verify campaign existence
    camp = await db["campaigns"].find_one({"tenant_id": tenant_id, "id": campaign_id})
    if not camp:
        return False, ["Campaign not found or does not belong to this tenant."]

    # 2. Check product existence and active state
    prod = await db["products"].find_one({"tenant_id": tenant_id, "product_id": camp["product_id"]})
    if not prod:
        issues.append(f"Linked product '{camp['product_id']}' was not found.")
    elif not prod.get("active", False):
        issues.append(f"Linked product '{prod.get('name')}' is deactivated. Activate it first.")

    # 3. Check recipient snapshot count >= 1
    recipient_count = await db["campaign_recipients"].count_documents({
        "tenant_id": tenant_id, "campaign_id": campaign_id
    })
    if recipient_count == 0:
        issues.append("Audience snapshot has 0 recipients. Build audience before launching.")

    # 4. Check voice configuration
    version = camp.get("current_voice_config_version", 1)
    vconfig_doc = await db["campaign_voice_configs"].find_one({
        "tenant_id": tenant_id, "campaign_id": campaign_id, "version": version
    })
    if not vconfig_doc or "config" not in vconfig_doc:
        issues.append(f"Voice configuration version {version} not found.")
    else:
        cfg = vconfig_doc["config"]
        # Required non-empty string fields
        for field_name in ["system_prompt", "opening_message", "conversation_objective", "success_condition"]:
            val = (cfg.get(field_name) or "").strip()
            if not val:
                issues.append(f"Voice config '{field_name}' cannot be empty.")

        # Check info to collect
        info_items = cfg.get("info_to_collect") or []
        if len(info_items) == 0:
            issues.append("Voice config must have at least one field in 'info_to_collect'.")

        # Check template variables in text fields
        for field_name in ["system_prompt", "opening_message", "closing_message"]:
            text_val = cfg.get(field_name) or ""
            found = set(TEMPLATE_VAR_REGEX.findall(text_val))
            unknown = found - ALLOWED_TEMPLATE_VARS
            if unknown:
                issues.append(
                    f"Forbidden template variables {sorted(unknown)} in '{field_name}'. Allowed: {sorted(ALLOWED_TEMPLATE_VARS)}"
                )

        # AI disclosure check: if missing, auto-prepend compliant notice
        opening_msg = cfg.get("opening_message") or ""
        if opening_msg and not has_ai_disclosure(opening_msg):
            updated_opening = COMPLIANT_DISCLOSURE_PREFIX + opening_msg
            cfg["opening_message"] = updated_opening
            await db["campaign_voice_configs"].update_one(
                {"_id": vconfig_doc["_id"]},
                {"$set": {"config.opening_message": updated_opening}}
            )

    return len(issues) == 0, issues


async def render_recipient_preview(
    tenant_id: str,
    campaign_id: str,
    record_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Render system prompt and opening message for a sample or specific recipient in campaign snapshot.
    Returns sanitized RenderedVoicePayload dictionary without sensitive contact or financial fields.
    """
    db = get_db()
    camp = await db["campaigns"].find_one({"tenant_id": tenant_id, "id": campaign_id})
    if not camp:
        raise ValueError("Campaign not found.")

    prod = await db["products"].find_one({"tenant_id": tenant_id, "product_id": camp["product_id"]})
    product_name = prod.get("name", "Financial Product") if prod else "Financial Product"

    tenant_doc = await db["tenants"].find_one({"tenant_id": tenant_id})
    bank_name = tenant_doc.get("name", "Test Bank") if tenant_doc else "Test Bank"

    # Find recipient from snapshot
    query: Dict[str, Any] = {"tenant_id": tenant_id, "campaign_id": campaign_id}
    if record_id:
        query["record_id"] = record_id

    recipient = await db["campaign_recipients"].find_one(query)
    first_name = recipient.get("first_name", "Customer") if recipient else "Ankit"
    preferred_lang = recipient.get("preferred_language", "en-IN") if recipient else "en-IN"

    # Fetch voice config
    version = camp.get("current_voice_config_version", 1)
    vconfig_doc = await db["campaign_voice_configs"].find_one({
        "tenant_id": tenant_id, "campaign_id": campaign_id, "version": version
    })
    cfg = vconfig_doc.get("config", {}) if vconfig_doc else {}

    raw_sys = cfg.get("system_prompt", "Assist {{first_name}} regarding {{product_name}} from {{bank_name}}.")
    raw_open = cfg.get("opening_message", COMPLIANT_DISCLOSURE_PREFIX + "How are you today?")

    ctx = {
        "first_name": first_name,
        "bank_name": bank_name,
        "product_name": product_name,
    }

    rendered_sys = render_template(raw_sys, ctx)
    rendered_open = render_template(raw_open, ctx)

    payload = RenderedVoicePayload(
        first_name=first_name,
        bank_name=bank_name,
        product_name=product_name,
        language=preferred_lang,
        system_prompt=rendered_sys,
        opening_message=rendered_open,
        max_turns=cfg.get("max_turns", 8),
        info_to_collect=cfg.get("info_to_collect", []),
    )
    return payload.model_dump()
