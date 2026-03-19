from __future__ import annotations

from datetime import date

from app.repositories.base import BaseRepository

_TABLE = "subscriptions"


class SubscriptionRepository(BaseRepository):

    def create(
        self,
        user_uuid: str,
        title: str,
        value: float,
        plan: str,
        due_date: date,
        category_id: int | None = None,
    ) -> dict:
        row: dict = {
            "user_uuid": user_uuid,
            "title": title,
            "value": value,
            "plan": plan,
            "due_date": due_date.isoformat(),
        }
        if category_id is not None:
            row["category_id"] = category_id

        response = self.supabase.table(_TABLE).insert(row).execute()
        if response.data:
            return response.data[0]
        return row
