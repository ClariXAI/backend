from app.repositories.base import BaseRepository

_TABLE = "signature"


class SignatureRepository(BaseRepository):
    def _get_recurrence_id(self, plan_name: str) -> int | None:
        response = (
            self.supabase.table("recurrence")
            .select("id")
            .ilike("name", f"%{plan_name}%")
            .limit(1)
            .execute()
        )
        return response.data[0]["id"] if response.data else None

    def create(
        self,
        user_uuid: str,
        name: str,
        value: float | None,
        plan: str | None,
        date_of_signature: str | None = None,
    ) -> dict:
        recurrence_id = self._get_recurrence_id(plan) if plan else None
        data: dict = {
            "user_uuid": user_uuid,
            "name": name,
            "value": int(value) if value is not None else None,
            "recurrence_id": recurrence_id,
        }
        if date_of_signature:
            data["date_of_signature"] = str(date_of_signature)

        response = self.supabase.table(_TABLE).insert(data).execute()
        return response.data[0]
