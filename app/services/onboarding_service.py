from __future__ import annotations

import math
from datetime import date
from typing import Any

import anthropic
import structlog
from fastapi import HTTPException, status
from supabase import Client

from app.core.config import settings
from app.repositories.category_repository import CategoryRepository
from app.repositories.consortia_repository import ConsortiaRepository
from app.repositories.credit_card_repository import CreditCardRepository
from app.repositories.goal_repository import GoalRepository, PRIORITY_ALTA, PRIORITY_BAIXA
from app.repositories.limit_repository import LimitRepository
from app.repositories.loan_repository import LoanRepository
from app.repositories.onboarding_repository import OnboardingRepository
from app.repositories.signature_repository import SignatureRepository
from app.schemas.onboarding import (
    CATEGORY_WEIGHTS,
    CommitmentSchema,
    CommitmentSummarySchema,
    CompleteOnboardingResponse,
    EmergencyFundGoalSchema,
    EmergencyFundRequest,
    EmergencyFundResponse,
    GoalSummarySchema,
    NextGoalCreatedResponse,
    NextGoalRequest,
    NextGoalSchema,
    OnboardingResponse,
    SaveOnboardingRequest,
    SaveOnboardingResponse,
)

logger = structlog.get_logger()

_GOAL_PRESETS: dict[str, dict] = {
    "viagem_europa": {
        "title": "Viagem Europa",
        "description": "Ferias dos sonhos na Europa",
        "target_amount": 25000.0,
    },
    "entrada_apartamento": {
        "title": "Entrada Apartamento",
        "description": "Entrada para o apartamento proprio",
        "target_amount": 50000.0,
    },
    "novo_notebook": {
        "title": "Novo Notebook",
        "description": "Notebook para trabalho e estudo",
        "target_amount": 5000.0,
    },
}

# helpers

import math
from datetime import date
from typing import Any


def _calculate_suggested_limits(income: float, categories: list) -> dict:
    from app.schemas.onboarding import CATEGORY_WEIGHTS
    return {
        cat: round(income * CATEGORY_WEIGHTS[cat], 2)
        for cat in categories
        if cat in CATEGORY_WEIGHTS
    }


def _months_ahead(months: int) -> date:
    today = date.today()
    month = today.month + months
    year = today.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    return date(year, month, 1)


def _calc_emergency_fund(has_emergency_fund, emergency_fund_amount, income, monthly_cost) -> dict:
    if not has_emergency_fund:
        target = round(6 * monthly_cost, 2)
        surplus = max(income - monthly_cost, 0)
        contribution = round(max(surplus * 0.3, 200), 2)
        months = math.ceil(target / contribution) if contribution > 0 else 24
        return {
            "title": "Reserva de Emergencia",
            "target_amount": target,
            "current_amount": 0.0,
            "priority": "alta",
            "target_date": _months_ahead(months),
            "monthly_contribution": contribution,
        }
    amount = emergency_fund_amount or 0.0
    return {
        "title": "Reserva de Emergencia",
        "target_amount": amount,
        "current_amount": amount,
        "priority": "baixa",
        "target_date": None,
        "monthly_contribution": 0.0,
    }


def _ai_suggestion(prompt: str) -> str:
    from app.core.config import settings
    import anthropic
    if not settings.ANTHROPIC_API_KEY:
        return ""
    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as exc:
        logger.warning("ai_suggestion_failed", error=str(exc))
        return ""


