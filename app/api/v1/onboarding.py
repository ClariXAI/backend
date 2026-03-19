from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.core.dependencies import UserContext, get_current_user, get_supabase_client
from app.schemas.onboarding import (
    EmergencyFundRequest,
    EmergencyFundResponse,
    NextGoalRequest,
    NextGoalResponse,
    OnboardingCompleteResponse,
    OnboardingResponse,
    OnboardingSaveRequest,
)
from app.services import onboarding_service

router = APIRouter()


@router.get("/", response_model=OnboardingResponse)
def get_onboarding(
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> OnboardingResponse:
    return onboarding_service.get_onboarding(current_user.user_id, supabase)


@router.post("/", response_model=OnboardingResponse, status_code=201)
def save_onboarding(
    data: OnboardingSaveRequest,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> OnboardingResponse:
    return onboarding_service.save_onboarding(current_user.user_id, data, supabase)


@router.patch("/complete", response_model=OnboardingCompleteResponse)
def complete_onboarding(
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> OnboardingCompleteResponse:
    return onboarding_service.complete_onboarding(current_user.user_id, supabase)


@router.get("/suggested-limits", response_model=dict)
def get_suggested_limits(
    income: Annotated[float, Query(gt=0, description="Renda mensal do usuário")],
    categories: Annotated[str, Query(description="Categorias separadas por vírgula")],
    current_user: UserContext = Depends(get_current_user),  # noqa: ARG001
) -> dict:
    category_list = [c.strip() for c in categories.split(",") if c.strip()]
    return onboarding_service.get_suggested_limits(income, category_list)


@router.post("/emergency-fund", response_model=EmergencyFundResponse)
def calculate_emergency_fund(
    data: EmergencyFundRequest,
    current_user: UserContext = Depends(get_current_user),  # noqa: ARG001
    supabase: Client = Depends(get_supabase_client),
) -> EmergencyFundResponse:
    return onboarding_service.calculate_emergency_fund(data, supabase)


@router.post("/next-goal", response_model=NextGoalResponse, status_code=201)
def calculate_next_goal(
    data: NextGoalRequest,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> NextGoalResponse:
    return onboarding_service.calculate_next_goal(current_user.user_id, data, supabase)
