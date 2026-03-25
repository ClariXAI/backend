from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.core.dependencies import get_supabase_client

_bearer = HTTPBearer()
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
    ResendConfirmationRequest,
    ResendConfirmationResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(
    data: RegisterRequest,
    supabase: Client = Depends(get_supabase_client),
) -> RegisterResponse:
    return auth_service.register(data, supabase)


@router.post("/login", response_model=LoginResponse)
def login(
    data: LoginRequest,
    supabase: Client = Depends(get_supabase_client),
) -> LoginResponse:
    return auth_service.login(data, supabase)


@router.post("/refresh", response_model=RefreshResponse)
def refresh(
    data: RefreshRequest,
    supabase: Client = Depends(get_supabase_client),
) -> RefreshResponse:
    return auth_service.refresh(data, supabase)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    data: ForgotPasswordRequest,
    supabase: Client = Depends(get_supabase_client),
) -> ForgotPasswordResponse:
    return auth_service.forgot_password(data, supabase)


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    data: ResetPasswordRequest,
    supabase: Client = Depends(get_supabase_client),
) -> ResetPasswordResponse:
    return auth_service.reset_password(data, supabase)


@router.post("/logout", response_model=LogoutResponse)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    supabase: Client = Depends(get_supabase_client),
) -> LogoutResponse:
    return auth_service.logout(credentials.credentials, supabase)


@router.post("/resend-confirmation", response_model=ResendConfirmationResponse)
def resend_confirmation(
    data: ResendConfirmationRequest,
    supabase: Client = Depends(get_supabase_client),
) -> ResendConfirmationResponse:
    return auth_service.resend_confirmation(data, supabase)
