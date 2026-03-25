from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── Next goal ─────────────────────────────────────────────────────────────────

class NextGoalData(BaseModel):
    """Dados de próxima meta armazenados como JSONB no onboarding."""
    id: str  # preset id ou "outro"
    title: str
    description: str | None = None
    target_amount: float
    priority: str
    target_date: date | None = None
    monthly_contribution: float | None = None


# ── Emergency fund ────────────────────────────────────────────────────────────

class EmergencyFundRequest(BaseModel):
    has_emergency_fund: bool
    emergency_fund_amount: float | None = Field(default=None, gt=0)
    income: float = Field(gt=0)
    monthly_cost: float = Field(gt=0)


class EmergencyFundResponse(BaseModel):
    title: str
    target_amount: float
    current_amount: float
    priority: str
    target_date: date | None = None
    monthly_contribution: float | None = None
    ai_suggestion: str


# ── Next goal request/response ────────────────────────────────────────────────

class NextGoalRequest(BaseModel):
    goal_id: str  # viagem_europa | entrada_apartamento | novo_notebook | outro
    custom_title: str | None = None
    custom_description: str | None = None
    custom_amount: float | None = Field(default=None, gt=0)
    income: float = Field(gt=0)
    monthly_cost: float = Field(gt=0)

    @field_validator("custom_title")
    @classmethod
    def require_custom_title_for_outro(cls, v: str | None, info: object) -> str | None:
        return v


class NextGoalResponse(BaseModel):
    title: str
    description: str | None = None
    target_amount: float
    current_amount: float = 0
    priority: str
    target_date: date | None = None
    monthly_contribution: float | None = None
    ai_suggestion: str


# ── Suggested limits ──────────────────────────────────────────────────────────

SuggestedLimitsResponse = dict


# ── Onboarding save (POST) ────────────────────────────────────────────────────

class OnboardingSaveRequest(BaseModel):
    income: float | None = Field(default=None, gt=0)
    monthly_cost: float | None = Field(default=None, gt=0)
    selected_categories: list[str] | None = None
    has_emergency_fund: bool | None = None
    emergency_fund_amount: float | None = Field(default=None, gt=0)
    next_goal: NextGoalData | None = None
    current_step: int = Field(ge=1, le=5)


# ── Onboarding response models ────────────────────────────────────────────────

class EmergencyFundGoalPreview(BaseModel):
    title: str
    target_amount: float
    current_amount: float
    priority: str
    target_date: date | None = None
    monthly_contribution: float | None = None


class OnboardingResponse(BaseModel):
    income: float | None = None
    monthly_cost: float | None = None
    selected_categories: list[str] | None = None
    suggested_limits: dict | None = None
    has_emergency_fund: bool | None = None
    emergency_fund_amount: float | None = None
    emergency_fund_goal: EmergencyFundGoalPreview | None = None
    next_goal: NextGoalData | None = None
    current_step: int
    completed: bool


# ── Complete (PATCH) ──────────────────────────────────────────────────────────

class GoalCreatedSummary(BaseModel):
    title: str
    target_amount: float
    current_amount: float
    priority: str


class OnboardingCompleteResponse(BaseModel):
    completed: bool
    categories_created: int
    limits_created: int
    goals_created: list[GoalCreatedSummary]
    message: str = "Onboarding finalizado com sucesso"
