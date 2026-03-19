from __future__ import annotations

from datetime import date

from app.repositories.base import BaseRepository

_TABLE = "goals"


class GoalRepository(BaseRepository):

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
        if response.data:
            return response.data[0]
        return row
