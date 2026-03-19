from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import httpx
import structlog
from fastapi import HTTPException, status
from supabase import Client

from app.core.config import settings
from app.repositories.onboarding_repository import OnboardingRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TrialInfo,
    UserResponse,
)

# Mensagens de erro de email não confirmado retornadas pelo Supabase
_EMAIL_NOT_CONFIRMED_MSGS = ("email not confirmed", "email_not_confirmed")

logger = structlog.get_logger()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _format_phone(phone: str) -> str:
    """Formata dígitos brutos para (XX) XXXXX-XXXX ou (XX) XXXX-XXXX."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return phone


def _create_abacatepay_customer(
    name: str,
    email: str,
    phone: str | None,
    tax_id: str | None,
) -> str | None:
    """Cria cliente na AbacatePay. Retorna customer_id ou None em caso de falha.
    Falha silenciosa: nunca bloqueia o registro do usuário.
    """
    if not settings.ABACATEPAY_API_KEY:
        return None

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{settings.ABACATEPAY_BASE_URL}/v1/customer/create",
                headers={"Authorization": f"Bearer {settings.ABACATEPAY_API_KEY}"},
                json={
                    "name": name,
                    "cellphone": _format_phone(phone) if phone else "",
                    "email": email,
                    "taxId": tax_id or "",
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}).get("id") or data.get("id")
    except Exception as exc:
        logger.error("abacatepay_customer_create_failed", error=str(exc))
        return None


def _rollback_auth_user(supabase: Client, user_uuid: str) -> None:
    """Remove o usuário do Supabase Auth em caso de falha no registro."""
    try:
        supabase.auth.admin.delete_user(user_uuid)
    except Exception as exc:
        logger.error("auth_rollback_failed", user_uuid=user_uuid, error=str(exc))


# ── Register ───────────────────────────────────────────────────────────────────

def register(data: RegisterRequest, supabase: Client) -> RegisterResponse:
    user_repo = UserRepository(supabase)
    onboarding_repo = OnboardingRepository(supabase)

    # 1. Verifica duplicidade de email e WhatsApp antes de chamar o Supabase Auth
    if user_repo.email_exists(data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já cadastrado",
        )

    if data.whatsapp and user_repo.phone_exists(data.whatsapp):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="WhatsApp já cadastrado",
        )

    # 2. Calcula datas do trial
    now = datetime.now(timezone.utc)
    trial_ends_at = now + timedelta(days=settings.TRIAL_DAYS)

    # 3. Cria usuário no Supabase Auth
    try:
        auth_response = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password,
        })
    except Exception as exc:
        msg = str(exc).lower()
        if "already registered" in msg or "already been registered" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email já cadastrado",
            )
        logger.error("supabase_signup_failed", email=data.email, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar conta",
        )

    if not auth_response.user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar conta",
        )

    user_uuid = str(auth_response.user.id)

    # 4. Cria perfil em public.users
    try:
        user_repo.create(
            user_uuid=user_uuid,
            name=data.name,
            email=data.email,
            phone=data.whatsapp,
            tax_id=data.cpf,
            trial_starts_at=now,
            trial_ends_at=trial_ends_at,
        )
    except Exception as exc:
        logger.error("user_profile_create_failed", user_uuid=user_uuid, error=str(exc))
        _rollback_auth_user(supabase, user_uuid)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar perfil do usuário",
        )

    # 5. Cria registro inicial de onboarding
    try:
        onboarding_repo.create(user_uuid)
    except Exception as exc:
        logger.error("onboarding_create_failed", user_uuid=user_uuid, error=str(exc))
        _rollback_auth_user(supabase, user_uuid)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao inicializar onboarding",
        )

    # 6. Cria cliente na AbacatePay (falha silenciosa)
    customer_id = _create_abacatepay_customer(
        name=data.name,
        email=data.email,
        phone=data.whatsapp,
        tax_id=data.cpf,
    )
    if customer_id:
        try:
            user_repo.update_customer_id(user_uuid, customer_id)
        except Exception as exc:
            logger.error("customer_id_update_failed", user_uuid=user_uuid, error=str(exc))

    logger.info("user_registered", user_uuid=user_uuid, email=data.email)

    return RegisterResponse(
        user=UserResponse(
            id=user_uuid,
            name=data.name,
            email=data.email,
        ),
        detail="Verifique seu email para confirmar o cadastro.",
    )


# ── Login ──────────────────────────────────────────────────────────────────────

def login(data: LoginRequest, supabase: Client) -> LoginResponse:
    user_repo = UserRepository(supabase)
    onboarding_repo = OnboardingRepository(supabase)

    # 1. Autentica via Supabase Auth
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password,
        })
    except Exception as exc:
        msg = str(exc).lower()
        if any(m in msg for m in _EMAIL_NOT_CONFIRMED_MSGS):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email ainda não confirmado. Verifique sua caixa de entrada.",
            )
        if "invalid" in msg or "credentials" in msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha inválidos",
            )
        logger.error("supabase_signin_failed", email=data.email, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao realizar login",
        )

    if not auth_response.user or not auth_response.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
        )

    user_uuid = str(auth_response.user.id)

    # 2. Busca perfil no DB
    profile = user_repo.get_by_uuid(user_uuid)
    if not profile:
        logger.error("user_profile_not_found", user_uuid=user_uuid)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil do usuário não encontrado",
        )

    # 3. Verifica se o trial expirou e atualiza o status
    plan_status = profile["plan_status"]
    now = datetime.now(timezone.utc)

    if plan_status == "trial":
        trial_ends_at = datetime.fromisoformat(profile["trial_ends_at"])
        # Garante timezone para comparação
        if trial_ends_at.tzinfo is None:
            trial_ends_at = trial_ends_at.replace(tzinfo=timezone.utc)

        if now > trial_ends_at:
            plan_status = "expired"
            try:
                user_repo.update_plan_status(user_uuid, "expired")
            except Exception as exc:
                logger.error("plan_status_update_failed", user_uuid=user_uuid, error=str(exc))

    # 4. Monta trial info (apenas quando relevante)
    trial_info: TrialInfo | None = None
    if plan_status in ("trial", "expired") and profile.get("trial_starts_at") and profile.get("trial_ends_at"):
        trial_ends_at = datetime.fromisoformat(profile["trial_ends_at"])
        trial_starts_at = datetime.fromisoformat(profile["trial_starts_at"])
        if trial_ends_at.tzinfo is None:
            trial_ends_at = trial_ends_at.replace(tzinfo=timezone.utc)
        if trial_starts_at.tzinfo is None:
            trial_starts_at = trial_starts_at.replace(tzinfo=timezone.utc)

        days_remaining = max(0, (trial_ends_at - now).days)
        trial_info = TrialInfo(
            starts_at=trial_starts_at,
            ends_at=trial_ends_at,
            days_remaining=days_remaining,
        )

    # 5. Verifica onboarding
    onboarding_completed = onboarding_repo.is_completed(user_uuid)

    logger.info("user_logged_in", user_uuid=user_uuid, plan_status=plan_status)

    return LoginResponse(
        user=UserResponse(
            id=user_uuid,
            name=profile["name"],
            email=profile["email"],
        ),
        onboarding_completed=onboarding_completed,
        plan_status=plan_status,
        trial=trial_info,
        access_token=auth_response.session.access_token,
        refresh_token=auth_response.session.refresh_token,
    )


# ── Refresh ────────────────────────────────────────────────────────────────────

def refresh(data: RefreshRequest, supabase: Client) -> RefreshResponse:
    try:
        auth_response = supabase.auth.refresh_session(data.refresh_token)
    except Exception as exc:
        msg = str(exc).lower()
        if "invalid" in msg or "expired" in msg or "not found" in msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido ou expirado",
            )
        logger.error("supabase_refresh_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao renovar sessão",
        )

    if not auth_response.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado",
        )

    return RefreshResponse(
        access_token=auth_response.session.access_token,
        refresh_token=auth_response.session.refresh_token,
    )


# ── Logout ─────────────────────────────────────────────────────────────────────

# ── Forgot password ────────────────────────────────────────────────────────────

def forgot_password(data: ForgotPasswordRequest, supabase: Client) -> ForgotPasswordResponse:
    """Dispara o email de redefinição via Supabase.
    Sempre retorna sucesso — nunca revela se o email existe ou não.
    """
    try:
        supabase.auth.reset_password_email(data.email)
    except Exception as exc:
        # Loga mas não expõe o erro ao cliente (evita user enumeration)
        logger.error("reset_password_email_failed", email=data.email, error=str(exc))

    logger.info("forgot_password_requested", email=data.email)
    return ForgotPasswordResponse()


# ── Reset password ─────────────────────────────────────────────────────────────

def reset_password(data: ResetPasswordRequest, supabase: Client) -> ResetPasswordResponse:
    """Troca a senha usando o token OTP do link de redefinição."""
    # 1. Troca o token por uma sessão válida
    try:
        session_response = supabase.auth.exchange_code_for_session(data.token)
    except Exception as exc:
        msg = str(exc).lower()
        logger.error("exchange_code_failed", error=str(exc))
        if any(k in msg for k in ("invalid", "expired", "not found")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Link de redefinição inválido ou expirado.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao validar o link de redefinição.",
        )

    if not session_response.session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link de redefinição inválido ou expirado.",
        )

    # 2. Atualiza a senha usando o access_token da sessão recém-criada
    try:
        session_client = supabase
        session_client.auth.set_session(
            session_response.session.access_token,
            session_response.session.refresh_token,
        )
        session_client.auth.update_user({"password": data.new_password})
    except Exception as exc:
        logger.error("update_password_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao redefinir a senha.",
        )

    logger.info("password_reset_success", user_id=str(session_response.user.id if session_response.user else "unknown"))
    return ResetPasswordResponse()


# ── Logout ─────────────────────────────────────────────────────────────────────

def logout(access_token: str, supabase: Client) -> LogoutResponse:
    try:
        supabase.auth.admin.sign_out(access_token)
    except Exception as exc:
        logger.error("supabase_signout_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao encerrar sessão",
        )
    return LogoutResponse()
