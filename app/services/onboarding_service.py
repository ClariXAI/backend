from __future__ import annotations

import math
from datetime import date, datetime, timezone

import structlog
from fastapi import HTTPException, status
from supabase import Client

from app.repositories.category_repository import CategoryRepository
from app.repositories.goal_repository import GoalRepository
from app.repositories.limit_repository import LimitRepository
from app.repositories.onboarding_repository import OnboardingRepository
from app.schemas.onboarding import (
    EmergencyFundGoalPreview,
    EmergencyFundRequest,
    EmergencyFundResponse,
    GoalCreatedSummary,
    NextGoalData,
    NextGoalRequest,
    NextGoalResponse,
    OnboardingCompleteResponse,
    OnboardingResponse,
    OnboardingSaveRequest,
)
from app.services import ai_service

logger = structlog.get_logger()

# ── Pesos por categoria (soma = 1.0) ──────────────────────────────────────────

_CATEGORY_WEIGHTS: dict[str, float] = {
    "alimentacao": 0.20,
    "agua": 0.03,
    "moradia": 0.30,
    "energia": 0.05,
    "internet": 0.04,
    "transporte": 0.10,
    "estudo": 0.05,
    "saude": 0.08,
    "entretenimento": 0.05,
    "lazer": 0.05,
}

# Categorias do tipo fixo (custo recorrente previsível)
_FIXED_CATEGORIES = {"moradia", "agua", "energia", "internet", "estudo"}

