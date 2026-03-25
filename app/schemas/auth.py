from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)
    cpf: str | None = None
    whatsapp: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nome não pode ser vazio")
        return v

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: str | None) -> str | None:
        if v is None:
            return v
        digits = re.sub(r"\D", "", v)
        if len(digits) != 11:
            raise ValueError("CPF deve conter 11 dígitos")
        # Rejeita CPFs com todos os dígitos iguais (ex: 111.111.111-11)
        if len(set(digits)) == 1:
            raise ValueError("CPF inválido")
        return digits

    @field_validator("whatsapp")
    @classmethod
    def validate_whatsapp(cls, v: str | None) -> str | None:
        if v is None:
            return v
        digits = re.sub(r"\D", "", v)
        # Normaliza: adiciona código do Brasil se ainda não tiver
        if len(digits) in (10, 11):
            digits = "55" + digits
        if len(digits) not in (12, 13):
            raise ValueError("WhatsApp inválido")
        return digits  # armazena sempre com código do país: 5575982985771


# ── Response models ────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: str
    name: str
    email: str


class TrialInfo(BaseModel):
    starts_at: datetime
    ends_at: datetime
    days_remaining: int


class RegisterResponse(BaseModel):
    user: UserResponse
    detail: str  # ex: "Verifique seu email para confirmar o cadastro"


# ── Login ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    user: UserResponse
    onboarding_completed: bool
    plan_status: str
    trial: TrialInfo | None = None
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── Logout ────────────────────────────────────────────────────────────────────

class LogoutResponse(BaseModel):
    detail: str = "Sessão encerrada com sucesso."


# ── Refresh ────────────────────────────────────────────────────────────────────

class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── Forgot / Reset password ────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    detail: str = "Se este email estiver cadastrado, você receberá um link de redefinição."


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ResetPasswordResponse(BaseModel):
    detail: str = "Senha redefinida com sucesso."


# ── Resend confirmation ────────────────────────────────────────────────────────

class ResendConfirmationRequest(BaseModel):
    email: EmailStr


class ResendConfirmationResponse(BaseModel):
    detail: str = "Se este email estiver cadastrado, você receberá um novo link de confirmação."
