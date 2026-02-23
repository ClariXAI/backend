from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.core.dependencies import UserContext, get_current_user, get_supabase_client
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.services import auth_service

_bearer = HTTPBearer()

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


@router.post("/logout", response_model=LogoutResponse)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    _: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> LogoutResponse:
    return auth_service.logout(credentials.credentials, supabase)
