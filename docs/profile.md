# Perfil

Gerencia dados pessoais, plano de assinatura e histórico de pagamentos do usuário autenticado.

Base: `/api/v1/profile`
Autenticação: `Authorization: Bearer <access_token>` em todos os endpoints.

---

## Endpoints

### `GET /`

Retorna o perfil completo do usuário.

**Response 200**
```json
{
  "id": "uuid-user-id",
  "name": "Rafael Lima",
  "email": "rafael@email.com",
  "cpf": "075.129.315-65",
  "phone": "5575982985771",
  "plan": "trial",
  "billing_period": null,
  "onboarding_completed": false,
  "created_at": "2026-03-09T19:25:34Z"
}
```

- `cpf` — formatado como `000.000.000-00` (armazenado como dígitos no banco)
- `phone` — retornado como armazenado (WhatsApp com código do país)
- `plan` — `"trial"` | `"essential"` | `"premium"`
- `billing_period` — `"mensal"` | `"anual"` | `null` (durante trial ou sem assinatura ativa)

**Erros**
| Status | Detalhe |
|---|---|
| 401 | Token inválido ou ausente |
| 404 | Perfil não encontrado |

---

### `PUT /`

Atualiza nome e/ou telefone. O email **não pode ser alterado** por este endpoint.

**Request**
```json
{
  "name": "Rafael Lima Barreto",
  "phone": "5575981891893"
}
```

Todos os campos são opcionais — apenas os enviados são atualizados.

**Response 200**

Mesmo formato do `GET /`.

**Erros**
| Status | Detalhe |
|---|---|
| 401 | Token inválido ou ausente |
| 404 | Perfil não encontrado |
| 422 | `name` menor que 2 caracteres |

> A alteração de email requer fluxo separado via Supabase Auth (confirmação por email). Não implementado neste endpoint.

---

### `PUT /plan`

Altera o plano de assinatura e/ou período de cobrança.

**Request**
```json
{
  "plan": "premium",
  "billing_period": "anual"
}
```

- `plan` — `"essential"` | `"premium"`
- `billing_period` — `"mensal"` | `"anual"`

**Response 200**
```json
{
  "plan": "premium",
  "billing_period": "anual",
  "price": 478.80,
  "next_billing_date": "2027-03-18T00:00:00Z",
  "message": "Plano atualizado com sucesso"
}
```

- `price` — valor total cobrado: mensal = preço mensal; anual = preço mensal anual × 12

**Tabela de preços**

| Plano | Mensal | Anual (total) |
|---|---|---|
| Essential | R$ 29,90/mês | R$ 238,80/ano (R$ 19,90×12) |
| Premium | R$ 49,90/mês | R$ 478,80/ano (R$ 39,90×12) |

**Comportamento interno**
1. Cria registro em `user_plan_subscriptions` com `status = "pending"`
2. Atualiza `users.plan_id` e `users.plan_status = "active"` de forma otimista
3. Confirmação final do pagamento ocorre via webhook da **AbacatePay**

**Erros**
| Status | Detalhe |
|---|---|
| 400 | Plano inválido. Opções: essential, premium |
| 401 | Token inválido ou ausente |

---

### `GET /payments`

Retorna o histórico de pagamentos com paginação.

**Query Parameters**

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `page` | integer | `1` | Página (mínimo: 1) |
| `limit` | integer | `10` | Itens por página (máximo: 100) |

**Response 200**
```json
{
  "data": [
    {
      "id": 1,
      "date": "2026-02-01T00:00:00Z",
      "amount": 49.90,
      "status": "active",
      "method": "Cartão de Crédito",
      "invoice": "charge_abc123"
    },
    {
      "id": 2,
      "date": "2026-01-01T00:00:00Z",
      "amount": 49.90,
      "status": "active",
      "method": "PIX",
      "invoice": "charge_xyz789"
    }
  ],
  "total": 2,
  "page": 1,
  "limit": 10
}
```

- `status` — `"pending"` | `"active"` | `"cancelled"` | `"expired"` | `"failed"`
- `method` — `"PIX"` | `"Cartão de Crédito"` | `null`
- `invoice` — `abacatepay_charge_id` quando disponível

---

## Tabelas relacionadas

### `public.users`

Ver [auth.md](auth.md#tabelaspúblicausers) para a estrutura completa.

Campos relevantes para perfil:

| Coluna | Tipo | Descrição |
|---|---|---|
| `name` | TEXT | Atualizável via `PUT /` |
| `phone` | TEXT | Atualizável via `PUT /` |
| `tax_id` | TEXT | CPF (somente leitura) |
| `plan_id` | INT | FK para `plans` — atualizado em `PUT /plan` |
| `plan_status` | TEXT | `trial` \| `expired` \| `active` |

### `public.plans`

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | INT | PK |
| `name` | TEXT | `Essential` \| `Premium` |
| `price_monthly` | NUMERIC | Preço mensal |
| `price_annual` | NUMERIC | Preço mensal equivalente no plano anual |
| `abacatepay_product_monthly_id` | TEXT | ID do produto mensal na AbacatePay |
| `abacatepay_product_annual_id` | TEXT | ID do produto anual na AbacatePay |

### `public.user_plan_subscriptions`

Histórico de assinaturas de plano (pagamentos SaaS — não confundir com `subscriptions` que são assinaturas financeiras do usuário como Netflix).

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | BIGINT | PK |
| `user_uuid` | UUID | FK para `auth.users` |
| `plan_id` | INT | FK para `plans` |
| `recurrence` | TEXT | `mensal` \| `anual` |
| `status` | TEXT | `pending` \| `active` \| `cancelled` \| `expired` \| `failed` |
| `amount_paid` | NUMERIC | Valor pago |
| `payment_method` | TEXT | `PIX` \| `CARD` |
| `abacatepay_charge_id` | TEXT | ID da cobrança na AbacatePay |
| `abacatepay_billing_id` | TEXT | ID do billing na AbacatePay |
| `starts_at` | TIMESTAMPTZ | Início do período |
| `ends_at` | TIMESTAMPTZ | Fim do período |
| `created_at` | TIMESTAMPTZ | |