def get_onboarding(user_uuid: str, supabase):
    from app.repositories.onboarding_repository import OnboardingRepository
    from app.schemas.onboarding import OnboardingResponse, NextGoalSchema, CommitmentSchema
    from fastapi import HTTPException, status
    repo = OnboardingRepository(supabase)
    row = repo.get_by_user_uuid(user_uuid)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Onboarding nao iniciado")
    ng = row.get("next_goal")
    cm = row.get("commitment")
    return OnboardingResponse(
        income=row.get("income"),
        monthly_cost=row.get("monthly_cost"),
        selected_categories=row.get("selected_categories"),
        suggested_limits=row.get("suggested_limits"),
        has_emergency_fund=row.get("has_emergency_fund"),
        emergency_fund_amount=row.get("emergency_fund_amount"),
        next_goal=NextGoalSchema(**ng) if ng else None,
        commitment=CommitmentSchema(**cm) if cm else None,
        current_step=row.get("current_step"),
        completed=row.get("completed") or False,
    )


def save_onboarding(user_uuid: str, data, supabase):
    from app.repositories.onboarding_repository import OnboardingRepository
    from app.schemas.onboarding import (
        SaveOnboardingResponse, NextGoalSchema, CommitmentSchema, EmergencyFundGoalSchema
    )
    from fastapi import HTTPException, status
    if data.income is not None and data.income <= 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Renda deve ser maior que zero")
    if data.monthly_cost is not None and data.monthly_cost <= 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Custo mensal deve ser maior que zero")

    income = data.income
    categories = data.selected_categories
    suggested_limits = None
    if income and categories:
        suggested_limits = _calculate_suggested_limits(income, categories)

    db_data = {}
    if data.income is not None:
        db_data["income"] = int(data.income)
    if data.monthly_cost is not None:
        db_data["monthly_cost"] = int(data.monthly_cost)
    if data.selected_categories is not None:
        db_data["selected_categories"] = data.selected_categories
    if suggested_limits is not None:
        db_data["suggested_limits"] = suggested_limits
    if data.has_emergency_fund is not None:
        db_data["has_emergency_fund"] = data.has_emergency_fund
    if data.emergency_fund_amount is not None:
        db_data["emergency_fund_amount"] = int(data.emergency_fund_amount)
    if data.next_goal is not None:
        db_data["next_goal"] = data.next_goal.model_dump(mode="json")
    if data.commitment is not None:
        db_data["commitment"] = data.commitment.model_dump(mode="json")
    if data.current_step is not None:
        db_data["current_step"] = data.current_step

    repo = OnboardingRepository(supabase)
    row = repo.save(user_uuid, db_data)

    ef_goal = None
    ef_has = row.get("has_emergency_fund")
    ef_income = row.get("income") or 0
    ef_cost = row.get("monthly_cost") or 0
    if ef_has is not None and ef_income and ef_cost:
        ef_data = _calc_emergency_fund(ef_has, row.get("emergency_fund_amount"), ef_income, ef_cost)
        ef_goal = EmergencyFundGoalSchema(**ef_data)

    ng = row.get("next_goal")
    cm = row.get("commitment")
    return SaveOnboardingResponse(
        income=row.get("income"),
        monthly_cost=row.get("monthly_cost"),
        selected_categories=row.get("selected_categories"),
        suggested_limits=row.get("suggested_limits"),
        has_emergency_fund=row.get("has_emergency_fund"),
        emergency_fund_amount=row.get("emergency_fund_amount"),
        emergency_fund_goal=ef_goal,
        next_goal=NextGoalSchema(**ng) if ng else None,
        commitment=CommitmentSchema(**cm) if cm else None,
        current_step=row.get("current_step"),
        completed=row.get("completed") or False,
    )


def get_suggested_limits(income: float, categories: list) -> dict:
    return _calculate_suggested_limits(income, categories)


