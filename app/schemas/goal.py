from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class GoalCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    target_amount: float = Field(gt=0)
    priority: Literal["alta", "media", "baixa"] = "media"
    target_date: date | None = None
    monthly_contribution: float | None = Field(default=None, gt=0)


class GoalUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    target_amount: float | None = Field(default=None, gt=0)
    priority: Literal["alta", "media", "baixa"] | None = None
    target_date: date | None = None
    monthly_contribution: float | None = Field(default=None, gt=0)


class GoalProgressRequest(BaseModel):
    amount: float = Field(gt=0, description="Valor a adicionar ao current_amount")


class GoalResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    target_amount: float
    current_amount: float
    priority: str
    target_date: date | None = None
    monthly_contribution: float | None = None
    is_completed: bool
    progress_percentage: float = 0.0


class GoalsListResponse(BaseModel):
    data: list[GoalResponse]


class GoalDeleteResponse(BaseModel):
    message: str = "Meta removida com sucesso"
