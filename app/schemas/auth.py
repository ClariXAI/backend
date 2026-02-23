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
