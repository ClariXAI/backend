# ClariX API — Documentação

FastAPI + Supabase (PostgreSQL). Arquitetura em camadas: Router → Service → Repository → Supabase.

Base URL: `http://localhost:8000`
Prefixo: `/api/v1`

---

## Módulos implementados

| Módulo | Prefixo | Arquivo | Status |
|---|---|---|---|
| Auth | `/api/v1/auth` | [auth.md](auth.md) | Implementado |
| Onboarding | `/api/v1/onboarding` | [onboarding.md](onboarding.md) | Implementado |
| Perfil | `/api/v1/profile` | [profile.md](profile.md) | Implementado |
| Categorias | `/api/v1/categories` | [categories.md](categories.md) | Implementado |

---

## Todos os endpoints

### Auth
| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| POST | `/auth/register` | Público | Cria conta |
| POST | `/auth/login` | Público | Autentica e retorna tokens |
| POST | `/auth/refresh` | Público | Renova access_token |
| POST | `/auth/logout` | JWT | Invalida sessão |
| POST | `/auth/forgot-password` | Público | Envia email de redefinição |
| POST | `/auth/reset-password` | Público | Redefine senha via token OTP |

### Onboarding
| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| GET | `/onboarding/` | JWT | Busca dados e progresso |
| POST | `/onboarding/` | JWT | Salva progresso parcial ou total |
| PATCH | `/onboarding/complete` | JWT | Finaliza e cria categorias/metas/compromisso |
| GET | `/onboarding/suggested-limits` | JWT | Calcula limites por categoria |
| POST | `/onboarding/emergency-fund` | JWT | Calcula meta de reserva de emergência (IA) |
| POST | `/onboarding/next-goal` | JWT | Calcula próxima meta financeira (IA) |

### Perfil
| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| GET | `/profile/` | JWT | Dados do perfil |
| PUT | `/profile/` | JWT | Atualiza nome e telefone |
| PUT | `/profile/plan` | JWT | Altera plano de assinatura |
| GET | `/profile/payments` | JWT | Histórico de pagamentos |

### Categorias
| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| GET | `/categories/` | JWT | Lista categorias (filtro opcional por tipo) |
| POST | `/categories/` | JWT | Cria nova categoria |
| PUT | `/categories/{id}` | JWT | Atualiza categoria |
| DELETE | `/categories/{id}` | JWT | Remove categoria |

---

## Autenticação

Todos os endpoints marcados com **JWT** exigem:

```
Authorization: Bearer <access_token>
```

O `access_token` é obtido via `POST /auth/login` ou `POST /auth/refresh`. Expira em **1 hora**.

---

## Hierarquia de acesso

```
Token JWT inválido/ausente  → 401
Onboarding não concluído    → 403  (frontend redireciona para /onboarding)
Trial expirado / sem plano  → 402  (frontend redireciona para /planos)
Acesso liberado             → 200
```

---

## Stack técnica

| Componente | Tecnologia |
|---|---|
| Framework | FastAPI |
| Banco de dados | Supabase (PostgreSQL) |
| Autenticação | Supabase Auth (JWT HS256) |
| Validação | Pydantic v2 |
| Logging | structlog |
| Pagamentos SaaS | AbacatePay |
| IA | Anthropic Claude (Haiku) |
| Tarefas agendadas | APScheduler |

---

## Estrutura do projeto

```
backend/
├── app/
│   ├── api/v1/          # Routers (thin layer)
│   │   ├── auth.py
│   │   ├── onboarding.py
│   │   └── profile.py
│   ├── services/        # Lógica de negócio
│   │   ├── auth_service.py
│   │   ├── onboarding_service.py
│   │   ├── profile_service.py
│   │   └── ai_service.py
│   ├── repositories/    # Acesso ao banco (Supabase client)
│   │   ├── user_repository.py
│   │   ├── onboarding_repository.py
│   │   ├── category_repository.py
│   │   ├── goal_repository.py
│   │   ├── limit_repository.py
│   │   ├── subscription_repository.py
│   │   ├── credit_card_repository.py
│   │   ├── loan_repository.py
│   │   ├── consortium_repository.py
│   │   └── user_plan_subscription_repository.py
│   ├── schemas/         # Pydantic schemas
│   │   ├── auth.py
│   │   ├── onboarding.py
│   │   └── profile.py
│   └── core/
│       ├── config.py        # Settings via pydantic-settings
│       ├── dependencies.py  # get_current_user, get_supabase_client
│       ├── security.py      # verify_supabase_token
│       ├── exceptions.py    # Handlers globais
│       └── middleware.py    # CORS, logging
├── docs/                # Esta documentação
└── requirements.txt
```

---

## Variáveis de ambiente (`.env`)

```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=seu-jwt-secret

ABACATEPAY_API_KEY=...
ABACATEPAY_BASE_URL=https://api.abacatepay.com

ANTHROPIC_API_KEY=sk-ant-...

TRIAL_DAYS=14
DEBUG=true
```
