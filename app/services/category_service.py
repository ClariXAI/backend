from __future__ import annotations

import structlog
from fastapi import HTTPException, status
from supabase import Client

from app.repositories.category_repository import CategoryRepository
from app.schemas.category import (
    CategoriesListResponse,
    CategoryCreateRequest,
    CategoryDeleteResponse,
    CategoryResponse,
    CategoryUpdateRequest,
)

logger = structlog.get_logger()


def _to_response(row: dict, stats: dict[int, dict] | None = None) -> CategoryResponse:
    cid = row["id"]
    stat = (stats or {}).get(cid, {})
    return CategoryResponse(
        id=cid,
        name=row["name"],
        icon=row.get("icon") or "",
        color=row["color"],
        type=row["type"],
        transaction_count=stat.get("count", 0),
        total_amount=round(stat.get("total", 0.0), 2),
    )


# ── GET /categories/ ──────────────────────────────────────────────────────────

def list_categories(
    user_uuid: str,
    type_filter: str | None,
    supabase: Client,
) -> CategoriesListResponse:
    repo = CategoryRepository(supabase)
    rows = repo.list_by_user(user_uuid, type_filter)
    stats = repo.get_transaction_stats(user_uuid)
    return CategoriesListResponse(data=[_to_response(r, stats) for r in rows])


# ── POST /categories/ ─────────────────────────────────────────────────────────

def create_category(
    user_uuid: str,
    data: CategoryCreateRequest,
    supabase: Client,
) -> CategoryResponse:
    repo = CategoryRepository(supabase)

    if repo.name_exists(user_uuid, data.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Categoria com este nome já existe",
        )

    row = repo.create(
        user_uuid=user_uuid,
        name=data.name.strip(),
        icon=data.icon.strip(),
        color=data.color.strip(),
        type=data.type,
    )

    logger.info("category_created", user_uuid=user_uuid, name=data.name)
    return _to_response(row)


# ── PUT /categories/{id} ──────────────────────────────────────────────────────

def update_category(
    user_uuid: str,
    category_id: int,
    data: CategoryUpdateRequest,
    supabase: Client,
) -> CategoryResponse:
    repo = CategoryRepository(supabase)

    existing = repo.get_by_id(user_uuid, category_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada",
        )

    fields: dict = {}
    if data.name is not None:
        name = data.name.strip()
        if repo.name_exists(user_uuid, name, exclude_id=category_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Categoria com este nome já existe",
            )
        fields["name"] = name
    if data.icon is not None:
        fields["icon"] = data.icon.strip()
    if data.color is not None:
        fields["color"] = data.color.strip()
    if data.type is not None:
        fields["type"] = data.type

    if not fields:
        stats = repo.get_transaction_stats(user_uuid)
        return _to_response(existing, stats)

    updated = repo.update(user_uuid, category_id, fields)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada",
        )

    stats = repo.get_transaction_stats(user_uuid)
    logger.info("category_updated", user_uuid=user_uuid, category_id=category_id)
    return _to_response(updated, stats)


# ── DELETE /categories/{id} ───────────────────────────────────────────────────

def delete_category(
    user_uuid: str,
    category_id: int,
    supabase: Client,
) -> CategoryDeleteResponse:
    repo = CategoryRepository(supabase)

    existing = repo.get_by_id(user_uuid, category_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada",
        )

    repo.delete(user_uuid, category_id)

    logger.info("category_deleted", user_uuid=user_uuid, category_id=category_id)
    return CategoryDeleteResponse()
