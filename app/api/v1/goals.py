from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.core.dependencies import UserContext, get_current_user, get_supabase_client
from app.schemas.goal import (
    GoalCreateRequest,
    GoalDeleteResponse,
    GoalProgressRequest,
    GoalResponse,
    GoalUpdateRequest,
    GoalsListResponse,
)
from app.services import goal_service

router = APIRouter()


@router.get("/", response_model=GoalsListResponse)
def list_goals(
    completed: Annotated[Optional[bool], Query(description="Filtrar por concluidas")] = None,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> GoalsListResponse:
    return goal_service.list_goals(current_user.user_id, completed, supabase)


@router.get("/{goal_id}", response_model=GoalResponse)
def get_goal(
    goal_id: int,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> GoalResponse:
    return goal_service.get_goal(current_user.user_id, goal_id, supabase)


@router.post("/", response_model=GoalResponse, status_code=201)
def create_goal(
    data: GoalCreateRequest,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> GoalResponse:
    return goal_service.create_goal(current_user.user_id, data, supabase)


@router.put("/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: int,
    data: GoalUpdateRequest,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> GoalResponse:
    return goal_service.update_goal(current_user.user_id, goal_id, data, supabase)


@router.patch("/{goal_id}/progress", response_model=GoalResponse)
def add_goal_progress(
    goal_id: int,
    data: GoalProgressRequest,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> GoalResponse:
    return goal_service.add_goal_progress(current_user.user_id, goal_id, data, supabase)


@router.delete("/{goal_id}", response_model=GoalDeleteResponse)
def delete_goal(
    goal_id: int,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> GoalDeleteResponse:
    return goal_service.delete_goal(current_user.user_id, goal_id, supabase)
