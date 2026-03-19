# Categorias

CRUD de categorias de transações do usuário. Apenas os tipos `fixa` e `variavel` são suportados.

Base: `/api/v1/categories`
Autenticação: `Authorization: Bearer <access_token>` em todos os endpoints.

---

## Endpoints

### `GET /`

Lista todas as categorias do usuário com contagem e valor total de transações vinculadas.

**Query Parameters**

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `type` | string | Não | Filtrar por tipo: `fixa` ou `variavel` |

**Response 200**
```json
{
  "data": [
    {
      "id": 1,
      "name": "Alimentação",
      "icon": "fork-knife",
      "color": "bg-orange-500",
      "type": "variavel",
      "transaction_count": 12,
      "total_amount": 1850.00
    },
    {
      "id": 2,
      "name": "Moradia",
      "icon": "house",
      "color": "bg-blue-500",
      "type": "fixa",
      "transaction_count": 1,
      "total_amount": 1500.00
    }
  ]
}
```

- `transaction_count` — número de transações vinculadas à categoria
- `total_amount` — soma dos valores das transações vinculadas
- Retorna `0` para ambos quando não há transações

**Erros**
| Status | Detalhe |
|---|---|
| 401 | Token inválido ou ausente |

---

### `POST /`

Cria uma nova categoria personalizada.

**Request**
```json
{
  "name": "Lazer",
  "icon": "gamepad",
  "color": "bg-pink-500",
  "type": "variavel"
}
```

Todos os campos são obrigatórios.

- `icon` — nome do ícone (ex: `"fork-knife"`, `"car"`, `"house"`)
- `color` — classe Tailwind (ex: `"bg-orange-500"`, `"bg-blue-600"`)
- `type` — `"fixa"` ou `"variavel"`

**Response 201**
```json
{
  "id": 10,
  "name": "Lazer",
  "icon": "gamepad",
  "color": "bg-pink-500",
  "type": "variavel",
  "transaction_count": 0,
  "total_amount": 0
}
```

**Erros**
| Status | Detalhe |
|---|---|
| 401 | Token inválido ou ausente |
| 409 | Categoria com este nome já existe |
| 422 | Campos obrigatórios ausentes ou inválidos |

> A verificação de nome duplicado é **case-insensitive** — "Alimentação" e "alimentação" são consideradas iguais.

---

### `PUT /{id}`

Atualiza uma categoria existente. Todos os campos são opcionais — apenas os enviados são atualizados.

**Path Parameters**

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `id` | integer | ID da categoria |

**Request**
```json
{
  "name": "Lazer e Diversão",
  "color": "bg-pink-600"
}
```

**Response 200**

Mesmo formato do `POST /`.

**Erros**
| Status | Detalhe |
|---|---|
| 401 | Token inválido ou ausente |
| 404 | Categoria não encontrada |
| 409 | Categoria com este nome já existe |

---

### `DELETE /{id}`

Remove uma categoria. Transações vinculadas perdem a referência (`category_id` fica `null`).

**Path Parameters**

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `id` | integer | ID da categoria |

**Response 200**
```json
{
  "message": "Categoria removida com sucesso"
}
```

**Erros**
| Status | Detalhe |
|---|---|
| 401 | Token inválido ou ausente |
| 404 | Categoria não encontrada |

---

## Tabela no banco (`public.categories`)

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER | PK auto-gerado |
| `user_uuid` | UUID | FK para `auth.users` (nullable para categorias globais futuras) |
| `name` | TEXT NOT NULL | Nome da categoria |
| `icon` | TEXT NOT NULL | Nome do ícone para o frontend |
| `color` | TEXT NOT NULL | Classe de cor Tailwind |
| `type` | TEXT NOT NULL | `fixa` \| `variavel` |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | Atualizado automaticamente via trigger |

**Constraint de tipo:**
```sql
CHECK (type = ANY (ARRAY['fixa'::text, 'variavel'::text]))
```

**Index:**
```sql
idx_categories_user_type ON (user_uuid, type)
```

---

## Criação automática via onboarding

Durante o `PATCH /onboarding/complete`, categorias são criadas automaticamente para cada item em `selected_categories`. O tipo é atribuído com base no seguinte mapeamento:

| Categoria | Tipo |
|---|---|
| `moradia`, `agua`, `energia`, `internet`, `estudo` | `fixa` |
| `alimentacao`, `transporte`, `saude`, `entretenimento`, `lazer` | `variavel` |

Categorias criadas via onboarding seguem o mesmo modelo — podem ser editadas e deletadas pelo usuário normalmente.
