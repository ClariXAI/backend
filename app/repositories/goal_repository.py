from app.repositories.base import BaseRepository

_TABLE = "goals"

PRIORITY_ALTA = 1
PRIORITY_MEDIA = 2
PRIORITY_BAIXA = 3


class GoalRepository(BaseRepository):
    def create(
        self,
        user_uuid: str,
        name: str,
        description: str | None,
        target_value: float,
        priority_id: int,
        target_date: str | None = None,
        monthly_contribution: float | None = None,
        current_value: float = 0,
    ) -> dict:
        data: dict = {
            "user_uuid": user_uuid,
            "name": name,
            "description": description,
            "target_value": int(target_value),
            "current_value": int(current_value),
            "priority_id": priority_id,
        }
        if target_date:
            data["target_date"] = str(target_date)
        if monthly_contribution is not None:
            data["monthly_contribution"] = int(monthly_contribution)

        response = self.supabase.table(_TABLE).insert(data).execute()
        return response.data[0]
