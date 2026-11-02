"""
System prompt builder and configuration guardrail for voice agent sessions.

Enforces strict field whitelisting to prevent prompt injection and unauthorized context.
All product and institution details are injected dynamically from configuration.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

HINGLISH_REGEX = re.compile(
    r"\b(haan|nahi|nahin|mujhe|chahiye|theek|accha|kya|batao|lena|hai|namaste|lakh)\b",
    re.IGNORECASE,
)
ENGLISH_REGEX = re.compile(
    r"\b(what|how|why|when|is|are|the|this|that|loan|interest|rate|details|hello|please)\b",
    re.IGNORECASE,
)


def detect_language(text: str, current_lang: str, stt_detected: Optional[str] = None) -> str:
    """Detect spoken language using STT header first, Unicode script, English words, or Hinglish."""
    if stt_detected in ["en-IN", "hi-IN", "te-IN"]:
        return stt_detected
    if any("\u0900" <= c <= "\u097f" for c in text):
        return "hi-IN"
    if any("\u0c00" <= c <= "\u0c7f" for c in text):
        return "te-IN"
    if HINGLISH_REGEX.search(text):
        return "hi-IN"
    if ENGLISH_REGEX.search(text) and all(ord(c) < 128 for c in text):
        return "en-IN"
    return current_lang


PERMITTED_PROMPT_FIELDS = {
    "first_name",
    "bank_name",
    "product_name",
    "language",
    "system_prompt",
    "opening_message",
    "info_to_collect",
    "success_condition",
    "max_turns",
    "voice_by_language",
    "tenant_id",
    "input_mode",
}

LANGUAGE_INSTRUCTIONS = {
    "en-IN": "Respond naturally in Indian English.",
    "hi-IN": "Respond naturally in conversational Hindi (Devanagari script or standard spoken Hindi).",
    "te-IN": "Respond naturally in conversational Telugu (Telugu script or standard spoken Telugu).",
}


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate that the configuration contains ONLY permitted fields and required values.

    Raises ValueError if any unexpected field is present or required fields are missing.
    """
    extra_fields = set(config.keys()) - PERMITTED_PROMPT_FIELDS
    if extra_fields:
        raise ValueError(
            f"Config validation failed: unexpected field(s) detected: {sorted(extra_fields)}"
        )

    required_fields = ["first_name", "bank_name", "product_name", "language", "system_prompt"]
    missing = [f for f in required_fields if not config.get(f)]
    if missing:
        raise ValueError(f"Config validation failed: missing required field(s): {missing}")


def build_system_prompt(config: Dict[str, Any], current_language: str = "en-IN") -> str:
    """
    Assemble the runtime system prompt for the voice agent session.

    Guarantees concise turns (1-2 sentences), clear AI identity disclosure,
    and adaptive language alignment.
    """
    validate_config(config)

    first_name = config["first_name"]
    bank_name = config["bank_name"]
    product_name = config["product_name"]
    base_prompt = config["system_prompt"]
    lang_instruction = LANGUAGE_INSTRUCTIONS.get(
        current_language, LANGUAGE_INSTRUCTIONS["en-IN"]
    )

    info_list = config.get("info_to_collect", [])
    fields_desc = ", ".join(
        f"{item['field']} ({item.get('question', '')})" for item in info_list
    )

    return (
        f"{base_prompt}\n\n"
        f"You are speaking with {first_name} on behalf of {bank_name} regarding {product_name}.\n"
        f"Language requirement: {lang_instruction}\n"
        "Crucial Voice Rules:\n"
        "1. Be extremely concise: reply in strictly 1 to 2 short sentences per turn. Keep the first sentence under 8 words so playback starts immediately.\n"
        "2. Never monologue or list long paragraphs. This is an interactive spoken phone conversation.\n"
        "3. Always be polite, professional, and helpful.\n"
        "4. You must always be honest that you are an AI assistant if asked.\n"
        f"5. Target information to collect if customer is interested: {fields_desc}.\n"
        "6. If the customer declines or is busy, politely acknowledge and offer to reconnect later."
    )

