"""
Product catalogue management: tenant-scoped CRUD with structured eligibility rules.
Never hardcodes specific bank product names; all definitions are dynamic.
"""
from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import TokenUser, get_current_user
from app.db import get_db

router = APIRouter(prefix="/api/products", tags=["products"])


class EligibilityRules(BaseModel):
    min_income: float = 0.0
    min_age: int = 18
    max_age: int = 70
    min_credit_score: int = 300
    employment_types: List[str] = ["salaried", "self_employed"]


class ProductCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    category: str = Field(..., min_length=2, max_length=60)
    description: str = ""
    active: bool = True
    eligibility_rules: EligibilityRules
    default_prompt: str = ""
    default_opening_message: str = ""


class ProductUpdateRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    eligibility_rules: Optional[EligibilityRules] = None
    default_prompt: Optional[str] = None
    default_opening_message: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreateRequest,
    current_user: TokenUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new product definition scoped to the authenticated tenant."""
    db = get_db()
    product_id = f"prd_{uuid.uuid4().hex[:10]}"
    doc = {
        "product_id": product_id,
        "tenant_id": current_user.tenant_id,
        "name": payload.name.strip(),
        "category": payload.category.strip(),
        "description": payload.description.strip(),
        "active": payload.active,
        "eligibility_rules": payload.eligibility_rules.model_dump(),
        "default_prompt": payload.default_prompt.strip(),
        "default_opening_message": payload.default_opening_message.strip(),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await db["products"].insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("")
async def list_products(
    active_only: bool = False,
    current_user: TokenUser = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List products belonging exclusively to the current tenant."""
    db = get_db()
    query: Dict[str, Any] = {"tenant_id": current_user.tenant_id}
    if active_only:
        query["active"] = True

    cursor = db["products"].find(query, {"_id": 0}).sort("created_at", -1)
    return [doc async for doc in cursor]


@router.get("/{product_id}")
async def get_product(
    product_id: str,
    current_user: TokenUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Fetch single product by ID, returning 404 on cross-tenant access."""
    db = get_db()
    doc = await db["products"].find_one(
        {"product_id": product_id, "tenant_id": current_user.tenant_id},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return doc


@router.put("/{product_id}")
async def update_product(
    product_id: str,
    payload: ProductUpdateRequest,
    current_user: TokenUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update product fields, enforcing tenant boundary."""
    db = get_db()
    update_data: Dict[str, Any] = {
        k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None
    }
    if "eligibility_rules" in update_data and isinstance(update_data["eligibility_rules"], BaseModel):
        update_data["eligibility_rules"] = update_data["eligibility_rules"].model_dump()
    update_data["updated_at"] = datetime.now(timezone.utc)

    result = await db["products"].find_one_and_update(
        {"product_id": product_id, "tenant_id": current_user.tenant_id},
        {"$set": update_data},
        return_document=True,
        projection={"_id": 0},
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return result


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user: TokenUser = Depends(get_current_user),
) -> None:
    """Delete product within tenant workspace, returning 404 if record is outside tenant."""
    db = get_db()
    res = await db["products"].delete_one({"product_id": product_id, "tenant_id": current_user.tenant_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
