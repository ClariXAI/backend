# Onboarding

Fluxo de 7 etapas obrigatório após o registro. Bloqueia o acesso ao resto da aplicação enquanto `completed = false`.

---

## Fluxo das etapas

| Etapa | Nome | Descrição |
|---|---|---|
| 1 | Renda Mensal | Usuário informa sua renda mensal líquida |
| 2 | Custo Mensal | Usuário informa o total de gastos mensais recorrentes |
| 3 | Categorias de Gastos | Seleciona categorias e recebe limites sugeridos proporcionais à renda |
| 4 | Reserva de Emergência | Informa se possui reserva; IA calcula meta e aporte ideal |
| 5 | Próximo Objetivo | Condicional — disponível apenas se `has_emergency_fund = true` |
| 6 | Tipo de Compromisso | Usuário seleciona o tipo: assinatura, cartão, empréstimo ou consórcio |
| 7 | Formulário do Compromisso | Preenche os dados do compromisso selecionado na etapa 6 |

> O progresso é salvo a cada etapa via `POST /api/v1/onboarding/`. O frontend pode retomar de onde parou usando `current_step` retornado pelo `GET`.

---

## Endpoints

Base: `/api/v1/onboarding`
Autenticação: `Authorization: Bearer <access_token>` em todos os endpoints.

---

### `GET /`

Busca os dados de onboarding do usuário autenticado.

**Response 200**
```json
{
  "income": 5000,
  "monthly_cost": 3500,
  "selected_categories": ["alimentacao", "moradia", "transporte"],
  "suggested_limits": {
    "alimentacao": 1000,
    "moradia": 1500,
    "transporte": 500
  },
  "has_emergency_fund": false,
  "emergency_fund_amount": null,
  "next_goal": null,
  "commitment": {
    "type": "assinatura",
    "data": {
      "title": "Netflix",
      "value": 39.9,
      "plan": "mensal",
      "due_date": "2026-03-05"
    }
  },
  "current_step": 7,
  "completed": false
}
```

**Erros**
| Status | Detalhe |
|---|---|
| 401 | Token inválido ou ausente |
| 404 | Onboarding não iniciado |

---

### `POST /`

Salva progresso parcial ou total do onboarding. Pode ser chamado a cada etapa.

- `current_step` é obrigatório (indica a etapa sendo salva).
- Todos os outros campos são opcionais — apenas os enviados são atualizados.
- Quando `income` + `selected_categories` são enviados, `suggested_limits` é calculado automaticamente e persistido.
- Quando `has_emergency_fund = false` + `income` + `monthly_cost` estão presentes, a resposta inclui o preview de `emergency_fund_goal` (calculado, ainda não salvo no DB).

**Request**
```json
{
  "income": 5000,
  "monthly_cost": 3500,
  "selected_categories": ["alimentacao", "moradia", "transporte"],
  "has_emergency_fund": false,
  "emergency_fund_amount": null,
  "next_goal": null,
  "commitment": {
    "type": "assinatura",
    "data": {
      "title": "Netflix",
      "value": 39.9,
      "plan": "mensal",
      "due_date": "2026-03-05"
    }
  },
  "current_step": 7
}
```

**Response 201**
```json
{
  "income": 5000,
  "monthly_cost": 3500,
  "selected_categories": ["alimentacao", "moradia", "transporte"],
  "suggested_limits": {
    "alimentacao": 1000,
    "moradia": 1500,
    "transporte": 500
  },
  "has_emergency_fund": false,
  "emergency_fund_amount": null,
  "emergency_fund_goal": {
    "title": "Reserva de Emergência",
    "target_amount": 21000,
    "current_amount": 0,
    "priority": "alta",
    "target_date": "2027-08-01",
    "monthly_contribution": 1000
  },
  "next_goal": null,
  "commitment": {
    "type": "assinatura",
    "data": {
      "title": "Netflix",
      "value": 39.9,
      "plan": "mensal",
      "due_date": "2026-03-05"
    }
  },
  "current_step": 7,
  "completed": false
}
```

> `emergency_fund_goal` aparece somente quando `has_emergency_fund = false` e é um preview para exibição no frontend — a meta real é criada no banco apenas ao chamar `PATCH /complete`.

