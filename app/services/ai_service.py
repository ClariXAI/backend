from __future__ import annotations

import structlog

from app.core.config import settings

logger = structlog.get_logger()


def _get_client():
    """Retorna cliente Anthropic ou None se API key não configurada."""
    if not settings.ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    except ImportError:
        logger.warning("anthropic_not_installed")
        return None


def get_emergency_fund_suggestion(
    target_amount: float,
    monthly_contribution: float,
    months: int,
    has_fund: bool,
) -> str:
    """Gera sugestão textual para meta de reserva de emergência."""
    fallback = (
        f"Parabéns! Sua reserva de emergência de R$ {target_amount:,.0f} já está em andamento."
        if has_fund
        else f"Com contribuições de R$ {monthly_contribution:,.0f}/mês, você atingirá "
             f"a reserva de emergência de R$ {target_amount:,.0f} em aproximadamente {months} meses."
    )

    client = _get_client()
    if not client:
        return fallback

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": (
                    f"Você é um consultor financeiro brasileiro. Gere uma mensagem motivacional "
                    f"curta (máx 2 frases) para um usuário que {'já tem' if has_fund else 'quer criar'} "
                    f"uma reserva de emergência de R$ {target_amount:,.0f}. "
                    f"{'Contribuição mensal sugerida: R$ ' + f'{monthly_contribution:,.0f}' + f', prazo: {months} meses.' if not has_fund else ''} "
                    f"Seja direto, positivo e prático. Responda somente a mensagem, sem prefixo."
                ),
            }],
        )
        return message.content[0].text.strip()
    except Exception as exc:
        logger.error("ai_emergency_fund_suggestion_failed", error=str(exc))
        return fallback


def get_goal_suggestion(
    title: str,
    target_amount: float,
    monthly_contribution: float,
    months: int,
) -> str:
    """Gera sugestão textual para uma meta financeira."""
    fallback = (
        f"Com contribuições de R$ {monthly_contribution:,.0f}/mês, "
        f"você atingirá a meta \"{title}\" de R$ {target_amount:,.0f} "
        f"em aproximadamente {months} meses."
    )

    client = _get_client()
    if not client:
        return fallback

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": (
                    f"Você é um consultor financeiro brasileiro. Gere uma mensagem motivacional "
                    f"curta (máx 2 frases) para um usuário com meta \"{title}\" de R$ {target_amount:,.0f}, "
                    f"contribuição mensal de R$ {monthly_contribution:,.0f} e prazo de {months} meses. "
                    f"Seja direto, positivo e prático. Responda somente a mensagem, sem prefixo."
                ),
            }],
        )
        return message.content[0].text.strip()
    except Exception as exc:
        logger.error("ai_goal_suggestion_failed", error=str(exc))
        return fallback
