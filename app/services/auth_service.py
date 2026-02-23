import re

import httpx
import structlog
from fastapi import HTTPException, status
from supabase import Client

from app.core.config import settings
from app.repositories.onboarding_repository import OnboardingRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    RegisterUserResponse,
)

logger = structlog.get_logger()


def _format_phone(phone: str) -> str:
    """Format raw digits to (XX) XXXXX-XXXX or (XX) XXXX-XXXX."""
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
    """Create customer in AbacatePay. Returns customer_id or None on failure."""
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
            # AbacatePay wraps the resource in a "data" key
            return data.get("data", {}).get("id") or data.get("id")
    except Exception as exc:
        logger.error("abacatepay_customer_create_failed", error=str(exc))
        return None


def register(data: RegisterRequest, supabase: Client) -> RegisterResponse:
    # --- Validações ---
    if len(data.password) < 6:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Senha deve ter no mínimo 6 caracteres",
        )

    user_repo = UserRepository(supabase)

    if user_repo.email_exists(data.email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email já cadastrado")

    # --- Supabase Auth ---
    try:
        auth_response = supabase.auth.sign_up(
            {"email": data.email, "password": data.password}
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "already registered" in msg or "already been registered" in msg:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email já cadastrado")
        logger.error("supabase_signup_failed", error=str(exc))
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro ao criar conta"
        )

    if not auth_response.user:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro ao criar conta"
        )

    user_uuid = str(auth_response.user.id)

    # --- Perfil em public.users ---
    try:
        user_repo.create(
            uuid=user_uuid,
            name=data.name,
            email=data.email,
            phone=data.whatsapp,
            tax_id=data.cpf,
            active_bot=data.active_bot,
        )
    except Exception as exc:
        logger.error("user_profile_create_failed", uuid=user_uuid, error=str(exc))
        # Rollback: remove auth user to avoid orphan
        try:
            supabase.auth.admin.delete_user(user_uuid)
        except Exception:
            pass
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro ao criar perfil do usuário"
        )

    # --- AbacatePay customer (falha silenciosa: não bloqueia o registro) ---
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
            logger.error("customer_id_update_failed", uuid=user_uuid, error=str(exc))

    return RegisterResponse(
        user=RegisterUserResponse(email=data.email),
        detail="Verificação de email pendente.",
    )


def login(data: LoginRequest, supabase: Client) -> LoginResponse:
    # --- Autenticar via Supabase ---
    try:
        auth_response = supabase.auth.sign_in_with_password(
            {"email": data.email, "password": data.password}
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "email not confirmed" in msg or "not confirmed" in msg:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Requer verificação do email",
            )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")

    # Email ainda não confirmado (session None sem exceção em alguns casos)
    if auth_response.session is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Requer verificação do email",
        )

    user_uuid = str(auth_response.user.id)
    logger.info("login_auth_success", uuid=user_uuid, email=data.email)

    # sign_in_with_password mutates the client session to the user's JWT.
    # Reset PostgREST back to service_role so DB queries bypass RLS.
    supabase.postgrest.auth(settings.SUPABASE_SERVICE_ROLE_KEY)

    # --- Buscar perfil em public.users ---
    user_repo = UserRepository(supabase)
    user = user_repo.get_by_uuid(user_uuid)
    logger.info("login_user_lookup", uuid=user_uuid, found=user is not None)

    if not user:
        logger.error("user_profile_not_found_on_login", uuid=user_uuid)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Perfil não encontrado para uuid={user_uuid}",
        )

    # --- Verificar onboarding ---
    onboarding_repo = OnboardingRepository(supabase)
    onboarding_completed = onboarding_repo.is_completed(user_uuid)

    session = auth_response.session
    return LoginResponse(
        id=user["id"],
        uuid=str(user["uuid"]),
        name=user.get("name"),
        email=user.get("email"),
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in or 3600,
        onboarding_completed=onboarding_completed,
    )


def refresh(data: RefreshRequest, supabase: Client) -> RefreshResponse:
    try:
        auth_response = supabase.auth.refresh_session(data.refresh_token)
    except Exception as exc:
        logger.warning("token_refresh_failed", error=str(exc))
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Refresh token inválido ou expirado"
        )

    if auth_response.session is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Refresh token inválido ou expirado"
        )

    session = auth_response.session
    return RefreshResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in or 3600,
    )


def logout(access_token: str, supabase: Client) -> LogoutResponse:
    try:
        # Set the user's token so sign_out invalidates their specific session
        supabase.auth.set_session(access_token, "")
        supabase.auth.sign_out()
    except Exception as exc:
        logger.warning("logout_failed", error=str(exc))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")

    return LogoutResponse(message="Logout realizado com sucesso")