**Erros**
| Status | Detalhe |
|---|---|
| 401 | Token inválido ou ausente |
| 404 | Onboarding não iniciado |
| 422 | Renda deve ser maior que zero |
| 422 | Custo mensal deve ser maior que zero |

---

### `PATCH /complete`

Finaliza o onboarding. Cria automaticamente no banco:

1. **Categorias** — uma para cada item em `selected_categories` com tipo `fixa` ou `variavel`
2. **Limites** — um por categoria com o valor de `suggested_limits`, vinculado ao mês atual
3. **Meta de Reserva de Emergência** — calculada com base em `has_emergency_fund`:
   - `false` → target = 6x custo mensal, prioridade `alta`, aporte e prazo calculados pela IA
   - `true` → target = valor informado em `emergency_fund_amount`, prioridade `baixa`
4. **Próxima meta** — criada se `next_goal` estiver preenchido no onboarding
5. **Compromisso** — criado na tabela correspondente ao `type` (subscriptions / credit_cards / loans / consortiums)

Ao final, marca `completed = true` e `completed_at` no registro de onboarding.

**Response 200**
```json
{
  "completed": true,
  "categories_created": 3,
  "limits_created": 3,
  "goals_created": [
    {
      "title": "Reserva de Emergência",
      "target_amount": 21000,
      "current_amount": 0,
      "priority": "alta"
    }
  ],
  "commitment_created": {
    "type": "assinatura",
    "title": "Netflix"
  },
  "message": "Onboarding finalizado com sucesso"
}
```

**Erros**
| Status | Detalhe |
|---|---|
| 400 | Dados de onboarding incompletos (income, monthly_cost ou selected_categories ausentes) |
| 401 | Token inválido ou ausente |
| 404 | Onboarding não iniciado |

---

### `GET /suggested-limits`

Calcula limites de gasto proporcionais à renda para as categorias informadas. Não persiste nada.

**Query Parameters**

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `income` | number | Sim | Renda mensal (ex: `5000`) |
| `categories` | string | Sim | Categorias separadas por vírgula (ex: `alimentacao,moradia`) |

**Response 200**
```json
{
  "alimentacao": 1000.0,
  "moradia": 1500.0,
  "transporte": 500.0
}
```

**Pesos por categoria**

| Categoria | Peso | Tipo |
|---|---|---|
| moradia | 30% | fixa |
| alimentacao | 20% | variavel |
| saude | 8% | variavel |
| transporte | 10% | variavel |
| energia | 5% | fixa |
| estudo | 5% | fixa |
| entretenimento | 5% | variavel |
| lazer | 5% | variavel |
| internet | 4% | fixa |
| agua | 3% | fixa |

> Categorias fora da lista acima recebem peso padrão de 5%.

---

### `POST /emergency-fund`

Calcula a meta de reserva de emergência. Usa IA (Claude Haiku) para gerar sugestão textual personalizada. Não persiste nada.

**Request**
```json
{
  "has_emergency_fund": false,
  "emergency_fund_amount": null,
  "income": 5000,
  "monthly_cost": 3500
}
```

**Response 200 — sem reserva**
```json
{
  "title": "Reserva de Emergência",
  "target_amount": 21000,
  "current_amount": 0,
  "priority": "alta",
  "target_date": "2027-08-01",
  "monthly_contribution": 1000,
  "ai_suggestion": "Com contribuições de R$ 1.000/mês, você atingirá sua reserva de emergência em 21 meses."
}
```

**Response 200 — já possui reserva**
```json
{
  "title": "Reserva de Emergência",
  "target_amount": 15000,
  "current_amount": 15000,
  "priority": "baixa",
  "target_date": null,
  "monthly_contribution": null,
  "ai_suggestion": "Parabéns! Sua reserva de emergência já está garantindo sua tranquilidade financeira."
}
```

**Lógica de cálculo**

- `target_amount` = 6 × `monthly_cost`
- `monthly_contribution` = `max((income - monthly_cost) × 30%, income × 10%)`
- `target_date` = hoje + ceil(target / contribution) meses

---

### `POST /next-goal`