def calc_emergency_fund(data):
    from app.schemas.onboarding import EmergencyFundResponse
    ef = _calc_emergency_fund(
        data.has_emergency_fund, data.emergency_fund_amount, data.income, data.monthly_cost
    )
    if not data.has_emergency_fund:
        mc = ef["monthly_contribution"]
        months = math.ceil(ef["target_amount"] / mc) if mc else 24
        prompt = (
            "Voce e um consultor financeiro brasileiro. Responda em portugues, motivacional "
            "e conciso (1 frase). O usuario quer montar uma reserva de emergencia. "
            "Levara cerca de " + str(months) + " meses com contribuicoes mensais. "
            "Escreva apenas a frase de incentivo."
        )
    else:
        prompt = (
            "Voce e um consultor financeiro brasileiro. Responda em portugues, motivacional "
            "e conciso (1 frase). O usuario ja possui reserva de emergencia. "
            "Parabenize e incentive-o a manter. Escreva apenas a frase."
        )
    suggestion = _ai_suggestion(prompt)
    return EmergencyFundResponse(
        title=ef["title"],
        target_amount=ef["target_amount"],
        current_amount=ef["current_amount"],
        priority=ef["priority"],
        target_date=ef["target_date"],
        monthly_contribution=ef["monthly_contribution"],
        ai_suggestion=suggestion or None,
    )


def create_next_goal(user_uuid: str, data, supabase):
    from app.repositories.goal_repository import GoalRepository, PRIORITY_ALTA, PRIORITY_BAIXA
    from app.schemas.onboarding import NextGoalCreatedResponse, NextGoalSchema, GoalSummarySchema

    preset = _GOAL_PRESETS.get(data.goal_key) if data.goal_key else None
    title = preset["title"] if preset else (data.title or "Meta")
    description = preset["description"] if preset else data.description
    target_amount = float(preset["target_amount"]) if preset else float(data.target_amount or 0)

    income = data.income or 0.0
    monthly_cost = data.monthly_cost or 0.0
    surplus = max(income - monthly_cost, 0)
    contribution = round(surplus * 0.1, 2) if surplus > 0 else 100.0
    months = math.ceil(target_amount / contribution) if contribution > 0 else 12
    target_date = _months_ahead(months)

    prompt = (
        "Voce e um consultor financeiro brasileiro. Responda em portugues, motivacional "
        "e conciso (1 frase). O usuario definiu uma meta financeira: " + title + ". "
        "Com contribuicoes mensais chegara la em cerca de " + str(months) + " meses. "
        "Escreva apenas a frase de incentivo."
    )
    suggestion = _ai_suggestion(prompt)

    goal_repo = GoalRepository(supabase)
    priority_id = PRIORITY_ALTA if months <= 6 else PRIORITY_BAIXA
    saved_goal = goal_repo.create(
        user_uuid=user_uuid,
        name=title,
        description=description,
        target_value=target_amount,
        priority_id=priority_id,
        target_date=str(target_date),
        monthly_contribution=contribution,
    )

    from app.repositories.onboarding_repository import OnboardingRepository
    onboarding_repo = OnboardingRepository(supabase)
    onboarding_repo.save(user_uuid, {
        "next_goal": {
            "goal_key": data.goal_key,
            "title": title,
            "description": description,
            "target_amount": target_amount,
            "monthly_contribution": contribution,
        }
    })

    goal_summary = GoalSummarySchema(
        id=saved_goal["id"],
        name=saved_goal["name"],
        target_value=saved_goal["target_value"],
        current_value=saved_goal["current_value"],
        monthly_contribution=saved_goal.get("monthly_contribution"),
        target_date=saved_goal.get("target_date"),
        priority_id=saved_goal["priority_id"],
    )
    return NextGoalCreatedResponse(
        goal=goal_summary,
        monthly_contribution=contribution,
        months_to_goal=months,
        target_date=target_date,
        ai_suggestion=suggestion or None,
    )


