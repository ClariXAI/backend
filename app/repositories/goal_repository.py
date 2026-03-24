from __future__ import annotations

from datetime import date

from app.repositories.base import BaseRepository

_TABLE = "goals"
_SELECT = "id, title, description, target_amount, current_amount, priority, target_date, monthly_contribution, is_completed, completed_at"


class GoalRepository(BaseRepository):

    # ── List ──────────────────────────────────────────────────────────────────

    def list_by_user(self, user_uuid: str, completed: bool | None = None) -> list[dict]:
        query = (
            self.supabase.table(_TABLE)
            .select(_SELECT)
            .eq("user_uuid", user_uuid)
        )
        if completed is not None:
            query = query.eq("is_completed", completed)
        response = query.order("created_at", desc=True).execute()
        return response.data or []

    def get_by_id(self, user_uuid: str, goal_id: int) -> dict | None:
        response = (
            self.supabase.table(_TABLE)
            .select(_SELECT)
            .eq("id", goal_id)
            .eq("user_uuid", user_uuid)
            .maybe_single()
            .execute()
        )
        return response.data or None

    # ── Create ────────────────────────────────────────────────────────────────

    def create(
        self,
        user_uuid: str,
        title: str,
        target_amount: float,
        priority: str,
        description: str | None = None,
        current_amount: float = 0.0,
        target_date: date | None = None,
        monthly_contribution: float | None = None,
    ) -> dict:
        row: dict = {
            "user_uuid": user_uuid,
            "title": title,
            "target_amount": target_amount,
            "current_amount": current_amount,
            "priority": priority,
        }
        if description is not None:
            row["description"] = description
        if target_date is not None:
            row["target_date"] = target_date.isoformat()
        if monthly_contribution is not None:
            row["monthly_contribution"] = monthly_contribution

        response = self.supabase.table(_TABLE).insert(row).execute()
        return response.data[0] if response.data else row

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, user_uuid: str, goal_id: int, fields: dict) -> dict | None:
        response = (
            self.supabase.table(_TABLE)
            .update(fields)
            .eq("id", goal_id)
            .eq("user_uuid", user_uuid)
            .execute()
        )
        return response.data[0] if response.data else None

    # ── Progress ──────────────────────────────────────────────────────────────

    def add_progress(self, user_uuid: str, goal_id: int, amount: float) -> dict | None:
        """
        Incrementa current_amount atomicamente via RPC do Supabase.
        Fallback: lê o valor atual e faz update.
        """
        existing = self.get_by_id(user_uuid, goal_id)
        if not existing:
            return None

        new_amount = round(float(existing["current_amount"]) + amount, 2)
        target = float(existing["target_amount"])
        fields: dict = {"current_amount": new_amount}

        if new_amount >= target and not existing["is_completed"]:
            from datetime import datetime, timezone
            fields["is_completed"] = True
            fields["completed_at"] = datetime.now(timezone.utc).isoformat()

        return self.update(user_uuid, goal_id, fields)

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete(self, user_uuid: str, goal_id: int) -> bool:
        response = (
            self.supabase.table(_TABLE)
            .delete()
            .eq("id", goal_id)
            .eq("user_uuid", user_uuid)
            .execute()
        )
        return bool(response.data)
