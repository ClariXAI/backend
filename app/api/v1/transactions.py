from __future__ import annotations

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.core.dependencies import UserContext, get_current_user, get_supabase_client
from app.schemas.transaction import (
    TransactionCreateRequest,
    TransactionDeleteResponse,
    TransactionResponse,
    TransactionSummary,
    TransactionUpdateRequest,
    TransactionsListResponse,
)
from app.services import transaction_service

router = APIRouter()


@router.get("/summary", response_model=TransactionSummary)
def get_summary(
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> TransactionSummary:
    return transaction_service.get_summary(current_user.user_id, date_from, date_to, supabase)


@router.get("/", response_model=TransactionsListResponse)
def list_transactions(
    type: Annotated[Optional[str], Query(description="entrada ou saida")] = None,
    category_id: Annotated[Optional[int], Query()] = None,
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> TransactionsListResponse:
    return transaction_service.list_transactions(
        current_user.user_id, type, category_id, date_from, date_to, limit, offset, supabase
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> TransactionResponse:
    return transaction_service.get_transaction(current_user.user_id, transaction_id, supabase)


@router.post("/", response_model=TransactionResponse, status_code=201)
def create_transaction(
    data: TransactionCreateRequest,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> TransactionResponse:
    return transaction_service.create_transaction(current_user.user_id, data, supabase)


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    data: TransactionUpdateRequest,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> TransactionResponse:
    return transaction_service.update_transaction(current_user.user_id, transaction_id, data, supabase)


@router.delete("/{transaction_id}", response_model=TransactionDeleteResponse)
def delete_transaction(
    transaction_id: int,
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> TransactionDeleteResponse:
    return transaction_service.delete_transaction(current_user.user_id, transaction_id, supabase)
