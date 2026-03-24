from __future__ import annotations

from app.repositories.base import BaseRepository

_TABLE = "spending_limits"
_CATEGORIES_TABLE = "categories"


class LimitRepository(BaseRepository):

    # ── Onboarding bulk create ─────────────────────────────────────────────────

    def bulk_create(self, user_uuid: str, limits: list[dict]) -> list[dict]:
        rows = [{"user_uuid": user_uuid, **lim} for lim in limits]
        response = self.supabase.table(_TABLE).insert(rows).execute()
        return response.data or []

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def list_by_user(self, user_uuid: str) -> list[dict]:
        response = (
            self.supabase.table(_TABLE)
            .select("id, category_id, amount, period")
            .eq("user_uuid", user_uuid)
            .order("id")
            .execute()
        )
        return response.data or []

    def get_by_id(self, user_uuid: str, limit_id: int) -> dict | None:
        response = (
            self.supabase.table(_TABLE)
            .select("id, category_id, amount, period")
            .eq("id", limit_id)
            .eq("user_uuid", user_uuid)
            .maybe_single()
            .execute()
        )
        return response.data or None

    def get_by_category(self, user_uuid: str, category_id: int) -> dict | None:
        response = (
            self.supabase.table(_TABLE)
            .select("id, category_id, amount, period")
            .eq("user_uuid", user_uuid)
            .eq("category_id", category_id)
            .maybe_single()
            .execute()
        )
        return response.data or None

    def create(self, user_uuid: str, category_id: int, amount: float) -> dict:
        response = (
            self.supabase.table(_TABLE)
            .insert({"user_uuid": user_uuid, "category_id": category_id, "amount": amount, "period": "mensal"})
            .execute()
        )
        return response.data[0] if response.data else {}

    def update(self, user_uuid: str, limit_id: int, amount: float) -> dict | None:
        response = (
            self.supabase.table(_TABLE)
            .update({"amount": amount})
            .eq("id", limit_id)
            .eq("user_uuid", user_uuid)
            .execute()
        )
        return response.data[0] if response.data else None

    def delete(self, user_uuid: str, limit_id: int) -> bool:
        response = (
            self.supabase.table(_TABLE)
            .delete()
            .eq("id", limit_id)
            .eq("user_uuid", user_uuid)
            .execute()
        )
        return bool(response.data)

    def get_categories_map(self, user_uuid: str) -> dict[int, dict]:
        response = (
            self.supabase.table(_CATEGORIES_TABLE)
            .select("id, name, icon, color")
            .eq("user_uuid", user_uuid)
            .execute()
        )
        return {r["id"]: r for r in (response.data or [])}
