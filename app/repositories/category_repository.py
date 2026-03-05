from app.repositories.base import BaseRepository

_TABLE = "categories"


class CategoryRepository(BaseRepository):
    def create(self, user_uuid: str, name: str) -> dict:
        response = (
            self.supabase.table(_TABLE)
            .insert({"user_uuid": user_uuid, "name": name})
            .execute()
        )
        return response.data[0]
