from app.repositories.base import BaseRepository

_TABLE = "users"

# Fixed defaults applied on every new user
_DEFAULT_PLAN_ID = 1        # Essencial
_DEFAULT_RECURRENCE_ID = 3  # Mensal
_DEFAULT_STATUS_ID = 1      # Teste


class UserRepository(BaseRepository):
    def email_exists(self, email: str) -> bool:
        response = (
            self.supabase.table(_TABLE)
            .select("id")
            .eq("email", email)
            .execute()
        )
        return bool(response.data)

    def create(
        self,
        uuid: str,
        name: str,
        email: str,
        phone: str | None,
        tax_id: str | None,
        active_bot: bool,
    ) -> dict:
        response = (
            self.supabase.table(_TABLE)
            .insert(
                {
                    "uuid": uuid,
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "tax_id": tax_id,
                    "active_bot": active_bot,
                    "plan_id": _DEFAULT_PLAN_ID,
                    "recurrence_id": _DEFAULT_RECURRENCE_ID,
                    "user_status_id": _DEFAULT_STATUS_ID,
                }
            )
            .execute()
        )
        return response.data[0] if response.data else {}

    def update_customer_id(self, uuid: str, customer_id: str) -> None:
        (
            self.supabase.table(_TABLE)
            .update({"customer_id": customer_id})
            .eq("uuid", uuid)
            .execute()
        )
