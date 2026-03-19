# Auth

Toda autenticação é delegada ao **Supabase Auth** (JWT HS256). O FastAPI valida o token localmente, extrai `user_id` (`sub`) e injeta como `UserContext` nas rotas protegidas. Nenhuma chamada extra ao Supabase é feita na validação.

Base: `/api/v1/auth`

---

## Fluxo geral

```
Register → confirmar email → Login → Onboarding (se não concluído) → App
```

- O registro **não** retorna tokens — o usuário precisa confirmar o email antes de logar.
- O login verifica onboarding e trial, retornando tudo que o frontend precisa para decidir o próximo passo.

---

## Endpoints

### `POST /register`

Cria conta no Supabase Auth + perfil em `public.users` + registro de onboarding.

**Request**
```json
{
  "name": "Rafael Lima",
  "email": "rafael@email.com",
  "password": "minhasenha123",
  "cpf": "075.129.315-65",
  "whatsapp": "+5575982985771"
}
```

- `cpf` — opcional; armazenado como dígitos limpos (`07512931565`)
- `whatsapp` — opcional; normalizado para sempre incluir código do país (`5575982985771`)
- Números com 10 ou 11 dígitos recebem `55` automaticamente

**Response 201**
```json
{
  "user": {
    "id": "uuid-user-id",
    "name": "Rafael Lima",
    "email": "rafael@email.com"
  },
  "detail": "Verifique seu email para confirmar o cadastro."
}
```

**Erros**
| Status | Detalhe |
|---|---|
| 409 | Email já cadastrado |
| 409 | WhatsApp já cadastrado |
| 422 | CPF inválido |
| 422 | WhatsApp inválido |
| 500 | Erro ao criar conta |

**Comportamento interno**
1. Verifica duplicidade de email e WhatsApp em `public.users`
2. Cria usuário em `auth.users` via `supabase.auth.sign_up()`
3. Cria perfil em `public.users` com `plan_status = "trial"` e datas do trial calculadas
4. Cria registro em `public.onboarding` (`current_step = 1`, `completed = false`)
5. Cria cliente na AbacatePay (falha silenciosa — não bloqueia o registro)
6. **Rollback:** se o INSERT em `public.users` falhar, o usuário criado em `auth.users` é deletado

---

### `POST /login`

Autentica o usuário e retorna tokens + estado da conta.

**Request**
```json
{
  "email": "rafael@email.com",
  "password": "minhasenha123"
}
```

**Response 200**
```json
{
  "user": {
    "id": "uuid-user-id",
    "name": "Rafael Lima",
    "email": "rafael@email.com"
  },
  "onboarding_completed": false,
  "plan_status": "trial",
  "trial": {
    "starts_at": "2026-03-09T19:25:32Z",
    "ends_at": "2026-03-23T19:25:32Z",
    "days_remaining": 5
  },
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

- `trial` é `null` quando `plan_status = "active"`
- `plan_status`: `"trial"` | `"expired"` | `"active"`
- Se `plan_status == "trial"` e `trial_ends_at < now`, atualiza automaticamente para `"expired"` no banco antes de retornar

**Lógica do frontend após login**
```
onboarding_completed == false  → redirecionar para /onboarding
plan_status == "expired"       → redirecionar para /planos
plan_status == "trial"         → acesso liberado (exibir banner de trial)
plan_status == "active"        → acesso liberado
```

**Erros**
| Status | Detalhe |
|---|---|
| 401 | Email ou senha inválidos |
| 403 | Email ainda não confirmado. Verifique sua caixa de entrada. |
| 500 | Erro ao realizar login |

---

### `POST /refresh`

Renova o `access_token` usando o `refresh_token`.

**Request**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response 200**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

O `access_token` expira em **1 hora** (padrão Supabase). O frontend deve chamar este endpoint antes da expiração ou ao receber `401`.

**Erros**
| Status | Detalhe |
|---|---|
| 401 | Refresh token inválido ou expirado |

---

### `POST /logout`

Invalida a sessão no Supabase. Requer token no header.

**Header**
```
Authorization: Bearer <access_token>
```

**Response 200**
```json
{
  "detail": "Sessão encerrada com sucesso."
}
```

**Erros**
| Status | Detalhe |
|---|---|
| 401 | Token inválido ou ausente |
| 500 | Erro ao encerrar sessão |

---

### `POST /forgot-password`

Dispara email de redefinição de senha. Sempre retorna `200` independente de o email existir (evita enumeração de usuários).

**Request**
```json
{
  "email": "rafael@email.com"
}
```

**Response 200**
```json
{
  "detail": "Se este email estiver cadastrado, você receberá um link de redefinição."
}
```

---

### `POST /reset-password`

Redefine a senha usando o token OTP do link enviado por email.

**Request**
```json
{
  "token": "otp_token_do_link",
  "new_password": "novaSenha123"
}
```

- `token` — extraído da URL do link (`?token=xxx` ou `#access_token=xxx`)
- `new_password` — mínimo 8 caracteres

