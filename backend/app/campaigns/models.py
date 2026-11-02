"""
Domain models and schema definitions for campaign configuration, audience targeting,
and immutable voice versions. Strictly validates permitted template variables.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

ALLOWED_TEMPLATE_VARS = {"first_name", "bank_name", "product_name"}
TEMPLATE_VAR_REGEX = re.compile(r"\{\{([^}]+)\}\}")


def validate_template_variables(text: str) -> None:
    """Verify that only whitelisted variables (first_name, bank_name, product_name) exist in text."""
    found_vars = set(TEMPLATE_VAR_REGEX.findall(text))
    unknown_vars = found_vars - ALLOWED_TEMPLATE_VARS
    if unknown_vars:
        raise ValueError(
            f"Invalid template variables detected: {sorted(unknown_vars)}. Allowed: {sorted(ALLOWED_TEMPLATE_VARS)}"
        )


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=3, ge=1, le=5)
    retry_interval_minutes: int = Field(default=60, ge=5, le=1440)


class InfoField(BaseModel):
    field: str
    question: str
    required: bool = True


class VoiceConfigData(BaseModel):
    default_language: Literal["en-IN", "hi-IN", "te-IN"] = "en-IN"
    voice_by_language: Dict[str, str] = Field(default_factory=lambda: {
        "en-IN": "Nalini", "hi-IN": "Nalini", "te-IN": "Suhana"
    })
    tone: str = "polite, helpful, professional"
    system_prompt: str = ""
    opening_message: str = ""
    conversation_objective: str = ""
    info_to_collect: List[InfoField] = Field(default_factory=list)
    success_condition: str = ""
    fallback_behaviour: str = "Politely acknowledge and ask if executive can call later."
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    max_turns: int = Field(default=8, ge=2, le=20)
    closing_message: str = "Thank you for your time. Have a wonderful day!"

    @field_validator("system_prompt", "opening_message", "closing_message")
    @classmethod
    def check_vars(cls, v: str) -> str:
        validate_template_variables(v)
        return v


class CampaignCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    product_id: str
    audience_type: Literal["customers", "leads"]
    objective: str = ""
    description: str = ""
    allow_ineligible_override: bool = False


class CampaignUpdateRequest(BaseModel):
    name: Optional[str] = None
    objective: Optional[str] = None
    description: Optional[str] = None
    allow_ineligible_override: Optional[bool] = None


class AudienceFilter(BaseModel):
    bands: Optional[List[str]] = None
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    eligibility: Literal["eligible", "not_eligible", "all"] = "all"
    language: Optional[str] = None
    city: Optional[str] = None


class AudiencePreviewRequest(BaseModel):
    audience_type: Literal["customers", "leads"]
    product_id: str
    filters: AudienceFilter = Field(default_factory=AudienceFilter)


class SaveAudienceRequest(BaseModel):
    selection_mode: Literal["filter", "manual", "combined"] = "filter"
    filters: AudienceFilter = Field(default_factory=AudienceFilter)
    selected_record_ids: Optional[List[str]] = None
    excluded_record_ids: Optional[List[str]] = None
    allow_ineligible_override: bool = False
