from __future__ import annotations

from calendar import monthrange
from datetime import date

import structlog
from fastapi import HTTPException, status
from supabase import Client

from app.repositories.category_repository import CategoryRepository
from app.repositories.limit_repository import LimitRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.limit import (
    LimitCreateRequest,
    LimitDeleteResponse,
    LimitResponse,
    LimitUpdateRequest,
    LimitsListResponse,
)

logger = structlog.get_logger()


def _month_range() -> tuple[date, date]:
    today = date.today()
    last_day = monthrange(today.year, today.month)[1]
    return date(today.year, today.month, 1), date(today.year, today.month, last_day)


def _to_response(row: dict, cat_map: dict[int, dict], spent_map: dict[int, float]) -> LimitResponse:
    cid = row["category_id"]
    cat = cat_map.get(cid, {})
    limit_amount = float(row["amount"])
    spent = round(spent_map.get(cid, 0.0), 2)
    remaining = round(max(limit_amount - spent, 0.0), 2)
    percentage = round((spent / limit_amount) * 100, 1) if limit_amount > 0 else 0.0
    return LimitResponse(
        id=row["id"],
        category_id=cid,
        category_name=cat.get("name", ""),
        category_icon=cat.get("icon", ""),
        category_color=cat.get("color", ""),
        amount=limit_amount,
        period=row.get("period", "mensal"),
        spent=spent,
        remaining=remaining,
        percentage=percentage,
    )


# ── GET /limits/ ──────────────────────────────────────────────────────────────

def list_limits(user_uuid: str, supabase: Client) -> LimitsListResponse:
    repo = LimitRepository(supabase)
    rows = repo.list_by_user(user_uuid)
    cat_map = repo.get_categories_map(user_uuid)
    month_start, month_end = _month_range()
    spent_map = TransactionRepository(supabase).spending_this_month(user_uuid, month_start, month_end)
    return LimitsListResponse(data=[_to_response(r, cat_map, spent_map) for r in rows])


# ── POST /limits/ ─────────────────────────────────────────────────────────────

def create_limit(user_uuid: str, data: LimitCreateRequest, supabase: Client) -> LimitResponse:
    repo = LimitRepository(supabase)

    # Validate category
    cat_repo = CategoryRepository(supabase)
    cat = cat_repo.get_by_id(user_uuid, data.category_id)
    if not cat:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Categoria não encontrada")

    # Check uniqueness
    existing = repo.get_by_category(user_uuid, data.category_id)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um limite para esta categoria")

    row = repo.create(user_uuid, data.category_id, data.amount)
    month_start, month_end = _month_range()
    spent_map = TransactionRepository(supabase).spending_this_month(user_uuid, month_start, month_end)
    cat_map = {data.category_id: cat}
    logger.info("limit_created", user_uuid=user_uuid, category_id=data.category_id)
    return _to_response(row, cat_map, spent_map)


# ── PUT /limits/{id} ──────────────────────────────────────────────────────────

def update_limit(user_uuid: str, limit_id: int, data: LimitUpdateRequest, supabase: Client) -> LimitResponse:
    repo = LimitRepository(supabase)
    existing = repo.get_by_id(user_uuid, limit_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Limite não encontrado")

    updated = repo.update(user_uuid, limit_id, data.amount)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Limite não encontrado")

    cat_map = repo.get_categories_map(user_uuid)
    month_start, month_end = _month_range()
    spent_map = TransactionRepository(supabase).spending_this_month(user_uuid, month_start, month_end)
    logger.info("limit_updated", user_uuid=user_uuid, limit_id=limit_id)
    return _to_response(updated, cat_map, spent_map)


# ── DELETE /limits/{id} ───────────────────────────────────────────────────────

def delete_limit(user_uuid: str, limit_id: int, supabase: Client) -> LimitDeleteResponse:
    repo = LimitRepository(supabase)
    existing = repo.get_by_id(user_uuid, limit_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Limite não encontrado")
    repo.delete(user_uuid, limit_id)
    logger.info("limit_deleted", user_uuid=user_uuid, limit_id=limit_id)
    return LimitDeleteResponse()
