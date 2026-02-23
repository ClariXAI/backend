from app.repositories.base import BaseRepository

_TABLE = "onboarding"


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
