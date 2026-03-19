from __future__ import annotations

from app.repositories.base import BaseRepository

_TABLE = "categories"
_TRANSACTIONS_TABLE = "transactions"


class CategoryRepository(BaseRepository):

    # ── Onboarding helper ─────────────────────────────────────────────────────

    def bulk_create(self, user_uuid: str, categories: list[dict]) -> list[dict]:
        """Insere múltiplas categorias. Cada item: {name, type, icon?, color?}."""
        rows = [{"user_uuid": user_uuid, **cat} for cat in categories]
        response = self.supabase.table(_TABLE).insert(rows).execute()
        return response.data or []

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def list_by_user(
        self,
        user_uuid: str,
        type_filter: str | None = None,
    ) -> list[dict]:
        query = (
            self.supabase.table(_TABLE)
            .select("id, name, icon, color, type")
            .eq("user_uuid", user_uuid)
        )
        if type_filter:
            query = query.eq("type", type_filter)
        response = query.order("name").execute()
        return response.data or []

    def get_by_id(self, user_uuid: str, category_id: int) -> dict | None:
        response = (
            self.supabase.table(_TABLE)
            .select("id, name, icon, color, type")
            .eq("id", category_id)
            .eq("user_uuid", user_uuid)
            .maybe_single()
            .execute()
        )
        return response.data or None

    def name_exists(self, user_uuid: str, name: str, exclude_id: int | None = None) -> bool:
        query = (
            self.supabase.table(_TABLE)
            .select("id")
            .eq("user_uuid", user_uuid)
            .ilike("name", name)
        )
        if exclude_id is not None:
            query = query.neq("id", exclude_id)
        response = query.execute()
        return bool(response.data)

    def create(
        self,
        user_uuid: str,
        name: str,
        icon: str,
        color: str,
        type: str,
    ) -> dict:
        response = (
            self.supabase.table(_TABLE)
            .insert({
                "user_uuid": user_uuid,
                "name": name,
                "icon": icon,
                "color": color,
                "type": type,
            })
            .execute()
        )
        return response.data[0] if response.data else {}

    def update(self, user_uuid: str, category_id: int, fields: dict) -> dict | None:
        response = (
            self.supabase.table(_TABLE)
            .update(fields)
            .eq("id", category_id)
            .eq("user_uuid", user_uuid)
            .execute()
        )
        return response.data[0] if response.data else None

    def delete(self, user_uuid: str, category_id: int) -> bool:
        response = (
            self.supabase.table(_TABLE)
            .delete()
            .eq("id", category_id)
            .eq("user_uuid", user_uuid)
            .execute()
        )
        return bool(response.data)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_transaction_stats(self, user_uuid: str) -> dict[int, dict]:
        """
        Retorna {category_id: {count, total}} para todas as categorias do usuário.
        Usa uma query na tabela transactions agrupada por category_id.
        """
        try:
            response = (
                self.supabase.table(_TRANSACTIONS_TABLE)
                .select("category_id, amount")
                .eq("user_uuid", user_uuid)
                .not_.is_("category_id", "null")
                .execute()
            )
        except Exception:
            return {}

        stats: dict[int, dict] = {}
        for row in response.data or []:
            cid = row.get("category_id")
            if cid is None:
                continue
            if cid not in stats:
                stats[cid] = {"count": 0, "total": 0.0}
            stats[cid]["count"] += 1
            stats[cid]["total"] += float(row.get("amount") or 0)

        return stats

    # ── get_by_user (retro-compat onboarding) ─────────────────────────────────

    def get_by_user(self, user_uuid: str) -> list[dict]:
        return self.list_by_user(user_uuid)
