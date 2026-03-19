from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from fastapi import HTTPException, status
from supabase import Client

from app.repositories.onboarding_repository import OnboardingRepository
from app.repositories.user_plan_subscription_repository import UserPlanSubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.profile import (
    PaymentRecord,
    PaymentsResponse,
    PlanUpdateRequest,
    PlanUpdateResponse,
    ProfileResponse,
    ProfileUpdateRequest,
)

logger = structlog.get_logger()

# Planos válidos com seus IDs no banco
_VALID_PLANS = {"essential": 1, "premium": 2}

# Preços por plano e recorrência — fonte: tabela plans
_PLAN_PRICES: dict[str, dict[str, float]] = {
    "essential": {"mensal": 29.90, "anual": 19.90 * 12},
    "premium": {"mensal": 49.90, "anual": 39.90 * 12},
}

# Mapeamento de payment_method para exibição
_METHOD_DISPLAY = {"PIX": "PIX", "CARD": "Cartão de Crédito"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_cpf(cpf: str) -> str:
    """Formata CPF de dígitos brutos para 123.456.789-09."""
    if not cpf or len(cpf) != 11:
        return cpf
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def _build_profile_response(
    row: dict,
    billing_period: str | None,
    onboarding_completed: bool,
) -> ProfileResponse:
    plan_name: str
    if row.get("plan_id") and row.get("plans"):
        plan_name = row["plans"]["name"].lower()
    else:
        plan_name = "trial"

    tax_id = row.get("tax_id")

    return ProfileResponse(
        id=row["user_uuid"],
        name=row["name"],
        email=row["email"],
        cpf=_format_cpf(tax_id) if tax_id else None,
        phone=row.get("phone"),
        plan=plan_name,
        billing_period=billing_period,
        onboarding_completed=onboarding_completed,
        created_at=row["created_at"],
    )


# ── GET /profile/ ─────────────────────────────────────────────────────────────

def get_profile(user_uuid: str, supabase: Client) -> ProfileResponse:
    user_repo = UserRepository(supabase)
    plan_sub_repo = UserPlanSubscriptionRepository(supabase)
    onboarding_repo = OnboardingRepository(supabase)

    row = user_repo.get_profile(user_uuid)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil não encontrado",
        )

    # billing_period da assinatura ativa (null se trial)
    active_sub = plan_sub_repo.get_active(user_uuid)
    billing_period = active_sub["recurrence"] if active_sub else None

    onboarding_completed = onboarding_repo.is_completed(user_uuid)

    logger.info("profile_fetched", user_uuid=user_uuid)
    return _build_profile_response(row, billing_period, onboarding_completed)


# ── PUT /profile/ ─────────────────────────────────────────────────────────────

def update_profile(
    user_uuid: str,
    data: ProfileUpdateRequest,
    supabase: Client,
) -> ProfileResponse:
    user_repo = UserRepository(supabase)
    plan_sub_repo = UserPlanSubscriptionRepository(supabase)
    onboarding_repo = OnboardingRepository(supabase)

    fields: dict = {}
    if data.name is not None:
        fields["name"] = data.name.strip()
    if data.phone is not None:
        fields["phone"] = data.phone

    if not fields:
        # Nada enviado — retorna perfil atual
        return get_profile(user_uuid, supabase)

    updated = user_repo.update_profile(user_uuid, fields)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil não encontrado",
        )

    active_sub = plan_sub_repo.get_active(user_uuid)
    billing_period = active_sub["recurrence"] if active_sub else None
    onboarding_completed = onboarding_repo.is_completed(user_uuid)

    logger.info("profile_updated", user_uuid=user_uuid, fields=list(fields.keys()))
    return _build_profile_response(updated, billing_period, onboarding_completed)


# ── PUT /profile/plan ─────────────────────────────────────────────────────────

def update_plan(
    user_uuid: str,
    data: PlanUpdateRequest,
    supabase: Client,
) -> PlanUpdateResponse:
    plan_id = _VALID_PLANS.get(data.plan)
    if not plan_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plano inválido. Opções: essential, premium",
        )

    price = _PLAN_PRICES[data.plan][data.billing_period]

    now = datetime.now(timezone.utc)
    if data.billing_period == "mensal":
        ends_at = now + timedelta(days=30)
    else:
        ends_at = now + timedelta(days=365)

    plan_sub_repo = UserPlanSubscriptionRepository(supabase)
    user_repo = UserRepository(supabase)

    # Cria registro de assinatura (status=pending até confirmação de pagamento)
    plan_sub_repo.create(
        user_uuid=user_uuid,
        plan_id=plan_id,
        recurrence=data.billing_period,
        amount_paid=price,
        starts_at=now,
        ends_at=ends_at,
        status="pending",
    )

    # Atualiza plan_id e plan_status no usuário (otimista)
    user_repo.update_plan_id(user_uuid, plan_id)

    logger.info("plan_updated", user_uuid=user_uuid, plan=data.plan, billing_period=data.billing_period)

    return PlanUpdateResponse(
        plan=data.plan,
        billing_period=data.billing_period,
        price=round(price, 2),
        next_billing_date=ends_at,
    )


# ── GET /profile/payments ─────────────────────────────────────────────────────

def get_payments(
    user_uuid: str,
    page: int,
    limit: int,
    supabase: Client,
) -> PaymentsResponse:
    repo = UserPlanSubscriptionRepository(supabase)
    rows, total = repo.list_by_user(user_uuid, page=page, limit=limit)

    records = [
        PaymentRecord(
            id=row["id"],
            date=row["starts_at"],
            amount=row.get("amount_paid"),
            status=row["status"],
            method=_METHOD_DISPLAY.get(row.get("payment_method", ""), row.get("payment_method")),
            invoice=row.get("abacatepay_charge_id"),
        )
        for row in rows
    ]

    return PaymentsResponse(data=records, total=total, page=page, limit=limit)
