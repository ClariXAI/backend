# Auth — Documentação Técnica

## Visão Geral

O ClariX não gerencia sessões nem armazena senhas. Toda autenticação é delegada ao **Supabase Auth**, que emite JWTs (RS256/HS256). O FastAPI apenas **valida** esses tokens, extrai o `user_id` (`sub`) e injeta como contexto em todos os endpoints protegidos.

```
Cliente               FastAPI                  Supabase Auth         PostgreSQL
  │                      │                           │                   │
  │ POST /auth/register  │                           │                   │
  │─────────────────────▶│  supabase.auth.sign_up()  │                   │
  │                      │──────────────────────────▶│                   │
  │                      │◀──────────────────────────│ session + user    │
  │                      │  INSERT INTO public.users │                   │
  │                      │──────────────────────────────────────────────▶│
  │◀─────────────────────│  { access_token, refresh_token, user }        │
  │                      │                           │                   │
  │ POST /auth/login     │                           │                   │
  │─────────────────────▶│  supabase.auth.sign_in()  │                   │
  │                      │──────────────────────────▶│                   │
  │◀─────────────────────│◀──────────────────────────│ session           │
  │                      │                           │                   │
  │ GET /profile         │                           │                   │
  │  Authorization: Bearer <access_token>            │                   │
  │─────────────────────▶│                           │                   │
  │                      │ verify_supabase_token()   │                   │
  │                      │ → UserContext(user_id)     │                   │
  │◀─────────────────────│                           │                   │
```

---

## Endpoints Planejados

| Método | Path | Proteção | Descrição |
|--------|------|----------|-----------|
| `POST` | `/api/v1/auth/register` | Público | Cria conta no Supabase Auth + registro em `public.users` |
| `POST` | `/api/v1/auth/login` | Público | Autentica e retorna `access_token` + `refresh_token` |
| `POST` | `/api/v1/auth/refresh` | Público | Troca `refresh_token` por novo par de tokens |
| `POST` | `/api/v1/auth/logout` | JWT | Invalida a sessão no Supabase |
| `GET`  | `/api/v1/auth/me` | JWT | Retorna dados do usuário autenticado |

---

## Fluxo de Register

```
POST /api/v1/auth/register
Body: { name, email, password, cpf?, whatsapp? }

1. Valida schema (Pydantic)
2. supabase.auth.sign_up({ email, password })
   → Supabase cria registro em auth.users
   → Envia e-mail de confirmação (configurável)
3. INSERT INTO public.users
   (id=auth_user.id, name, email, cpf, whatsapp, plan='free',
    onboarding_completed=false)
4. Retorna { access_token, refresh_token, token_type, user }
```

**Transação atômica:** O `id` de `public.users` é o mesmo UUID gerado pelo Supabase Auth (`auth.users.id`). Se o INSERT falhar após o sign_up, o handler de exceção chama `supabase.auth.admin.delete_user(uid)` para fazer rollback manual.

---

## Fluxo de Login

```
POST /api/v1/auth/login
Body: { email, password }

1. supabase.auth.sign_in_with_password({ email, password })
2. Supabase valida e retorna session
3. Retorna { access_token, refresh_token, token_type, expires_in }
```

Nenhuma query ao banco é necessária — Supabase faz tudo.

---

## Fluxo de Refresh

```
POST /api/v1/auth/refresh
Body: { refresh_token }

1. supabase.auth.refresh_session(refresh_token)
2. Retorna novo par { access_token, refresh_token }
```

O `access_token` do Supabase expira em **1 hora** por padrão. O frontend deve chamar este endpoint antes da expiração.

---

## Fluxo de Logout

```
POST /api/v1/auth/logout
Header: Authorization: Bearer <access_token>

1. get_current_user() → valida JWT → UserContext
2. supabase.auth.sign_out()
   → Invalida a sessão no lado do Supabase (blacklist interna)
3. Retorna 204 No Content
```