# Metas pré-definidas de próximo objetivo
_PRESET_GOALS: dict[str, dict] = {
    "viagem_europa": {
        "title": "Viagem Europa",
        "description": "Férias dos sonhos na Europa",
        "target_amount": 25000.0,
    },
    "entrada_apartamento": {
        "title": "Entrada de Apartamento",
        "description": "Entrada para compra do apartamento próprio",
        "target_amount": 50000.0,
    },
    "novo_notebook": {
        "title": "Novo Notebook",
        "description": "Equipamento para trabalho e estudos",
        "target_amount": 8000.0,
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _calculate_suggested_limits(income: float, categories: list[str]) -> dict[str, float]:
    """Calcula limites proporcionais à renda para as categorias selecionadas."""
    return {
        cat: round(income * _CATEGORY_WEIGHTS.get(cat, 0.05), 2)
        for cat in categories
    }


def _calculate_savings_contribution(income: float, monthly_cost: float) -> float:
    """Calcula aporte mensal disponível para poupança (30% da folga, mínimo 10% da renda)."""
    available = max(income - monthly_cost, 0)
    contribution = available * 0.30
    minimum = income * 0.10
    return max(round(contribution, 2), round(minimum, 2))


def _add_months(d: date, months: int) -> date:
    """Soma meses a uma data sem depender de bibliotecas externas."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
                       else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)


def _months_to_reach(target: float, contribution: float) -> int:
    if contribution <= 0:
        return 999
    return math.ceil(target / contribution)


def _map_db_to_response(row: dict, include_ef_preview: bool = False) -> OnboardingResponse:
    """Converte linha do DB para OnboardingResponse."""
    import json

    next_goal_raw = row.get("next_goal")
    next_goal = None
    if next_goal_raw:
        try:
            if isinstance(next_goal_raw, str):
                next_goal_raw = json.loads(next_goal_raw)
            next_goal = NextGoalData.model_validate(next_goal_raw)
        except Exception:
            pass

    return OnboardingResponse(
        income=row.get("monthly_income"),
        monthly_cost=row.get("monthly_cost"),
        selected_categories=row.get("selected_categories"),
        suggested_limits=row.get("suggested_limits"),
        has_emergency_fund=row.get("has_emergency_fund"),
        emergency_fund_amount=row.get("emergency_fund_amount"),
        next_goal=next_goal,
        current_step=row.get("current_step", 1),
        completed=bool(row.get("completed", False)),
    )


# ── GET /onboarding/ ──────────────────────────────────────────────────────────

def get_onboarding(user_uuid: str, supabase: Client) -> OnboardingResponse:
    repo = OnboardingRepository(supabase)
    row = repo.get(user_uuid)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding não iniciado",
        )
    return _map_db_to_response(row)


# ── POST /onboarding/ ─────────────────────────────────────────────────────────

def save_onboarding(
    user_uuid: str,
    data: OnboardingSaveRequest,
    supabase: Client,
) -> OnboardingResponse:
    repo = OnboardingRepository(supabase)

    # Garante que o registro existe
    existing = repo.get(user_uuid)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding não iniciado",
        )

    # Validações de negócio
    if data.income is not None and data.income <= 0:
        raise HTTPException(status_code=422, detail="Renda deve ser maior que zero")
    if data.monthly_cost is not None and data.monthly_cost <= 0:
        raise HTTPException(status_code=422, detail="Custo mensal deve ser maior que zero")

    # Monta campos para atualizar (apenas os enviados)
    fields: dict = {"current_step": data.current_step}

    if data.income is not None:
        fields["monthly_income"] = data.income
    if data.monthly_cost is not None:
        fields["monthly_cost"] = data.monthly_cost
    if data.selected_categories is not None:
        fields["selected_categories"] = data.selected_categories
    if data.has_emergency_fund is not None:
        fields["has_emergency_fund"] = data.has_emergency_fund
    if data.emergency_fund_amount is not None:
        fields["emergency_fund_amount"] = data.emergency_fund_amount
    if data.next_goal is not None:
        fields["next_goal"] = data.next_goal.model_dump(mode="json")

    # Calcula e persiste suggested_limits se tiver income + categorias
    income = data.income or existing.get("monthly_income")
    categories = data.selected_categories or existing.get("selected_categories") or []
    suggested_limits: dict | None = None
    if income and categories:
        suggested_limits = _calculate_suggested_limits(income, categories)
        fields["suggested_limits"] = suggested_limits

    updated = repo.upsert(user_uuid, fields)

    response = _map_db_to_response(updated)

    # Calcula preview da meta de reserva de emergência
    monthly_cost = data.monthly_cost or existing.get("monthly_cost")
    has_ef = data.has_emergency_fund if data.has_emergency_fund is not None else existing.get("has_emergency_fund")

    if income and monthly_cost and has_ef is False:
        target = round(monthly_cost * 6, 2)
        contribution = _calculate_savings_contribution(income, monthly_cost)
        months = _months_to_reach(target, contribution)
        target_date = _add_months(date.today(), months)
        response.emergency_fund_goal = EmergencyFundGoalPreview(
            title="Reserva de Emergência",
            target_amount=target,
            current_amount=0,
            priority="alta",
            target_date=target_date,
            monthly_contribution=contribution,
        )

    logger.info("onboarding_saved", user_uuid=user_uuid, step=data.current_step)
    return response


# ── PATCH /onboarding/complete ────────────────────────────────────────────────

def complete_onboarding(user_uuid: str, supabase: Client) -> OnboardingCompleteResponse:
    onboarding_repo = OnboardingRepository(supabase)

    row = onboarding_repo.get(user_uuid)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding não iniciado",
        )

    income = row.get("monthly_income")
    monthly_cost = row.get("monthly_cost")
    selected_categories = row.get("selected_categories") or []

    if not income or not monthly_cost or not selected_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dados de onboarding incompletos",
        )

    cat_repo = CategoryRepository(supabase)
    limit_repo = LimitRepository(supabase)
    goal_repo = GoalRepository(supabase)

    # 1. Criar categorias
    category_rows = [
        {
            "name": cat,
            "type": "fixa" if cat in _FIXED_CATEGORIES else "variavel",
        }
        for cat in selected_categories
    ]
    created_cats = cat_repo.bulk_create(user_uuid, category_rows)
    categories_created = len(created_cats)

    # 2. Criar limites (proporcional à renda)
    suggested_limits = row.get("suggested_limits") or _calculate_suggested_limits(income, selected_categories)

    cat_id_map: dict[str, int] = {c["name"]: c["id"] for c in created_cats if "id" in c and "name" in c}
    limit_rows = [
        {
            "category_id": cat_id_map[cat],
            "amount": suggested_limits.get(cat, round(income * 0.05, 2)),
        }
        for cat in selected_categories
        if cat in cat_id_map
    ]
    created_limits = limit_repo.bulk_create(user_uuid, limit_rows)
    limits_created = len(created_limits)

    # 3. Criar metas
    goals_created: list[GoalCreatedSummary] = []
    has_ef = row.get("has_emergency_fund")
    ef_amount = row.get("emergency_fund_amount")
    contribution = _calculate_savings_contribution(income, monthly_cost)

    if has_ef:
        # Usuário já tem reserva → meta com current_amount = valor informado
        target = ef_amount or round(monthly_cost * 6, 2)
        ef_goal = goal_repo.create(
            user_uuid=user_uuid,
            title="Reserva de Emergência",
            target_amount=target,
            current_amount=ef_amount or 0.0,
            priority="baixa",
        )
    else:
        # Usuário não tem reserva → meta = 6x custo mensal, prioridade alta
        target = round(monthly_cost * 6, 2)
        months = _months_to_reach(target, contribution)
        target_date = _add_months(date.today(), months)
        ef_goal = goal_repo.create(
            user_uuid=user_uuid,
            title="Reserva de Emergência",
            target_amount=target,
            current_amount=0.0,
            priority="alta",
            target_date=target_date,
            monthly_contribution=contribution,
        )

    goals_created.append(GoalCreatedSummary(
        title="Reserva de Emergência",
        target_amount=ef_goal.get("target_amount", target),
        current_amount=ef_goal.get("current_amount", 0),
        priority=ef_goal.get("priority", "alta"),
    ))

    # Próxima meta (se configurada)
    next_goal_raw = row.get("next_goal")
    if next_goal_raw:
        try:
            if isinstance(next_goal_raw, str):
                import json
                next_goal_raw = json.loads(next_goal_raw)
            ng = NextGoalData.model_validate(next_goal_raw)
            ng_months = _months_to_reach(ng.target_amount, contribution * 0.5)
            ng_target_date = ng.target_date or _add_months(date.today(), ng_months)
            ng_contribution = ng.monthly_contribution or round(contribution * 0.5, 2)
            ng_goal = goal_repo.create(
                user_uuid=user_uuid,
                title=ng.title,
                description=ng.description,
                target_amount=ng.target_amount,
                current_amount=0.0,
                priority=ng.priority,
                target_date=ng_target_date,
                monthly_contribution=ng_contribution,
            )
            goals_created.append(GoalCreatedSummary(
                title=ng.title,
                target_amount=ng_goal.get("target_amount", ng.target_amount),
                current_amount=0,
                priority=ng.priority,
            ))
        except Exception as exc:
            logger.error("next_goal_create_failed", user_uuid=user_uuid, error=str(exc))

    # 4. Marcar onboarding como concluído
    onboarding_repo.mark_complete(user_uuid)

    logger.info("onboarding_completed", user_uuid=user_uuid)

    return OnboardingCompleteResponse(
        completed=True,
        categories_created=categories_created,
        limits_created=limits_created,
        goals_created=goals_created,
    )


# ── GET /onboarding/suggested-limits ─────────────────────────────────────────

def get_suggested_limits(income: float, categories: list[str]) -> dict[str, float]:
    if income <= 0:
        raise HTTPException(status_code=422, detail="Renda deve ser maior que zero")
    if not categories:
        raise HTTPException(status_code=422, detail="Informe ao menos uma categoria")
    return _calculate_suggested_limits(income, categories)


# ── POST /onboarding/emergency-fund ──────────────────────────────────────────

def calculate_emergency_fund(
    data: EmergencyFundRequest,
    supabase: Client,  # noqa: ARG001  (mantido para consistência na assinatura)
) -> EmergencyFundResponse:
    if data.has_emergency_fund:
        # Usuário já tem reserva
        target = data.emergency_fund_amount or round(data.monthly_cost * 6, 2)
        current = data.emergency_fund_amount or 0.0
        suggestion = ai_service.get_emergency_fund_suggestion(
            target_amount=target,
            monthly_contribution=0,
            months=0,
            has_fund=True,
        )
        return EmergencyFundResponse(
            title="Reserva de Emergência",
            target_amount=target,
            current_amount=current,
            priority="baixa",
            ai_suggestion=suggestion,
        )

    # Usuário NÃO tem reserva
    target = round(data.monthly_cost * 6, 2)
    contribution = _calculate_savings_contribution(data.income, data.monthly_cost)
    months = _months_to_reach(target, contribution)
    target_date = _add_months(date.today(), months)

    suggestion = ai_service.get_emergency_fund_suggestion(
        target_amount=target,
        monthly_contribution=contribution,
        months=months,
        has_fund=False,
    )

    return EmergencyFundResponse(
        title="Reserva de Emergência",
        target_amount=target,
        current_amount=0,
        priority="alta",
        target_date=target_date,
        monthly_contribution=contribution,
        ai_suggestion=suggestion,
    )


# ── POST /onboarding/next-goal ────────────────────────────────────────────────

def calculate_next_goal(
    user_uuid: str,
    data: NextGoalRequest,
    supabase: Client,
) -> NextGoalResponse:
    # Valida que o usuário tem ou está criando uma reserva de emergência
    repo = OnboardingRepository(supabase)
    row = repo.get(user_uuid)
    if not row or not row.get("has_emergency_fund"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reserva de emergência não está completa. Etapa de próximo objetivo não disponível.",
        )

    if data.goal_id == "outro":
        if not data.custom_title:
            raise HTTPException(status_code=422, detail="Título é obrigatório para objetivo personalizado")
        if not data.custom_amount:
            raise HTTPException(status_code=422, detail="Valor é obrigatório para objetivo personalizado")
        title = data.custom_title
        description = data.custom_description
        target_amount = data.custom_amount
        priority = "media"
    else:
        preset = _PRESET_GOALS.get(data.goal_id)
        if not preset:
            raise HTTPException(status_code=422, detail=f"Objetivo '{data.goal_id}' não reconhecido")
        title = preset["title"]
        description = preset["description"]
        target_amount = data.custom_amount or preset["target_amount"]
        priority = "alta"

    contribution = _calculate_savings_contribution(data.income, data.monthly_cost)
    # Para o próximo objetivo usa 50% da capacidade de poupança (50% vai para reserva)
    goal_contribution = round(contribution * 0.5, 2)
    months = _months_to_reach(target_amount, goal_contribution)
    target_date = _add_months(date.today(), months)

    suggestion = ai_service.get_goal_suggestion(
        title=title,
        target_amount=target_amount,
        monthly_contribution=goal_contribution,
        months=months,
    )

    logger.info("next_goal_calculated", user_uuid=user_uuid, goal_id=data.goal_id)

    return NextGoalResponse(
        title=title,
        description=description,
        target_amount=target_amount,
        current_amount=0,
        priority=priority,
        target_date=target_date,
        monthly_contribution=goal_contribution,
        ai_suggestion=suggestion,
    )
