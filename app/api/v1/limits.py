from __future__ import annotations

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.dependencies import UserContext, get_current_user, get_supabase_client
from app.schemas.limit import (
    LimitCreateRequest,
    LimitDeleteResponse,
    LimitResponse,
    LimitUpdateRequest,
    LimitsListResponse,
)
from app.services import limit_service

router = APIRouter()


@router.get("/", response_model=LimitsListResponse)
def list_limits(
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> LimitsListResponse:
    return limit_service.list_limits(current_user.user_id, supabase)


@router.post("/", response_model=LimitResponse, status_code=201)
def create_limit(
    data: LimitCreateRequest,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> LimitResponse:
    return limit_service.create_limit(current_user.user_id, data, supabase)


@router.put("/{limit_id}", response_model=LimitResponse)
def update_limit(
    limit_id: int,
    data: LimitUpdateRequest,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> LimitResponse:
    return limit_service.update_limit(current_user.user_id, limit_id, data, supabase)


@router.delete("/{limit_id}", response_model=LimitDeleteResponse)
def delete_limit(
    limit_id: int,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> LimitDeleteResponse:
    return limit_service.delete_limit(current_user.user_id, limit_id, supabase)
