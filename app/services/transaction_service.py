from __future__ import annotations

from datetime import date

import structlog
from fastapi import HTTPException, status
from supabase import Client

from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import (
    TransactionCreateRequest,
    TransactionDeleteResponse,
    TransactionResponse,
    TransactionSummary,
    TransactionUpdateRequest,
    TransactionsListResponse,
)

logger = structlog.get_logger()


def _to_response(row: dict, cat_map: dict[int, dict]) -> TransactionResponse:
    cid = row.get("category_id")
    cat = cat_map.get(cid, {}) if cid else {}
    return TransactionResponse(
        id=row["id"],
        category_id=cid or 0,
        category_name=cat.get("name", ""),
        category_icon=cat.get("icon", ""),
        category_color=cat.get("color", ""),
        description=row["description"],
        amount=float(row["amount"]),
        date=row["date"],
        type=row["type"],
        notes=row.get("notes"),
        payment_method=row.get("payment_method"),
    )


# ── GET /transactions/ ────────────────────────────────────────────────────────

def list_transactions(
    user_uuid: str,
    type_filter: str | None,
    category_id: int | None,
    date_from: date | None,
    date_to: date | None,
    limit: int,
    offset: int,
    supabase: Client,
) -> TransactionsListResponse:
    repo = TransactionRepository(supabase)
    rows = repo.list_by_user(
        user_uuid, type_filter, category_id, date_from, date_to, limit, offset
    )
    total = repo.count_by_user(user_uuid, type_filter, category_id, date_from, date_to)
    cat_map = repo.get_categories_map(user_uuid)
    return TransactionsListResponse(
        data=[_to_response(r, cat_map) for r in rows],
        total=total,
    )


# ── GET /transactions/summary ─────────────────────────────────────────────────

def get_summary(
    user_uuid: str,
    date_from: date | None,
    date_to: date | None,
    supabase: Client,
) -> TransactionSummary:
    repo = TransactionRepository(supabase)
    s = repo.summary_by_user(user_uuid, date_from, date_to)
    return TransactionSummary(**s)


# ── GET /transactions/{id} ────────────────────────────────────────────────────

def get_transaction(
    user_uuid: str,
    transaction_id: int,
    supabase: Client,
) -> TransactionResponse:
    repo = TransactionRepository(supabase)
    row = repo.get_by_id(user_uuid, transaction_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada")
    cat_map = repo.get_categories_map(user_uuid)
    return _to_response(row, cat_map)


# ── POST /transactions/ ───────────────────────────────────────────────────────

def create_transaction(
    user_uuid: str,
    data: TransactionCreateRequest,
    supabase: Client,
) -> TransactionResponse:
    # Validate category belongs to user
    cat_repo = CategoryRepository(supabase)
    cat = cat_repo.get_by_id(user_uuid, data.category_id)
    if not cat:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Categoria não encontrada")

    repo = TransactionRepository(supabase)
    fields = {
        "category_id": data.category_id,
        "description": data.description.strip(),
        "amount": data.amount,
        "date": data.date.isoformat(),
        "type": data.type,
        "notes": data.notes,
        "payment_method": data.payment_method,
    }
    row = repo.create(user_uuid, fields)
    cat_map = {data.category_id: cat}
    logger.info("transaction_created", user_uuid=user_uuid, amount=data.amount, type=data.type)
    return _to_response(row, cat_map)


# ── PUT /transactions/{id} ────────────────────────────────────────────────────

def update_transaction(
    user_uuid: str,
    transaction_id: int,
    data: TransactionUpdateRequest,
    supabase: Client,
) -> TransactionResponse:
    repo = TransactionRepository(supabase)
    existing = repo.get_by_id(user_uuid, transaction_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada")

    fields: dict = {}
    if data.category_id is not None:
        cat_repo = CategoryRepository(supabase)
        cat = cat_repo.get_by_id(user_uuid, data.category_id)
        if not cat:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Categoria não encontrada")
        fields["category_id"] = data.category_id
    if data.description is not None:
        fields["description"] = data.description.strip()
    if data.amount is not None:
        fields["amount"] = data.amount
    if data.date is not None:
        fields["date"] = data.date.isoformat()
    if data.type is not None:
        fields["type"] = data.type
    if data.notes is not None:
        fields["notes"] = data.notes
    if data.payment_method is not None:
        fields["payment_method"] = data.payment_method

    if not fields:
        cat_map = repo.get_categories_map(user_uuid)
        return _to_response(existing, cat_map)

    updated = repo.update(user_uuid, transaction_id, fields)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada")

    cat_map = repo.get_categories_map(user_uuid)
    logger.info("transaction_updated", user_uuid=user_uuid, transaction_id=transaction_id)
    return _to_response(updated, cat_map)


# ── DELETE /transactions/{id} ─────────────────────────────────────────────────

def delete_transaction(
    user_uuid: str,
    transaction_id: int,
    supabase: Client,
) -> TransactionDeleteResponse:
    repo = TransactionRepository(supabase)
    existing = repo.get_by_id(user_uuid, transaction_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada")
    repo.delete(user_uuid, transaction_id)
    logger.info("transaction_deleted", user_uuid=user_uuid, transaction_id=transaction_id)
    return TransactionDeleteResponse()
