from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.core.dependencies import UserContext, get_current_user, get_supabase_client
from app.schemas.category import (
    CategoriesListResponse,
    CategoryCreateRequest,
    CategoryDeleteResponse,
    CategoryResponse,
    CategoryUpdateRequest,
)
from app.services import category_service

router = APIRouter()


@router.get("/", response_model=CategoriesListResponse)
def list_categories(
    type: Annotated[str | None, Query(description="Filtrar por tipo: fixa, variavel")] = None,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> CategoriesListResponse:
    return category_service.list_categories(current_user.user_id, type, supabase)


@router.post("/", response_model=CategoryResponse, status_code=201)
def create_category(
    data: CategoryCreateRequest,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> CategoryResponse:
    return category_service.create_category(current_user.user_id, data, supabase)


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    data: CategoryUpdateRequest,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> CategoryResponse:
    return category_service.update_category(current_user.user_id, category_id, data, supabase)


@router.delete("/{category_id}", response_model=CategoryDeleteResponse)
def delete_category(
    category_id: int,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> CategoryDeleteResponse:
    return category_service.delete_category(current_user.user_id, category_id, supabase)
