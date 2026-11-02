"""
Generic CSV ingestion router for customers and leads with tenant isolation,
strict synthetic phone verification, consent attestation, and deduplication.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
import re
import uuid
from typing import Any, Dict, List, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.auth import TokenUser, get_current_user
from app.db import get_db

router = APIRouter(prefix="/api/import", tags=["import"])

SYNTHETIC_PHONE_REGEX = re.compile(r"^(\+91[\s-]?)?90000\d{5}$")


def normalize_phone(raw_phone: str) -> str:
    """Standardize phone format to +9190000xxxxx."""
    digits = re.sub(r"\D", "", raw_phone)
    if digits.startswith("91") and len(digits) == 12:
        return f"+{digits}"
    if len(digits) == 10:
        return f"+91{digits}"
    return raw_phone.strip()


class ImportReport(BaseModel):
    record_type: str
    rows_processed: int
    rows_accepted: int
    rows_rejected: int
    duplicates_skipped: int
    rejections: List[Dict[str, Any]]


@router.post("/{record_type}", response_model=ImportReport)
async def import_csv(
    record_type: Literal["customers", "leads"],
    file: UploadFile = File(...),
    attestation: bool = Form(...),
    current_user: TokenUser = Depends(get_current_user),
) -> ImportReport:
    """Ingest customers or leads from CSV with consent and synthetic data enforcement."""
    if not attestation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent attestation is required before importing records",
        )

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or missing headers")

    db = get_db()
    collection_name = "customers" if record_type == "customers" else "leads"
    coll = db[collection_name]

    accepted_docs: List[Dict[str, Any]] = []
    rejections: List[Dict[str, Any]] = []
    duplicates_skipped = 0
    now = datetime.now(timezone.utc)

    # Fetch existing phone numbers for deduplication within tenant
    existing_phones = set()
    async for item in coll.find({"tenant_id": current_user.tenant_id}, {"phone": 1}):
        if item.get("phone"):
            existing_phones.add(item["phone"])

    seen_in_batch = set()

    for idx, row in enumerate(reader, start=1):
        full_name = row.get("full_name", "").strip()
        raw_phone = row.get("phone", "").strip()
        cleaned_phone = normalize_phone(raw_phone)

        # 1. Check synthetic phone safety pattern
        if not SYNTHETIC_PHONE_REGEX.match(cleaned_phone):
            rejections.append({
                "row": idx,
                "phone": raw_phone,
                "reason": "Rejected non-synthetic phone; must match test pattern +91 90000 xxxxx",
            })
            continue

        # 2. Check deduplication within tenant
        if cleaned_phone in existing_phones or cleaned_phone in seen_in_batch:
            duplicates_skipped += 1
            continue
        seen_in_batch.add(cleaned_phone)

        # Parse numeric and boolean fields
        try:
            age = int(row.get("age", 25))
            income = float(row.get("monthly_income_inr", 30000.0))
            credit_score = int(row.get("credit_score", 650))
        except ValueError:
            rejections.append({"row": idx, "reason": "Invalid numeric format in age/income/score"})
            continue

        consent_val = str(row.get("consent", "true")).strip().lower() in ["true", "1", "yes"]
        dnd_val = str(row.get("dnd", "false")).strip().lower() in ["true", "1", "yes"]

        doc = {
            "record_id": f"rec_{uuid.uuid4().hex[:10]}",
            "tenant_id": current_user.tenant_id,
            "record_type": record_type,
            "external_ref": row.get("external_ref", "").strip(),
            "full_name": full_name or "Valued Customer",
            "phone": cleaned_phone,
            "email": row.get("email", "").strip(),
            "age": age,
            "monthly_income_inr": income,
            "employment_type": row.get("employment_type", "salaried").strip().lower(),
            "credit_score": credit_score,
            "city": row.get("city", "Mumbai").strip(),
            "preferred_language": row.get("preferred_language", "en-IN").strip(),
            "consent": consent_val,
            "dnd": dnd_val,
            "contactable": bool(consent_val and not dnd_val),
            "created_at": now,
        }
        accepted_docs.append(doc)

    if accepted_docs:
        await coll.insert_many(accepted_docs)

    return ImportReport(
        record_type=record_type,
        rows_processed=idx if "idx" in locals() else 0,
        rows_accepted=len(accepted_docs),
        rows_rejected=len(rejections),
        duplicates_skipped=duplicates_skipped,
        rejections=rejections[:50],
    )

