from app.repositories.base import BaseRepository

_TABLE = "consortia"


class ConsortiaRepository(BaseRepository):
    def create(
        self,
        user_uuid: str,
        name: str,
        administrator: str | None = None,
        total_number_of_installments: int | None = None,
        installment_amount: float | None = None,
        due_day: int | None = None,
    ) -> dict:
        response = (
            self.supabase.table(_TABLE)
            .insert({
                "user_uuid": user_uuid,
                "name": name,
                "administrator": administrator,
                "total_number_of_installments": total_number_of_installments,
                "installment_amount": int(installment_amount) if installment_amount is not None else None,
                "due_day": due_day,
                "contemplated": False,
            })
            .execute()
        )
        return response.data[0]
