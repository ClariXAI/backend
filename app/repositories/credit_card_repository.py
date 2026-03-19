from __future__ import annotations

from app.repositories.base import BaseRepository

_TABLE = "credit_cards"


class CreditCardRepository(BaseRepository):

    def create(
        self,
        user_uuid: str,
        name: str,
        bank: str,
        total_limit: float,
        closing_day: int,
        due_day: int,
    ) -> dict:
        row = {
            "user_uuid": user_uuid,
            "name": name,
            "bank": bank,
            "total_limit": total_limit,
            "closing_day": closing_day,
            "due_day": due_day,
        }
        response = self.supabase.table(_TABLE).insert(row).execute()
        if response.data:
            return response.data[0]
        return row
