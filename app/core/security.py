import json
from functools import lru_cache

import httpx
import jwt
from fastapi import HTTPException, status
from jwt.algorithms import ECAlgorithm

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_supabase_public_key() -> object:
    """Busca e cacheia a chave pública EC do Supabase via JWKS."""
    url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    jwks = response.json()
    key_data = jwks["keys"][0]
    return ECAlgorithm.from_jwk(json.dumps(key_data))


async def verify_supabase_token(token: str) -> dict:
    """Decodifica e valida um JWT emitido pelo Supabase (ES256)."""
    try:
        public_key = _get_supabase_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["ES256"],
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
