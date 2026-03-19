from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon: str = Field(min_length=1)
    color: str = Field(min_length=1)
    type: Literal["fixa", "variavel"]


class CategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    icon: str | None = None
    color: str | None = None
    type: Literal["fixa", "variavel"] | None = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    icon: str
    color: str
    type: str
    transaction_count: int = 0
    total_amount: float = 0


class CategoriesListResponse(BaseModel):
    data: list[CategoryResponse]


class CategoryDeleteResponse(BaseModel):
    message: str = "Categoria removida com sucesso"
