from __future__ import annotations

from datetime import date

from app.repositories.base import BaseRepository

_TABLE = "consortiums"


class ConsortiumRepository(BaseRepository):

    def create(
        self,
        user_uuid: str,
        administrator: str,
        total_amount: float,
        installments: int,
        monthly_payment: float,
        start_date: date,
        category_id: int | None = None,
    ) -> dict:
        row: dict = {
            "user_uuid": user_uuid,
            "administrator": administrator,
            "total_amount": total_amount,
            "installments": installments,
            "monthly_payment": monthly_payment,
            "start_date": start_date.isoformat(),
        }
        if category_id is not None:
            row["category_id"] = category_id

        response = self.supabase.table(_TABLE).insert(row).execute()
        if response.data:
            return response.data[0]
        return row
