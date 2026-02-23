from fastapi import APIRouter, Depends
from supabase import Client

from app.core.dependencies import get_supabase_client
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse
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
