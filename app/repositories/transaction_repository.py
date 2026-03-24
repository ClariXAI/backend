from __future__ import annotations

from datetime import date

from app.repositories.base import BaseRepository

_TABLE = "transactions"
_CATEGORIES_TABLE = "categories"


class TransactionRepository(BaseRepository):

    # ── List ──────────────────────────────────────────────────────────────────

    def list_by_user(
        self,
        user_uuid: str,
        type_filter: str | None = None,
        category_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        query = (
            self.supabase.table(_TABLE)
            .select("id, category_id, description, amount, date, type, notes")
            .eq("user_uuid", user_uuid)
        )
        if type_filter:
            query = query.eq("type", type_filter)
        if category_id is not None:
            query = query.eq("category_id", category_id)
        if date_from:
            query = query.gte("date", date_from.isoformat())
        if date_to:
            query = query.lte("date", date_to.isoformat())
        response = (
            query
            .order("date", desc=True)
            .order("id", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return response.data or []

    def count_by_user(
        self,
        user_uuid: str,
        type_filter: str | None = None,
        category_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        query = (
            self.supabase.table(_TABLE)
            .select("id", count="exact")
            .eq("user_uuid", user_uuid)
        )
        if type_filter:
            query = query.eq("type", type_filter)
        if category_id is not None:
            query = query.eq("category_id", category_id)
        if date_from:
            query = query.gte("date", date_from.isoformat())
        if date_to:
            query = query.lte("date", date_to.isoformat())
        response = query.execute()
        return response.count or 0

    # ── Summary ───────────────────────────────────────────────────────────────

    def summary_by_user(
        self,
        user_uuid: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        query = (
            self.supabase.table(_TABLE)
            .select("type, amount")
            .eq("user_uuid", user_uuid)
        )
        if date_from:
            query = query.gte("date", date_from.isoformat())
        if date_to:
            query = query.lte("date", date_to.isoformat())
        response = query.execute()
        rows = response.data or []

        total_entrada = sum(float(r["amount"]) for r in rows if r["type"] == "entrada")
        total_saida = sum(float(r["amount"]) for r in rows if r["type"] == "saida")
        return {
            "total_entrada": round(total_entrada, 2),
            "total_saida": round(total_saida, 2),
            "balance": round(total_entrada - total_saida, 2),
            "count": len(rows),
        }

    # ── Single ────────────────────────────────────────────────────────────────

    def get_by_id(self, user_uuid: str, transaction_id: int) -> dict | None:
        response = (
            self.supabase.table(_TABLE)
            .select("id, category_id, description, amount, date, type, notes")
            .eq("id", transaction_id)
            .eq("user_uuid", user_uuid)
            .maybe_single()
            .execute()
        )
        return response.data or None

    # ── Create ────────────────────────────────────────────────────────────────

    def create(self, user_uuid: str, fields: dict) -> dict:
        payload = {"user_uuid": user_uuid, **fields}
        response = self.supabase.table(_TABLE).insert(payload).execute()
        return response.data[0] if response.data else {}

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, user_uuid: str, transaction_id: int, fields: dict) -> dict | None:
        response = (
            self.supabase.table(_TABLE)
            .update(fields)
            .eq("id", transaction_id)
            .eq("user_uuid", user_uuid)
            .execute()
        )
        return response.data[0] if response.data else None

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete(self, user_uuid: str, transaction_id: int) -> bool:
        response = (
            self.supabase.table(_TABLE)
            .delete()
            .eq("id", transaction_id)
            .eq("user_uuid", user_uuid)
            .execute()
        )
        return bool(response.data)

    # ── Category info helper ──────────────────────────────────────────────────

    def get_categories_map(self, user_uuid: str) -> dict[int, dict]:
        response = (
            self.supabase.table(_CATEGORIES_TABLE)
            .select("id, name, icon, color")
            .eq("user_uuid", user_uuid)
            .execute()
        )
        return {r["id"]: r for r in (response.data or [])}

    # ── Current month spending per category (for limits) ──────────────────────

    def spending_this_month(self, user_uuid: str, month_start: date, month_end: date) -> dict[int, float]:
        response = (
            self.supabase.table(_TABLE)
            .select("category_id, amount")
            .eq("user_uuid", user_uuid)
            .eq("type", "saida")
            .gte("date", month_start.isoformat())
            .lte("date", month_end.isoformat())
            .execute()
        )
        spent: dict[int, float] = {}
        for row in response.data or []:
            cid = row["category_id"]
            spent[cid] = spent.get(cid, 0.0) + float(row["amount"])
        return spent
