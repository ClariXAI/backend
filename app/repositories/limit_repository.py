from __future__ import annotations

from app.repositories.base import BaseRepository

_TABLE = "spending_limits"


class LimitRepository(BaseRepository):

    def bulk_create(
        self,
        user_uuid: str,
        limits: list[dict],
    ) -> list[dict]:
        """
        Insere limites de gasto em lote.
        Cada item: {"category_id": int, "amount": float, "month_year": "2026-03"}
        Retorna os registros criados.
        """
        rows = [{"user_uuid": user_uuid, **lim} for lim in limits]
        response = self.supabase.table(_TABLE).insert(rows).execute()
        return response.data or []
