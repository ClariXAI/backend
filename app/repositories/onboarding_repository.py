from app.repositories.base import BaseRepository

_TABLE = "onboarding"

_SELECT_FIELDS = (
    "income, monthly_cost, selected_categories, suggested_limits, "
    "has_emergency_fund, emergency_fund_amount, next_goal, commitment, "
    "current_step, completed"
)


class OnboardingRepository(BaseRepository):
    def is_completed(self, user_uuid: str) -> bool:
        """Return True only when a row with completed=True exists for this user."""
        response = (
            self.supabase.table(_TABLE)
            .select("id")
            .eq("user_uuid", user_uuid)
            .eq("completed", True)
            .execute()
        )
        return bool(response.data)

    def get_by_user_uuid(self, user_uuid: str) -> dict | None:
        """Return the onboarding row for the given user, or None if not found."""
        response = (
            self.supabase.table(_TABLE)
            .select(_SELECT_FIELDS)
            .eq("user_uuid", user_uuid)
            .execute()
        )
        return response.data[0] if response.data else None
