from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.core.dependencies import UserContext, get_current_user, get_supabase_client
from app.schemas.onboarding import (
    CompleteOnboardingResponse,
    EmergencyFundRequest,
    EmergencyFundResponse,
    NextGoalCreatedResponse,
    NextGoalRequest,
    OnboardingResponse,
    SaveOnboardingRequest,
    SaveOnboardingResponse,
)
from app.services import onboarding_service

router = APIRouter()


@router.get("/", response_model=OnboardingResponse)
def get_onboarding(
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> OnboardingResponse:
    return onboarding_service.get_onboarding(current_user.user_id, supabase)


@router.post("/", response_model=SaveOnboardingResponse, status_code=201)
def save_onboarding(
    data: SaveOnboardingRequest,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> SaveOnboardingResponse:
    return onboarding_service.save_onboarding(current_user.user_id, data, supabase)


@router.get("/suggested-limits")
def get_suggested_limits(
    income: float = Query(..., description="Renda mensal"),
    categories: str = Query(..., description="Categorias separadas por virgula"),
    current_user: UserContext = Depends(get_current_user),
) -> dict:
    cats = [c.strip() for c in categories.split(",") if c.strip()]
    return onboarding_service.get_suggested_limits(income, cats)


@router.post("/emergency-fund", response_model=EmergencyFundResponse)
def calc_emergency_fund(
    data: EmergencyFundRequest,
    current_user: UserContext = Depends(get_current_user),
) -> EmergencyFundResponse:
    return onboarding_service.calc_emergency_fund(data)


@router.post("/next-goal", response_model=NextGoalCreatedResponse, status_code=201)
def create_next_goal(
    data: NextGoalRequest,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> NextGoalCreatedResponse:
    return onboarding_service.create_next_goal(current_user.user_id, data, supabase)


@router.patch("/complete", response_model=CompleteOnboardingResponse)
def complete_onboarding(
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> CompleteOnboardingResponse:
    return onboarding_service.complete_onboarding(current_user.user_id, supabase)
