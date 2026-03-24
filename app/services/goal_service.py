from __future__ import annotations

import structlog
from fastapi import HTTPException, status
from supabase import Client

from app.repositories.goal_repository import GoalRepository
from app.schemas.goal import (
    GoalCreateRequest,
    GoalDeleteResponse,
    GoalProgressRequest,
    GoalResponse,
    GoalUpdateRequest,
    GoalsListResponse,
)

logger = structlog.get_logger()


def _to_response(row: dict) -> GoalResponse:
    target = float(row["target_amount"])
    current = float(row["current_amount"])
    percentage = round((current / target) * 100, 1) if target > 0 else 0.0
    return GoalResponse(
        id=row["id"],
        title=row["title"],
        description=row.get("description"),
        target_amount=target,
        current_amount=current,
        priority=row["priority"],
        target_date=row.get("target_date"),
        monthly_contribution=float(row["monthly_contribution"]) if row.get("monthly_contribution") else None,
        is_completed=row["is_completed"],
        progress_percentage=min(percentage, 100.0),
    )


def list_goals(user_uuid: str, completed, supabase: Client) -> GoalsListResponse:
    repo = GoalRepository(supabase)
    rows = repo.list_by_user(user_uuid, completed)
    return GoalsListResponse(data=[_to_response(r) for r in rows])


def get_goal(user_uuid: str, goal_id: int, supabase: Client) -> GoalResponse:
    repo = GoalRepository(supabase)
    row = repo.get_by_id(user_uuid, goal_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta nao encontrada")
    return _to_response(row)


def create_goal(user_uuid: str, data: GoalCreateRequest, supabase: Client) -> GoalResponse:
    repo = GoalRepository(supabase)
    row = repo.create(
        user_uuid=user_uuid,
        title=data.title.strip(),
        target_amount=data.target_amount,
        priority=data.priority,
        description=data.description,
        target_date=data.target_date,
        monthly_contribution=data.monthly_contribution,
    )
    logger.info("goal_created", user_uuid=user_uuid, title=data.title)
    return _to_response(row)


def update_goal(user_uuid: str, goal_id: int, data: GoalUpdateRequest, supabase: Client) -> GoalResponse:
    repo = GoalRepository(supabase)
    existing = repo.get_by_id(user_uuid, goal_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta nao encontrada")

    fields: dict = {}
    if data.title is not None:
        fields["title"] = data.title.strip()
    if data.description is not None:
        fields["description"] = data.description
    if data.target_amount is not None:
        fields["target_amount"] = data.target_amount
    if data.priority is not None:
        fields["priority"] = data.priority
    if data.target_date is not None:
        fields["target_date"] = data.target_date.isoformat()
    if data.monthly_contribution is not None:
        fields["monthly_contribution"] = data.monthly_contribution

    if not fields:
        return _to_response(existing)

    updated = repo.update(user_uuid, goal_id, fields)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta nao encontrada")

    logger.info("goal_updated", user_uuid=user_uuid, goal_id=goal_id)
    return _to_response(updated)


def add_goal_progress(user_uuid: str, goal_id: int, data: GoalProgressRequest, supabase: Client) -> GoalResponse:
    repo = GoalRepository(supabase)
    updated = repo.add_progress(user_uuid, goal_id, data.amount)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta nao encontrada")
    logger.info("goal_progress_added", user_uuid=user_uuid, goal_id=goal_id, amount=data.amount)
    return _to_response(updated)


def delete_goal(user_uuid: str, goal_id: int, supabase: Client) -> GoalDeleteResponse:
    repo = GoalRepository(supabase)
    existing = repo.get_by_id(user_uuid, goal_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta nao encontrada")
    repo.delete(user_uuid, goal_id)
    logger.info("goal_deleted", user_uuid=user_uuid, goal_id=goal_id)
    return GoalDeleteResponse()
