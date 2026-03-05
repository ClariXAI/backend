from app.repositories.base import BaseRepository

_TABLE = "limits"


class LimitRepository(BaseRepository):
    def create(self, user_uuid: str, category_id: int, value: float) -> dict:
        response = (
            self.supabase.table(_TABLE)
            .insert({
                "user_uuid": user_uuid,
                "category_id": category_id,
                "value": int(value),
                "alert_in": 80,
            })
            .execute()
        )
        return response.data[0]
