"""Admin usage statistics and model pricing API."""
import json
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db
from app.models.usage import ModelPricing
from app.core.response import success
from app.core.exceptions import BusinessError
from app.services import usage_service

router = APIRouter(prefix="/api/admin/usage", tags=["admin-usage"])


@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    data = await usage_service.get_admin_overview(db)
    return success(data)


@router.get("/by-user")
async def get_by_user(db: AsyncSession = Depends(get_db)):
    data = await usage_service.get_admin_by_user(db)
    return success(data)


class PricingRequest(BaseModel):
    model_name: str
    provider: str = ""
    input_price_per_1k: float = 0.0
    output_price_per_1k: float = 0.0
    currency: str = "CNY"
    is_active: bool = True


@router.get("/model-pricing")
async def list_pricing(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ModelPricing).order_by(ModelPricing.model_name))
    items = [
        {
            "id": p.id,
            "model_name": p.model_name,
            "provider": p.provider,
            "input_price_per_1k": p.input_price_per_1k,
            "output_price_per_1k": p.output_price_per_1k,
            "currency": p.currency,
            "is_active": p.is_active,
        }
        for p in result.scalars().all()
    ]
    return success(items)


@router.post("/model-pricing")
async def create_pricing(req: PricingRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(ModelPricing).where(ModelPricing.model_name == req.model_name)
    )
    if existing.scalar_one_or_none():
        raise BusinessError(-1, f"模型 '{req.model_name}' 定价已存在")

    pricing = ModelPricing(
        model_name=req.model_name,
        provider=req.provider,
        input_price_per_1k=req.input_price_per_1k,
        output_price_per_1k=req.output_price_per_1k,
        currency=req.currency,
        is_active=req.is_active,
    )
    db.add(pricing)
    await db.commit()
    return success({"id": pricing.id})


@router.put("/model-pricing/{pricing_id}")
async def update_pricing(
    pricing_id: int,
    req: PricingRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelPricing).where(ModelPricing.id == pricing_id))
    pricing = result.scalar_one_or_none()
    if not pricing:
        raise BusinessError(-4, "定价不存在")

    pricing.model_name = req.model_name
    pricing.provider = req.provider
    pricing.input_price_per_1k = req.input_price_per_1k
    pricing.output_price_per_1k = req.output_price_per_1k
    pricing.currency = req.currency
    pricing.is_active = req.is_active
    await db.commit()
    return success(None)
