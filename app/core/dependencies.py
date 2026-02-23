from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from supabase import Client, create_client

from app.core.config import settings
from app.core.security import verify_supabase_token


@dataclass
class UserContext:
    user_id: str
    email: str


def get_supabase_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


async def get_current_user(
    access_token: str = Header(alias="access-token"),
) -> UserContext:
    payload = await verify_supabase_token(access_token)

    user_id: str | None = payload.get("sub")
    email: str | None = payload.get("email")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem identificador de usuário",
        )

    return UserContext(user_id=user_id, email=email or "")