---

## Fluxo de /me

```
GET /api/v1/auth/me
Header: Authorization: Bearer <access_token>

1. get_current_user() → valida JWT → UserContext(user_id, email)
2. SELECT * FROM public.users WHERE id = user_id
3. Retorna { id, name, email, cpf, whatsapp, plan,
             onboarding_completed, created_at }
```

---

## Validação JWT (core/security.py)

```python
# O Supabase assina os JWTs com o SUPABASE_JWT_SECRET (HS256)
payload = jwt.decode(
    token,
    SUPABASE_JWT_SECRET,
    algorithms=["HS256"],
    audience="authenticated",   # claim obrigatória no token Supabase
)
# payload contém:
# {
#   "sub": "uuid-do-usuario",        ← user_id
#   "email": "user@email.com",
#   "role": "authenticated",
#   "aud": "authenticated",
#   "exp": 1234567890,
#   "iat": 1234567890,
# }
```

A validação verifica automaticamente: **expiração**, **audiência** e **assinatura**. Nenhuma chamada extra ao Supabase é necessária — o JWT é self-contained.

---

## Injeção de Dependência

Todos os endpoints protegidos recebem `current_user: UserContext` via:

```python
@router.get("/me")
async def get_me(
    current_user: UserContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    ...
```

`get_current_user` extrai o Bearer token do header, valida com `verify_supabase_token()` e retorna `UserContext(user_id, email)`.

---

## Tabela `public.users`

```sql
CREATE TABLE public.users (
    id                   UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name                 TEXT NOT NULL,
    email                TEXT NOT NULL UNIQUE,
    cpf                  TEXT,
    whatsapp             TEXT,
    plan                 TEXT NOT NULL DEFAULT 'free',       -- free | pro | premium
    billing_period       TEXT DEFAULT 'monthly',             -- monthly | yearly
    onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_select_own" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "users_update_own" ON public.users
    FOR UPDATE USING (auth.uid() = id);

-- Index
CREATE INDEX users_email_idx ON public.users(email);
```

**Nota:** O `INSERT` inicial é feito com a `service_role_key` (que bypassa RLS), porque no momento do register o usuário ainda não tem sessão ativa no banco.

---

## Schemas Pydantic (schemas/auth.py)

```python
# Request
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str          # min 8 chars — validado no Supabase
    cpf: str | None = None
    whatsapp: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

# Response
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    cpf: str | None
    whatsapp: str | None
    plan: str
    onboarding_completed: bool
    created_at: datetime

class RegisterResponse(BaseModel):
    tokens: TokenResponse
    user: UserResponse
```

---

## Tratamento de Erros

| Situação | HTTP | Mensagem |
|----------|------|----------|
| E-mail já cadastrado | 409 Conflict | "E-mail já está em uso" |
| Credenciais inválidas | 401 Unauthorized | "E-mail ou senha incorretos" |
| Token expirado | 401 Unauthorized | "Token expirado" |
| Token inválido | 401 Unauthorized | "Token inválido" |
| Usuário não encontrado | 404 Not Found | "Usuário não encontrado" |

---

## Variáveis de Ambiente Necessárias

| Variável | Onde encontrar | Uso |
|----------|---------------|-----|
| `SUPABASE_URL` | Dashboard → Project Settings → API → Project URL | Base URL do client |
| `SUPABASE_ANON_KEY` | Dashboard → Project Settings → API → anon public | Operações públicas (sign_up, sign_in) |
| `SUPABASE_SERVICE_ROLE_KEY` | Dashboard → Project Settings → API → service_role | INSERT em public.users (bypassa RLS) |
| `SUPABASE_JWT_SECRET` | Dashboard → Project Settings → API → JWT Settings → JWT Secret | Validação local do token |

> ⚠️ `SUPABASE_SERVICE_ROLE_KEY` nunca deve ser exposta no frontend. Fica apenas no backend.
