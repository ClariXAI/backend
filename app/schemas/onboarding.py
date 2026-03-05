from datetime import date
from typing import Any

from pydantic import BaseModel

# ─── Category weights (used for suggested_limits calculation) ─────────────────

CATEGORY_WEIGHTS: dict[str, float] = {
    "alimentacao": 0.20,
    "agua": 0.03,
    "moradia": 0.30,
    "energia": 0.05,
    "internet": 0.04,
    "transporte": 0.10,
    "estudo": 0.05,
    "saude": 0.08,
    "entretenimento": 0.05,
    "lazer": 0.05,
}


# ─── Shared sub-schemas ───────────────────────────────────────────────────────

class NextGoalSchema(BaseModel):
    id: str | None = None
    title: str | None = None
    description: str | None = None
    target_amount: float | None = None
    priority: str | None = None
    target_date: date | None = None
    monthly_contribution: float | None = None


class CommitmentSchema(BaseModel):
    type: str | None = None
    data: dict[str, Any] | None = None


class EmergencyFundGoalSchema(BaseModel):
    title: str
    target_amount: float
    current_amount: float
    priority: str
    target_date: date | None = None
    monthly_contribution: float | None = None


# ─── GET / ────────────────────────────────────────────────────────────────────

class OnboardingResponse(BaseModel):
    income: float | None = None
    monthly_cost: float | None = None
    selected_categories: list[str] | None = None
    suggested_limits: dict[str, float] | None = None
    has_emergency_fund: bool | None = None
    emergency_fund_amount: float | None = None
    next_goal: NextGoalSchema | None = None
    commitment: CommitmentSchema | None = None
    current_step: int | None = None
    completed: bool = False


# ─── POST / (save / upsert) ───────────────────────────────────────────────────

class SaveOnboardingRequest(BaseModel):
    income: float | None = None
    monthly_cost: float | None = None
    selected_categories: list[str] | None = None
    has_emergency_fund: bool | None = None
    emergency_fund_amount: float | None = None
    next_goal: NextGoalSchema | None = None
    commitment: CommitmentSchema | None = None
    current_step: int | None = None


class SaveOnboardingResponse(BaseModel):
    income: float | None = None
    monthly_cost: float | None = None
    selected_categories: list[str] | None = None
    suggested_limits: dict[str, float] | None = None
    has_emergency_fund: bool | None = None
    emergency_fund_amount: float | None = None
    emergency_fund_goal: EmergencyFundGoalSchema | None = None
    next_goal: NextGoalSchema | None = None
    commitment: CommitmentSchema | None = None
    current_step: int | None = None
    completed: bool = False


# ─── POST /emergency-fund ─────────────────────────────────────────────────────

class EmergencyFundRequest(BaseModel):
    has_emergency_fund: bool
    emergency_fund_amount: float | None = None
    income: float
    monthly_cost: float


class EmergencyFundResponse(BaseModel):
    title: str
    target_amount: float
    current_amount: float
    priority: str
    target_date: date | None = None
    monthly_contribution: float | None = None
    ai_suggestion: str | None = None


# ─── POST /next-goal ──────────────────────────────────────────────────────────

class NextGoalRequest(BaseModel):
    goal_id: str
    custom_title: str | None = None
    custom_description: str | None = None
    custom_amount: float | None = None
    income: float
    monthly_cost: float


class NextGoalCreatedResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    target_amount: float
    current_amount: float
    priority: str
    target_date: date | None = None
    monthly_contribution: float | None = None
    ai_suggestion: str | None = None


# ─── PATCH /complete ──────────────────────────────────────────────────────────

class GoalSummarySchema(BaseModel):
    title: str
    target_amount: float
    current_amount: float
    priority: str


class CommitmentSummarySchema(BaseModel):
    type: str
    title: str


class CompleteOnboardingResponse(BaseModel):
    completed: bool
    categories_created: int
    limits_created: int
    goals_created: list[GoalSummarySchema]
    commitment_created: CommitmentSummarySchema | None = None
    message: str
