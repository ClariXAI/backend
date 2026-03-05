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

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _calculate_suggested_limits(income: float, categories: list[str]) -> dict[str, float]:
    from app.schemas.onboarding import CATEGORY_WEIGHTS
    return {
        cat: round(income * CATEGORY_WEIGHTS[cat], 2)
        for cat in categories
        if cat in CATEGORY_WEIGHTS
    }


def _months_ahead(months: int):
    from datetime import date
    today = date.today()
    month = today.month + months
    year = today.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    return date(year, month, 1)


# helpers

import math as _math
from datetime import date as _date
from typing import Any


def _calculate_suggested_limits(income: float, categories: list[str]) -> dict[str, float]:
    from app.schemas.onboarding import CATEGORY_WEIGHTS
    return {
        cat: round(income * CATEGORY_WEIGHTS[cat], 2)
        for cat in categories
        if cat in CATEGORY_WEIGHTS
    }


def _months_ahead(months: int) -> _date:
    today = _date.today()
    month = today.month + months
    year = today.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    return _date(year, month, 1)


def _calc_emergency_fund(
    has_emergency_fund: bool,
    emergency_fund_amount: float | None,
    income: float,
    monthly_cost: float,
) -> dict[str, Any]:
    if not has_emergency_fund:
        target = round(6 * monthly_cost, 2)
        surplus = max(income - monthly_cost, 0)
        contribution = round(max(surplus * 0.3, 200), 2)
        months = _math.ceil(target / contribution) if contribution > 0 else 24
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


# get_onboarding
def get_onboarding(user_uuid: str, supabase) -> "OnboardingResponse":
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


# save_onboarding
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


# get_suggested_limits
def get_suggested_limits(income: float, categories: list) -> dict:
    return _calculate_suggested_limits(income, categories)


# calc_emergency_fund
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


# create_next_goal
def create_next_goal(user_uuid: str, data, supabase):
    from app.repositories.onboarding_repository import OnboardingRepository
    from app.repositories.goal_repository import GoalRepository, PRIORITY_ALTA
    from app.schemas.onboarding import NextGoalCreatedResponse
    from fastapi import HTTPException, status

    repo = OnboardingRepository(supabase)
    onboarding = repo.get_by_user_uuid(user_uuid)
    if not onboarding or not (onboarding.get("has_emergency_fund") or onboarding.get("emergency_fund_amount")):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Reserva de emergencia nao esta completa. Etapa de proximo objetivo nao disponivel.",
        )

    if data.goal_id == "outro":
        if not data.custom_title or not data.custom_amount:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Titulo e valor sao obrigatorios para meta personalizada",
            )
        title = data.custom_title
        description = data.custom_description
        target_amount = data.custom_amount
    else:
        preset = _GOAL_PRESETS.get(data.goal_id)
        if not preset:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "goal_id nao reconhecido: " + data.goal_id,
            )
        title = preset["title"]
        description = preset["description"]
        target_amount = preset["target_amount"]

    import math
    surplus = max(data.income - data.monthly_cost, 0)
    contribution = round(max(surplus * 0.5, 200), 2)
    months = math.ceil(target_amount / contribution) if contribution > 0 else 36
    target_date = _months_ahead(months)

    prompt = (
        "Voce e um consultor financeiro brasileiro. Responda em portugues, motivacional "
        "e conciso (1 frase). O usuario quer atingir o objetivo " + title + " e levara "
        + str(months) + " meses. Escreva apenas a frase de incentivo."
    )
    suggestion = _ai_suggestion(prompt)

    goal_repo = GoalRepository(supabase)
    row = goal_repo.create(
        user_uuid=user_uuid,
        name=title,
        description=description,
        target_value=target_amount,
        priority_id=PRIORITY_ALTA,
        target_date=str(target_date),
        monthly_contribution=contribution,
    )
    return NextGoalCreatedResponse(
        id=row["id"],
        title=row["name"],
        description=row.get("description"),
        target_amount=row["target_value"],
        current_amount=row.get("current_value") or 0,
        priority="alta",
        target_date=row.get("target_date"),
        monthly_contribution=row.get("monthly_contribution"),
        ai_suggestion=suggestion or None,
    )


