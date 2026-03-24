from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class TransactionCreateRequest(BaseModel):
    category_id: int
    description: str = Field(min_length=1, max_length=255)
    amount: float = Field(gt=0)
    date: date
    type: Literal["entrada", "saida"]
    notes: str | None = None
    payment_method: Literal["dinheiro", "pix", "debito", "credito"] | None = None


class TransactionUpdateRequest(BaseModel):
    category_id: int | None = None
    description: str | None = Field(default=None, min_length=1, max_length=255)
    amount: float | None = Field(default=None, gt=0)
    date: date | None = None
    type: Literal["entrada", "saida"] | None = None
    notes: str | None = None
    payment_method: Literal["dinheiro", "pix", "debito", "credito"] | None = None


class TransactionResponse(BaseModel):
    id: int
    category_id: int
    category_name: str = ""
    category_icon: str = ""
    category_color: str = ""
    description: str
    amount: float
    date: date
    type: str
    notes: str | None = None
    payment_method: str | None = None


class TransactionSummary(BaseModel):
    total_entrada: float
    total_saida: float
    balance: float
    count: int


class TransactionsListResponse(BaseModel):
    data: list[TransactionResponse]
    total: int


class TransactionDeleteResponse(BaseModel):
    message: str = "Transação removida com sucesso"
