from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator


# ── Commitment subtypes ────────────────────────────────────────────────────────

class AssinaturaData(BaseModel):
    title: str = Field(min_length=1)
    value: float = Field(gt=0)
    plan: Literal["mensal", "anual"]
    due_date: date


class CartaoData(BaseModel):
    name: str = Field(min_length=1)
    bank: str = Field(min_length=1)
    total_limit: float = Field(gt=0)
    closing_day: int = Field(ge=1, le=31)
    due_day: int = Field(ge=1, le=31)


class EmprestimoData(BaseModel):
    creditor: str = Field(min_length=1)
    total_amount: float = Field(gt=0)
    installments: int = Field(gt=0)
    monthly_payment: float = Field(gt=0)
    start_date: date


class ConsorcioData(BaseModel):
    administrator: str = Field(min_length=1)
    total_amount: float = Field(gt=0)
    installments: int = Field(gt=0)
    monthly_payment: float = Field(gt=0)
    start_date: date


class AssinaturaCommitment(BaseModel):
    type: Literal["assinatura"]
    data: AssinaturaData


class CartaoCommitment(BaseModel):
    type: Literal["cartao"]
    data: CartaoData


class EmprestimoCommitment(BaseModel):
    type: Literal["emprestimo"]
    data: EmprestimoData


class ConsorcioCommitment(BaseModel):
    type: Literal["consorcio"]
    data: ConsorcioData


CommitmentInput = Annotated[
    Union[AssinaturaCommitment, CartaoCommitment, EmprestimoCommitment, ConsorcioCommitment],
    Field(discriminator="type"),
]


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
        # validation happens at service level for clearer error messages
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

# Returned as dict[str, float]: {"alimentacao": 1000.0, ...}
SuggestedLimitsResponse = dict


# ── Onboarding save (POST) ────────────────────────────────────────────────────

class OnboardingSaveRequest(BaseModel):
    income: float | None = Field(default=None, gt=0)
    monthly_cost: float | None = Field(default=None, gt=0)
    selected_categories: list[str] | None = None
    has_emergency_fund: bool | None = None
    emergency_fund_amount: float | None = Field(default=None, gt=0)
    next_goal: NextGoalData | None = None
    commitment: CommitmentInput | None = None
    current_step: int = Field(ge=1, le=7)


# ── Onboarding response models ────────────────────────────────────────────────

class EmergencyFundGoalPreview(BaseModel):
    """Calculado e incluído na resposta do POST quando has_emergency_fund=False."""
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
    emergency_fund_goal: EmergencyFundGoalPreview | None = None  # apenas no POST
    next_goal: NextGoalData | None = None
    commitment: CommitmentInput | None = None
    current_step: int
    completed: bool


# ── Complete (PATCH) ──────────────────────────────────────────────────────────

class GoalCreatedSummary(BaseModel):
    title: str
    target_amount: float
    current_amount: float
    priority: str


class CommitmentCreatedSummary(BaseModel):
    type: str
    title: str


class OnboardingCompleteResponse(BaseModel):
    completed: bool
    categories_created: int
    limits_created: int
    goals_created: list[GoalCreatedSummary]
    commitment_created: CommitmentCreatedSummary | None = None
    message: str = "Onboarding finalizado com sucesso"