**Response 200**
```json
{
  "detail": "Senha redefinida com sucesso."
}
```

**Erros**
| Status | Detalhe |
|---|---|
| 400 | Link de redefinição inválido ou expirado. |
| 500 | Erro ao redefinir a senha. |

**Fluxo completo de recuperação**
```
1. Usuário clica "Esqueci minha senha"
2. Frontend → POST /auth/forgot-password { email }
3. Supabase envia email com link contendo token
4. Usuário clica no link → Frontend captura token da URL
5. Frontend → POST /auth/reset-password { token, new_password }
6. Supabase invalida o token após uso
```

---

## Validação JWT

Todos os endpoints protegidos exigem `Authorization: Bearer <access_token>`.

```python
# core/security.py
payload = jwt.decode(
    token,
    settings.SUPABASE_JWT_SECRET,
    algorithms=["HS256"],
    audience="authenticated",
)
# Campos extraídos:
# payload["sub"]   → user_id (UUID)
# payload["email"] → email do usuário
```

A validação verifica automaticamente: **expiração**, **audiência** e **assinatura**. Nenhuma chamada ao Supabase é feita — o JWT é self-contained.

---

## Trial

- Duração configurável via `TRIAL_DAYS` (padrão: `14` dias)
- Calculado no registro: `trial_ends_at = now + TRIAL_DAYS`
- Verificação ocorre **no login**: se `plan_status == "trial"` e `trial_ends_at < now` → atualiza para `"expired"`
- Acesso total durante o trial; bloqueio apenas após expiração sem plano ativo

---

## Tabelas relacionadas

### `public.users`

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | BIGINT | PK auto-gerado |
| `user_uuid` | UUID | FK para `auth.users` |
| `name` | TEXT | Nome completo |
| `email` | TEXT | Email (único) |
| `phone` | TEXT | WhatsApp com código do país (`5575982985771`) |
| `tax_id` | TEXT | CPF (apenas dígitos) |
| `active_bot` | BOOLEAN | Bot WhatsApp ativo |
| `plan_id` | INT | FK para `plans` (null durante trial) |
| `plan_status` | TEXT | `trial` \| `expired` \| `active` |
| `customer_id` | TEXT | ID do cliente na AbacatePay |
| `trial_starts_at` | TIMESTAMPTZ | Início do trial |
| `trial_ends_at` | TIMESTAMPTZ | Fim do trial |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

---

## Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `SUPABASE_URL` | Project URL |
| `SUPABASE_ANON_KEY` | Chave pública (sign_up, sign_in) |
| `SUPABASE_SERVICE_ROLE_KEY` | Chave de serviço — bypassa RLS (INSERT em public.users) |
| `SUPABASE_JWT_SECRET` | Segredo para validação local do JWT |
| `TRIAL_DAYS` | Duração do trial em dias (default: `14`) |

> `SUPABASE_SERVICE_ROLE_KEY` nunca deve ser exposta no frontend.
