from __future__ import annotations

from datetime import datetime

from app.repositories.base import BaseRepository

_TABLE = "user_plan_subscriptions"


class UserPlanSubscriptionRepository(BaseRepository):

    def get_active(self, user_uuid: str) -> dict | None:
        """Retorna a assinatura de plano ativa mais recente do usuário."""
        response = (
            self.supabase.table(_TABLE)
            .select("id, plan_id, recurrence, status, amount_paid, payment_method, abacatepay_charge_id, starts_at, ends_at")
            .eq("user_uuid", user_uuid)
            .eq("status", "active")
            .order("starts_at", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        return response.data or None

    def create(
        self,
        user_uuid: str,
        plan_id: int,
        recurrence: str,
        amount_paid: float,
        starts_at: datetime,
        ends_at: datetime,
        status: str = "pending",
        payment_method: str | None = None,
        abacatepay_charge_id: str | None = None,
        abacatepay_billing_id: str | None = None,
    ) -> dict:
        row: dict = {
            "user_uuid": user_uuid,
            "plan_id": plan_id,
            "recurrence": recurrence,
            "amount_paid": amount_paid,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "status": status,
        }
        if payment_method is not None:
            row["payment_method"] = payment_method
        if abacatepay_charge_id is not None:
            row["abacatepay_charge_id"] = abacatepay_charge_id
        if abacatepay_billing_id is not None:
            row["abacatepay_billing_id"] = abacatepay_billing_id

        response = self.supabase.table(_TABLE).insert(row).execute()
        if response.data:
            return response.data[0]
        return row

    def list_by_user(
        self,
        user_uuid: str,
        page: int = 1,
        limit: int = 10,
    ) -> tuple[list[dict], int]:
        """Retorna pagina de pagamentos e total de registros."""
        offset = (page - 1) * limit

        # total
        count_response = (
            self.supabase.table(_TABLE)
            .select("id", count="exact")
            .eq("user_uuid", user_uuid)
            .execute()
        )
        total = count_response.count or 0

        # dados
        data_response = (
            self.supabase.table(_TABLE)
            .select("id, starts_at, amount_paid, status, payment_method, abacatepay_charge_id")
            .eq("user_uuid", user_uuid)
            .order("starts_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return data_response.data or [], total
