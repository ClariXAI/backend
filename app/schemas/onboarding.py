from datetime import date
from typing import Any

from pydantic import BaseModel


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
