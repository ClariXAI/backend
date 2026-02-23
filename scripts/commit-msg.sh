#!/bin/sh
# =============================================================================
# Hook: commit-msg — Validação de Conventional Commits com Emojis
# Projeto: ClariX Backend
#
# Instalação:
#   cp scripts/commit-msg.sh .git/hooks/commit-msg
#   chmod +x .git/hooks/commit-msg
# =============================================================================

MSG_FILE="$1"
commit_msg=$(cat "$MSG_FILE")

# ─── Ignorar commits automáticos ────────────────────────────────────────────
case "$commit_msg" in
  Merge\ *|Revert\ *|fixup\!*|squash\!*) exit 0 ;;
esac

# Ignorar linhas de comentário (commits com --verbose)
first_line=$(echo "$commit_msg" | grep -v "^#" | head -1)
[ -z "$first_line" ] && exit 0

# ─── Tipos válidos ────────────────────────────────────────────────────────────
TYPES="feat|fix|docs|test|build|perf|style|refactor|chore|ci|raw|cleanup|remove|init"

# ─── Validação ────────────────────────────────────────────────────────────────
# Aceita os formatos:
#   ✨ feat: descrição
#   ✨ feat(escopo): descrição
#   :sparkles: feat: descrição          (formato textual do emoji)
#   feat: descrição                     (sem emoji, também válido)

# grep -P (Perl regex) para suporte correto a emojis multi-byte UTF-8
# \S+ captura qualquer sequência não-espaço (incluindo emojis de 4 bytes)
if echo "$first_line" | grep -qP "^(:[a-z_]+: |\S+ )?(${TYPES})(\([^)]+\))?: .+"; then
  exit 0
fi

# ─── Mensagem de erro ─────────────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║        Mensagem de commit inválida! ❌            ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo ""
echo "  Formato esperado:"
echo "    <emoji> <tipo>(<escopo>)?: <descrição curta>"
echo ""
echo "  Exemplos válidos:"
echo "    ✨ feat: adicionar endpoint de login"
echo "    🐛 fix(auth): corrigir validação de token JWT"
echo "    📚 docs: documentar padrões de commit"
echo "    ♻️  refactor: simplificar auth service"
echo "    🔧 chore: configurar variáveis de ambiente"
echo "    🧪 test: adicionar testes para register"
echo ""
echo "  Tipos válidos:"
echo "    feat     ✨  Novo recurso"
echo "    fix      🐛  Correção de bug"
echo "    docs     📚  Documentação"
echo "    test     🧪  Testes"
echo "    build    📦  Dependências / build"
echo "    perf     ⚡  Performance"
echo "    style    👌  Formatação / estilo"
echo "    refactor ♻️   Refatoração"
echo "    chore    🔧  Configuração / tarefas"
echo "    ci       🧱  Integração contínua"
echo "    raw      🗃️   Dados / configs"
echo "    cleanup  🧹  Limpeza de código"
echo "    remove   🗑️   Remoção de arquivos"
echo "    init     🎉  Commit inicial"
echo ""
echo "  Sua mensagem: \"$first_line\""
echo ""
exit 1
