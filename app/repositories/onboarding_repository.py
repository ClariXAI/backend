from __future__ import annotations

from datetime import datetime, timezone

from app.repositories.base import BaseRepository

_TABLE = "onboarding"


class OnboardingRepository(BaseRepository):

    def create(self, user_uuid: str) -> None:
        self.supabase.table(_TABLE).insert({
            "user_uuid": user_uuid,
            "current_step": 1,
            "completed": False,
        }).execute()

    def is_completed(self, user_uuid: str) -> bool:
        response = (
            self.supabase.table(_TABLE)
            .select("completed")
            .eq("user_uuid", user_uuid)
            .maybe_single()
            .execute()
        )
        if not response.data:
            return False
        return bool(response.data.get("completed"))

    def get(self, user_uuid: str) -> dict | None:
        response = (
            self.supabase.table(_TABLE)
            .select("*")
            .eq("user_uuid", user_uuid)
            .maybe_single()
            .execute()
        )
        return response.data or None

    def upsert(self, user_uuid: str, fields: dict) -> dict:
        """Atualiza campos do onboarding. Retorna o registro atualizado."""
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        response = (
            self.supabase.table(_TABLE)
            .update(fields)
            .eq("user_uuid", user_uuid)
            .execute()
        )
        if response.data:
            return response.data[0]
        # fallback: retorna o registro atual
        return self.get(user_uuid) or {}

    def mark_complete(self, user_uuid: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.supabase.table(_TABLE).update({
            "completed": True,
            "completed_at": now,
            "updated_at": now,
        }).eq("user_uuid", user_uuid).execute()
