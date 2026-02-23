from fastapi import APIRouter, Depends, Header, HTTPException, status
from supabase import Client

from app.core.dependencies import get_supabase_client
from app.core.security import verify_supabase_token
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
async def logout(
    access_token: str = Header(alias="access-token"),
    supabase: Client = Depends(get_supabase_client),
) -> LogoutResponse:
    try:
        await verify_supabase_token(access_token)
    except HTTPException:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")
    return auth_service.logout(access_token, supabase)
