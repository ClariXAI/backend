from __future__ import annotations

from datetime import datetime

from app.repositories.base import BaseRepository

_TABLE = "users"


class UserRepository(BaseRepository):

    def email_exists(self, email: str) -> bool:
        response = (
            self.supabase.table(_TABLE)
            .select("id")
            .eq("email", email)
            .execute()
        )
        return bool(response.data)

    def phone_exists(self, phone: str) -> bool:
        response = (
            self.supabase.table(_TABLE)
            .select("id")
            .eq("phone", phone)
            .execute()
        )
        return bool(response.data)

    def create(
        self,
        user_uuid: str,
        name: str,
        email: str,
        phone: str | None,
        tax_id: str | None,
        trial_starts_at: datetime,
        trial_ends_at: datetime,
    ) -> dict:
        response = (
            self.supabase.table(_TABLE)
            .insert({
                "user_uuid": user_uuid,
                "name": name,
                "email": email,
                "phone": phone,
                "tax_id": tax_id,
                "plan_status": "trial",
                "trial_starts_at": trial_starts_at.isoformat(),
                "trial_ends_at": trial_ends_at.isoformat(),
            })
            .execute()
        )
        return response.data[0] if response.data else {}

    def get_by_uuid(self, user_uuid: str) -> dict | None:
        response = (
            self.supabase.table(_TABLE)
            .select("user_uuid, name, email, plan_status, trial_starts_at, trial_ends_at")
            .eq("user_uuid", user_uuid)
            .maybe_single()
            .execute()
        )
        return response.data or None

    def update_plan_status(self, user_uuid: str, plan_status: str) -> None:
        (
            self.supabase.table(_TABLE)
            .update({"plan_status": plan_status})
            .eq("user_uuid", user_uuid)
            .execute()
        )

    def update_customer_id(self, user_uuid: str, customer_id: str) -> None:
        (
            self.supabase.table(_TABLE)
            .update({"customer_id": customer_id})
            .eq("user_uuid", user_uuid)
            .execute()
        )

    def get_profile(self, user_uuid: str) -> dict | None:
        """Retorna perfil completo com JOIN em plans."""
        response = (
            self.supabase.table(_TABLE)
            .select("user_uuid, name, email, phone, tax_id, plan_id, plan_status, created_at, plans(name)")
            .eq("user_uuid", user_uuid)
            .maybe_single()
            .execute()
        )
        return response.data or None

    def update_profile(self, user_uuid: str, fields: dict) -> dict | None:
        """Atualiza campos de perfil. Retorna o registro atualizado."""
        response = (
            self.supabase.table(_TABLE)
            .update(fields)
            .eq("user_uuid", user_uuid)
            .execute()
        )
        if response.data:
            return response.data[0]
        return self.get_profile(user_uuid)

    def update_plan_id(self, user_uuid: str, plan_id: int) -> None:
        (
            self.supabase.table(_TABLE)
            .update({"plan_id": plan_id, "plan_status": "active"})
            .eq("user_uuid", user_uuid)
            .execute()
        )
