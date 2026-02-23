import structlog
from fastapi import HTTPException, status
from supabase import Client

from app.repositories.onboarding_repository import OnboardingRepository
from app.schemas.onboarding import CommitmentSchema, NextGoalSchema, OnboardingResponse

logger = structlog.get_logger()


def get_onboarding(user_uuid: str, supabase: Client) -> OnboardingResponse:
    repo = OnboardingRepository(supabase)
    row = repo.get_by_user_uuid(user_uuid)

    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Onboarding não iniciado")

    next_goal_data = row.get("next_goal")
    commitment_data = row.get("commitment")

    return OnboardingResponse(
        income=row.get("income"),
        monthly_cost=row.get("monthly_cost"),
        selected_categories=row.get("selected_categories"),
        suggested_limits=row.get("suggested_limits"),
        has_emergency_fund=row.get("has_emergency_fund"),
        emergency_fund_amount=row.get("emergency_fund_amount"),
        next_goal=NextGoalSchema(**next_goal_data) if next_goal_data else None,
        commitment=CommitmentSchema(**commitment_data) if commitment_data else None,
        current_step=row.get("current_step"),
        completed=row.get("completed") or False,
    )
