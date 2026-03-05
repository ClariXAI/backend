from app.repositories.base import BaseRepository

_TABLE = "credit_cards"


class CreditCardRepository(BaseRepository):
    def create(
        self,
        user_uuid: str,
        name: str,
        bank: str | None = None,
        total_limit: float | None = None,
        closing_day: int | None = None,
        due_day: int | None = None,
    ) -> dict:
        response = (
            self.supabase.table(_TABLE)
            .insert({
                "user_uuid": user_uuid,
                "name": name,
                "bank": bank,
                "total_limit": int(total_limit) if total_limit is not None else None,
                "closing_day": closing_day,
                "due_day": due_day,
            })
            .execute()
        )
        return response.data[0]
