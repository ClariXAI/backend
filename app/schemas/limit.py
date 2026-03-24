from __future__ import annotations

from pydantic import BaseModel, Field


class LimitCreateRequest(BaseModel):
    category_id: int
    amount: float = Field(gt=0)


class LimitUpdateRequest(BaseModel):
    amount: float = Field(gt=0)


class LimitResponse(BaseModel):
    id: int
    category_id: int
    category_name: str = ""
    category_icon: str = ""
    category_color: str = ""
    amount: float
    period: str
    spent: float = 0.0
    remaining: float = 0.0
    percentage: float = 0.0


class LimitsListResponse(BaseModel):
    data: list[LimitResponse]


class LimitDeleteResponse(BaseModel):
    message: str = "Limite removido com sucesso"
