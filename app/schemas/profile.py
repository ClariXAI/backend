from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── GET /profile/ ─────────────────────────────────────────────────────────────

class ProfileResponse(BaseModel):
    id: str
    name: str
    email: str
    cpf: str | None = None
    phone: str | None = None
    plan: str  # "trial" | "essential" | "premium"
    billing_period: str | None = None  # "mensal" | "anual" | None (trial)
    onboarding_completed: bool
    created_at: datetime


# ── PUT /profile/ ─────────────────────────────────────────────────────────────

class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    phone: str | None = None


# ── PUT /profile/plan ─────────────────────────────────────────────────────────

class PlanUpdateRequest(BaseModel):
    plan: Literal["essential", "premium"]
    billing_period: Literal["mensal", "anual"]


class PlanUpdateResponse(BaseModel):
    plan: str
    billing_period: str
    price: float
    next_billing_date: datetime
    message: str = "Plano atualizado com sucesso"


# ── GET /profile/payments ─────────────────────────────────────────────────────

class PaymentRecord(BaseModel):
    id: int
    date: datetime
    amount: float | None = None
    status: str
    method: str | None = None  # "PIX" | "Cartão de Crédito"
    invoice: str | None = None


class PaymentsResponse(BaseModel):
    data: list[PaymentRecord]
    total: int
    page: int
    limit: int
