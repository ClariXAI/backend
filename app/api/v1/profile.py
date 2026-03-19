from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.core.dependencies import UserContext, get_current_user, get_supabase_client
from app.schemas.profile import (
    PaymentsResponse,
    PlanUpdateRequest,
    PlanUpdateResponse,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.services import profile_service

router = APIRouter()


@router.get("/", response_model=ProfileResponse)
def get_profile(
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> ProfileResponse:
    return profile_service.get_profile(current_user.user_id, supabase)


@router.put("/", response_model=ProfileResponse)
def update_profile(
    data: ProfileUpdateRequest,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> ProfileResponse:
    return profile_service.update_profile(current_user.user_id, data, supabase)


@router.put("/plan", response_model=PlanUpdateResponse)
def update_plan(
    data: PlanUpdateRequest,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> PlanUpdateResponse:
    return profile_service.update_plan(current_user.user_id, data, supabase)


@router.get("/payments", response_model=PaymentsResponse)
def get_payments(
    page: Annotated[int, Query(ge=1, description="Página")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Itens por página")] = 10,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> PaymentsResponse:
    return profile_service.get_payments(current_user.user_id, page, limit, supabase)
