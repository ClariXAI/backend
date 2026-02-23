# Padrões de Commits — ClariX Backend 📜

## Visão Geral

Este projeto adota a convenção **Conventional Commits** combinada com **emojis semânticos** para manter um histórico de alterações claro, rastreável e amigável para automações (changelogs, versionamento semântico, CI/CD).

Cada mensagem de commit é validada automaticamente pelo hook `scripts/commit-msg.sh` instalado em `.git/hooks/commit-msg`.

---

## Formato

```
<emoji> <tipo>(<escopo>)?: <descrição curta>

[corpo opcional — detalhes, motivações, impactos]

[rodapé opcional — Refs, Reviewed-by, Co-authored-by]
```

| Parte | Obrigatório | Descrição |
|-------|-------------|-----------|
| `emoji` | Recomendado | Representação visual do tipo de alteração |
| `tipo` | **Sim** | Categoria da mudança (ver tabela abaixo) |
| `escopo` | Não | Módulo ou contexto afetado, entre parênteses |
| `descrição` | **Sim** | Resumo imperativo em até ~70 caracteres |
| `corpo` | Não | Explicação detalhada, separado por linha em branco |
| `rodapé` | Não | Referências a issues, reviewers, co-autores |

### Regras
- A **primeira linha** deve ter no máximo **72 caracteres**
- Use o **imperativo** na descrição: `adicionar`, `corrigir`, `remover` (não `adicionado`, `corrigi`)
- Sem ponto final na descrição
- Emojis podem ser inseridos como caractere (`✨`) ou código (`:sparkles:`)

---

## Tipos e Emojis

| Emoji | Código | Tipo | Quando usar |
|-------|--------|------|-------------|
| 🎉 | `:tada:` | `init` | Commit inicial do projeto ou módulo |
| ✨ | `:sparkles:` | `feat` | Novo recurso ou funcionalidade |
| 🐛 | `:bug:` | `fix` | Correção de bug |
| 📚 | `:books:` | `docs` | Alterações em documentação |
| 🧪 | `:test_tube:` | `test` | Criação ou alteração de testes |
| 📦 | `:package:` | `build` | Dependências, build, empacotamento |
| ⚡ | `:zap:` | `perf` | Melhoria de performance |
| 👌 | `:ok_hand:` | `style` | Formatação, lint, sem impacto funcional |
| ♻️ | `:recycle:` | `refactor` | Refatoração sem mudança de comportamento |
| 🔧 | `:wrench:` | `chore` | Configurações, scripts, tarefas auxiliares |
| 🧱 | `:bricks:` | `ci` | Integração contínua, pipelines, Docker |
| 🗃️ | `:card_file_box:` | `raw` | Dados brutos, seeds, configs de ambiente |
| 🧹 | `:broom:` | `cleanup` | Remoção de código comentado / morto |
| 🗑️ | `:wastebasket:` | `remove` | Exclusão de arquivos ou funcionalidades |
| 💥 | `:boom:` | `fix` | Reversão de mudanças problemáticas |
| 💡 | `:bulb:` | `docs` | Comentários explicativos no código |
| 🏷️ | `:label:` | — | Tipagem, ajustes de tipos |
| 🚀 | `:rocket:` | — | Deploy / publicação |

---

## Escopos Recomendados — ClariX

Use escopos para indicar o módulo afetado:

| Escopo | Onde usar |
|--------|-----------|
| `auth` | Autenticação, JWT, register, login |
| `onboarding` | Fluxo de onboarding |
| `profile` | Perfil do usuário |
| `categories` | Categorias financeiras |
| `transactions` | Transações |
| `credit-cards` | Cartões de crédito |
| `loans` | Empréstimos e financiamentos |
| `wallets` | Carteiras e contas |
| `goals` | Metas financeiras |
| `limits` | Limites de gastos |
| `ai` | Agente de IA |
| `core` | Config, middleware, segurança |
| `deps` | Dependências (requirements.txt) |
| `ci` | Pipelines, Docker, deploy |

---

## Exemplos Práticos

```bash
# Novo endpoint
git commit -m "✨ feat(auth): adicionar endpoint POST /auth/login"

# Correção de bug
git commit -m "🐛 fix(auth): corrigir validação de token JWT expirado"

# Documentação
git commit -m "📚 docs: documentar padrões de commits semânticos"

# Dependência adicionada
git commit -m "📦 build(deps): adicionar pydantic[email] ao requirements"

# Refatoração sem impacto funcional
git commit -m "♻️ refactor(auth): extrair lógica de format_phone para utils"

# Configuração de ambiente
git commit -m "🔧 chore: adicionar hook commit-msg para conventional commits"

# Testes
git commit -m "🧪 test(auth): adicionar testes para endpoint register"

# Remoção de código morto
git commit -m "🧹 cleanup(auth): remover comentários e prints de debug"

# Commit com corpo e rodapé
git commit -m "✨ feat(auth): implementar POST /auth/register

Fluxo completo: Supabase Auth sign_up → INSERT public.users
com plan_id=1 (Essencial), status_id=1 (Teste) → criação de
customer na AbacatePay → atualização de customer_id.

AbacatePay falha de forma silenciosa para não bloquear o registro.

Refs #12
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Configuração do Hook

O script `scripts/commit-msg.sh` valida automaticamente cada mensagem antes do commit ser criado. **Execute uma vez após clonar o repositório:**

```bash
# Instalar o hook
cp scripts/commit-msg.sh .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

### O que o hook valida

- Presença de um **tipo válido** (`feat`, `fix`, `docs`, etc.)
- Formato geral: `[emoji] tipo(escopo)?: descrição`
- Commits automáticos (`Merge`, `Revert`, `fixup!`) são ignorados

### Testando o hook

```bash
# Deve passar ✅
git commit -m "✨ feat(auth): adicionar endpoint de login"

# Deve rejeitar ❌
git commit -m "adicionei o login"
git commit -m "WIP"
git commit -m "update"
```

---

## Relacionamento com Versionamento Semântico

| Tipo | Incremento | Exemplo |
|------|-----------|---------|
| `feat` | **MINOR** — `1.1.0` | Nova funcionalidade |
| `fix` | **PATCH** — `1.0.1` | Correção de bug |
| `feat` com `BREAKING CHANGE` no rodapé | **MAJOR** — `2.0.0` | Quebra de compatibilidade |

---

## Referências

- [Conventional Commits](https://www.conventionalcommits.org)
- [Semantic Versioning](https://semver.org)
- [gitmoji](https://gitmoji.dev)
