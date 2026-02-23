from fastapi import APIRouter, Depends
from supabase import Client

from app.core.dependencies import UserContext, get_current_user, get_supabase_client
from app.schemas.onboarding import OnboardingResponse
from app.services import onboarding_service

router = APIRouter()


@router.get("/", response_model=OnboardingResponse)
def get_onboarding(
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> OnboardingResponse:
    return onboarding_service.get_onboarding(current_user.user_id, supabase)