# complete_onboarding
def complete_onboarding(user_uuid: str, supabase):
    from app.repositories.onboarding_repository import OnboardingRepository
    from app.repositories.category_repository import CategoryRepository
    from app.repositories.limit_repository import LimitRepository
    from app.repositories.goal_repository import GoalRepository, PRIORITY_ALTA, PRIORITY_BAIXA
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

    if not row or not row.get("income") or not row.get("monthly_cost") or not row.get("selected_categories"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Dados de onboarding incompletos")

    income = float(row["income"])
    monthly_cost = float(row["monthly_cost"])
    categories = row["selected_categories"]
    suggested_limits = row.get("suggested_limits") or _calculate_suggested_limits(income, categories)

    cat_repo = CategoryRepository(supabase)
    limit_repo = LimitRepository(supabase)
    categories_created = 0
    limits_created = 0

    for cat_name in categories:
        try:
            cat_row = cat_repo.create(user_uuid=user_uuid, name=cat_name)
            categories_created += 1
            limit_repo.create(
                user_uuid=user_uuid,
                category_id=cat_row["id"],
                value=suggested_limits.get(cat_name, 0),
            )
            limits_created += 1
        except Exception as exc:
            logger.warning("onboarding_category_limit_failed", category=cat_name, error=str(exc))

    goal_repo = GoalRepository(supabase)
    goals_created = []
    has_ef = row.get("has_emergency_fund")
    ef_amount = row.get("emergency_fund_amount")
    ef_data = _calc_emergency_fund(bool(has_ef), ef_amount, income, monthly_cost)
    priority_id = PRIORITY_BAIXA if has_ef else PRIORITY_ALTA

    try:
        ef_row = goal_repo.create(
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
            title=ef_row["name"],
            target_amount=ef_row["target_value"],
            current_amount=ef_row.get("current_value") or 0,
            priority=ef_data["priority"],
        ))
    except Exception as exc:
        logger.error("onboarding_emergency_fund_goal_failed", error=str(exc))

    commitment_created = None
    commitment_data = row.get("commitment")
    if commitment_data:
        c_type = commitment_data.get("type")
        c_data = commitment_data.get("data") or {}
        try:
            if c_type == "assinatura":
                SignatureRepository(supabase).create(
                    user_uuid=user_uuid,
                    name=c_data.get("title") or c_data.get("name", ""),
                    value=c_data.get("value"),
                    plan=c_data.get("plan"),
                    date_of_signature=c_data.get("due_date"),
                )
                commitment_created = CommitmentSummarySchema(
                    type=c_type, title=c_data.get("title") or c_data.get("name", "")
                )
            elif c_type == "cartao":
                CreditCardRepository(supabase).create(
                    user_uuid=user_uuid,
                    name=c_data.get("name", ""),
                    bank=c_data.get("bank"),
                    total_limit=c_data.get("total_limit"),
                    closing_day=c_data.get("closing_day"),
                    due_day=c_data.get("due_day"),
                )
                commitment_created = CommitmentSummarySchema(type=c_type, title=c_data.get("name", ""))
            elif c_type == "emprestimo":
                LoanRepository(supabase).create(
                    user_uuid=user_uuid,
                    name=c_data.get("name", ""),
                    institution=c_data.get("institution"),
                    due_day=c_data.get("due_day"),
                    total_number_of_installments=c_data.get("total_number_of_installments"),
                    installment_amount=c_data.get("installment_amount"),
                    fees=c_data.get("fees"),
                )
                commitment_created = CommitmentSummarySchema(type=c_type, title=c_data.get("name", ""))
            elif c_type == "consorcio":
                ConsortiaRepository(supabase).create(
                    user_uuid=user_uuid,
                    name=c_data.get("name", ""),
                    administrator=c_data.get("administrator"),
                    total_number_of_installments=c_data.get("total_number_of_installments"),
                    installment_amount=c_data.get("installment_amount"),
                    due_day=c_data.get("due_day"),
                )
                commitment_created = CommitmentSummarySchema(type=c_type, title=c_data.get("name", ""))
        except Exception as exc:
            logger.error("onboarding_commitment_failed", type=c_type, error=str(exc))

    repo.mark_completed(user_uuid)

    return CompleteOnboardingResponse(
        completed=True,
        categories_created=categories_created,
        limits_created=limits_created,
        goals_created=goals_created,
        commitment_created=commitment_created,
        message="Onboarding finalizado com sucesso",
    )
