from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    email: EmailStr
    password: str
    cpf: str | None = None
    whatsapp: str | None = None
    active_bot: bool = Field(default=False, alias="activeBot")


class RegisterUserResponse(BaseModel):
    email: str


class RegisterResponse(BaseModel):
    user: RegisterUserResponse
    detail: str


# ─── Login ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    id: int
    uuid: str
    name: str | None
    email: str | None
    access_token: str
    refresh_token: str
    expires_in: int
    onboarding_completed: bool


# ─── Refresh ──────────────────────────────────────────────────────────────────

class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


# ─── Logout ───────────────────────────────────────────────────────────────────

class LogoutResponse(BaseModel):
    message: str


# ─── Forgot Password ──────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


# ─── Reset Password ───────────────────────────────────────────────────────────

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    message: str
