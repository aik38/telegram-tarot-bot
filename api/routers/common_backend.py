from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.db.common_backend import CommonBackendDB

router = APIRouter(prefix="/api/v1")

_db = CommonBackendDB()


def get_db() -> CommonBackendDB:
    return _db


class ResolveIdentityRequest(BaseModel):
    provider: Literal["telegram", "line"]
    provider_user_id: str = Field(..., min_length=1)


class ResolveIdentityResponse(BaseModel):
    account_id: int
    identity_id: int


@router.post("/identities/resolve", response_model=ResolveIdentityResponse)
async def resolve_identity(
    payload: ResolveIdentityRequest, db: CommonBackendDB = Depends(get_db)
) -> ResolveIdentityResponse:
    account_id, identity_id = db.resolve_identity(
        payload.provider, payload.provider_user_id
    )
    return ResolveIdentityResponse(account_id=account_id, identity_id=identity_id)


class CheckEntitlementRequest(BaseModel):
    account_id: int


class CheckEntitlementResponse(BaseModel):
    allowed: bool
    plan_key: str
    credits_remaining: int
    period_end: datetime


@router.post("/entitlements/check", response_model=CheckEntitlementResponse)
async def check_entitlement(
    payload: CheckEntitlementRequest, db: CommonBackendDB = Depends(get_db)
) -> CheckEntitlementResponse:
    entitlement, credits_remaining, period_end = db.check_entitlement(
        payload.account_id
    )
    allowed = credits_remaining > 0
    return CheckEntitlementResponse(
        allowed=allowed,
        plan_key=entitlement.plan.plan_code,
        credits_remaining=credits_remaining,
        period_end=period_end,
    )


class ConsumeEntitlementRequest(BaseModel):
    account_id: int
    feature: str
    units: int = 1
    request_id: str


class ConsumeEntitlementResponse(BaseModel):
    allowed: bool
    credits_remaining: int


@router.post("/entitlements/consume", response_model=ConsumeEntitlementResponse)
async def consume_entitlement(
    payload: ConsumeEntitlementRequest, db: CommonBackendDB = Depends(get_db)
) -> ConsumeEntitlementResponse:
    allowed, credits_remaining = db.consume_entitlement(
        account_id=payload.account_id,
        feature=payload.feature,
        units=payload.units,
        request_id=payload.request_id,
    )
    return ConsumeEntitlementResponse(
        allowed=allowed,
        credits_remaining=credits_remaining,
    )