def complete_onboarding(user_uuid: str, supabase):
    from app.repositories.onboarding_repository import OnboardingRepository
    from app.repositories.goal_repository import GoalRepository, PRIORITY_ALTA, PRIORITY_BAIXA
    from app.repositories.category_repository import CategoryRepository
    from app.repositories.limit_repository import LimitRepository
    from app.repositories.signature_repository import SignatureRepository
    from app.repositories.credit_card_repository import CreditCardRepository
    from app.repositories.loan_repository import LoanRepository
    from app.repositories.consortia_repository import ConsortiaRepository
    from app.schemas.onboarding import (
        CompleteOnboardingResponse, GoalSummarySchema, CommitmentSummarySchema
    )
    from fastapi import HTTPException, status

    repo = OnboardingRepository(supabase)
    row = repo.get_by_user_uuid(user_uuid)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Onboarding nao iniciado")

    goals_created: list[GoalSummarySchema] = []
    commitment_created: CommitmentSummarySchema | None = None

    # Emergency fund goal
    ef_has = row.get("has_emergency_fund")
    ef_income = row.get("income") or 0
    ef_cost = row.get("monthly_cost") or 0
    if ef_has is not None and ef_income and ef_cost:
        ef_data = _calc_emergency_fund(ef_has, row.get("emergency_fund_amount"), ef_income, ef_cost)
        priority_id = PRIORITY_ALTA if ef_data["priority"] == "alta" else PRIORITY_BAIXA
        goal_repo = GoalRepository(supabase)
        saved = goal_repo.create(
            user_uuid=user_uuid,
            name=ef_data["title"],
            description=None,
            target_value=ef_data["target_amount"],
            priority_id=priority_id,
            target_date=str(ef_data["target_date"]) if ef_data["target_date"] else None,
            monthly_contribution=ef_data["monthly_contribution"],
            current_value=ef_data["current_amount"],
        )
        goals_created.append(GoalSummarySchema(
            id=saved["id"],
            name=saved["name"],
            target_value=saved["target_value"],
            current_value=saved["current_value"],
            monthly_contribution=saved.get("monthly_contribution"),
            target_date=saved.get("target_date"),
            priority_id=saved["priority_id"],
        ))

    # Categories and limits
    cats = row.get("selected_categories") or []
    limits = row.get("suggested_limits") or {}
    if cats:
        cat_repo = CategoryRepository(supabase)
        limit_repo = LimitRepository(supabase)
        for cat_name in cats:
            saved_cat = cat_repo.create(user_uuid=user_uuid, name=cat_name)
            limit_val = limits.get(cat_name)
            if limit_val:
                limit_repo.create(user_uuid=user_uuid, category_id=saved_cat["id"], value=limit_val)

    # Commitment
    cm = row.get("commitment")
    if cm:
        ctype = cm.get("type")
        name = cm.get("name", "")
        value = float(cm.get("value") or 0)

        if ctype == "assinatura":
            sig_repo = SignatureRepository(supabase)
            saved_cm = sig_repo.create(
                user_uuid=user_uuid,
                name=name,
                value=value,
                plan=cm.get("plan"),
                date_of_signature=cm.get("due_date"),
            )
            commitment_created = CommitmentSummarySchema(id=saved_cm["id"], type=ctype, name=name, value=value)
        elif ctype == "cartao":
            cc_repo = CreditCardRepository(supabase)
            saved_cm = cc_repo.create(
                user_uuid=user_uuid,
                name=name,
                total_limit=value,
            )
            commitment_created = CommitmentSummarySchema(id=saved_cm["id"], type=ctype, name=name, value=value)
        elif ctype == "emprestimo":
            loan_repo = LoanRepository(supabase)
            saved_cm = loan_repo.create(
                user_uuid=user_uuid,
                name=name,
                installment_amount=value,
            )
            commitment_created = CommitmentSummarySchema(id=saved_cm["id"], type=ctype, name=name, value=value)
        elif ctype == "consorcio":
            con_repo = ConsortiaRepository(supabase)
            saved_cm = con_repo.create(
                user_uuid=user_uuid,
                name=name,
                installment_amount=value,
            )
            commitment_created = CommitmentSummarySchema(id=saved_cm["id"], type=ctype, name=name, value=value)

    repo.mark_completed(user_uuid)

    return CompleteOnboardingResponse(
        goals_created=goals_created,
        commitment_created=commitment_created,
        completed=True,
    )