Calcula uma meta de próximo objetivo com sugestão gerada por IA. Disponível apenas se `has_emergency_fund = true` no onboarding salvo. Não persiste — a meta é criada em `PATCH /complete`.

**Objetivos pré-definidos**

| `goal_id` | Título | Valor sugerido |
|---|---|---|
| `viagem_europa` | Viagem Europa | R$ 25.000 |
| `entrada_apartamento` | Entrada de Apartamento | R$ 50.000 |
| `novo_notebook` | Novo Notebook | R$ 8.000 |
| `outro` | Personalizado | definido pelo usuário |

**Request — objetivo pré-definido**
```json
{
  "goal_id": "viagem_europa",
  "custom_title": null,
  "custom_description": null,
  "custom_amount": null,
  "income": 5000,
  "monthly_cost": 3500
}
```

**Request — objetivo personalizado**
```json
{
  "goal_id": "outro",
  "custom_title": "Moto nova",
  "custom_description": "Honda CB 300",
  "custom_amount": 18000,
  "income": 5000,
  "monthly_cost": 3500
}
```

**Response 201**
```json
{
  "title": "Viagem Europa",
  "description": "Férias dos sonhos na Europa",
  "target_amount": 25000,
  "current_amount": 0,
  "priority": "alta",
  "target_date": "2027-10-01",
  "monthly_contribution": 500,
  "ai_suggestion": "Com R$ 500/mês, você realizará sua viagem dos sonhos em 50 meses!"
}
```

**Erros**
| Status | Detalhe |
|---|---|
| 400 | Reserva de emergência não está completa. Etapa de próximo objetivo não disponível. |
| 422 | Título é obrigatório para objetivo personalizado |
| 422 | Valor é obrigatório para objetivo personalizado |

---

## Tipos de compromisso

### `assinatura`
```json
{
  "type": "assinatura",
  "data": {
    "title": "Netflix",
    "value": 39.9,
    "plan": "mensal",
    "due_date": "2026-03-05"
  }
}
```

### `cartao`
```json
{
  "type": "cartao",
  "data": {
    "name": "Nubank",
    "bank": "Nu Pagamentos",
    "total_limit": 8000,
    "closing_day": 20,
    "due_day": 27
  }
}
```

### `emprestimo`
```json
{
  "type": "emprestimo",
  "data": {
    "creditor": "Banco do Brasil",
    "total_amount": 12000,
    "installments": 24,
    "monthly_payment": 550,
    "start_date": "2026-01-01"
  }
}
```

### `consorcio`
```json
{
  "type": "consorcio",
  "data": {
    "administrator": "Porto Seguro",
    "total_amount": 80000,
    "installments": 120,
    "monthly_payment": 720,
    "start_date": "2025-06-01"
  }
}
```

---

## Tabela no banco (`onboarding`)

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | BIGINT | PK auto-gerado |
| `user_uuid` | UUID | FK para `auth.users` |
| `monthly_income` | NUMERIC | Renda mensal (campo `income` na API) |
| `monthly_cost` | NUMERIC | Custo mensal |
| `selected_categories` | JSONB | Array de strings |
| `suggested_limits` | JSONB | Mapa `{categoria: valor}` |
| `has_emergency_fund` | BOOLEAN | Possui reserva de emergência |
| `emergency_fund_amount` | NUMERIC | Valor atual da reserva (quando `has_emergency_fund = true`) |
| `next_goal` | JSONB | Dados do próximo objetivo |
| `commitment` | JSONB | Dados do compromisso (type + data) |
| `current_step` | INT | Etapa atual (1–7) |
| `completed` | BOOLEAN | Onboarding finalizado |
| `completed_at` | TIMESTAMPTZ | Data de conclusão |
| `created_at` | TIMESTAMPTZ | Criado automaticamente no registro |
| `updated_at` | TIMESTAMPTZ | Atualizado a cada `POST /` |

> O registro é criado automaticamente com `current_step = 1` e `completed = false` durante o `POST /auth/register`.

---

## Hierarquia de bloqueio de acesso

```
Token JWT inválido → 401
Onboarding não concluído → 403 (redirecionar para /onboarding)
Trial expirado / sem plano → 402 (redirecionar para /planos)
Acesso liberado → 200
```
