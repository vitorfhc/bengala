"""Portuguese message templates for the Bengala bot."""

from __future__ import annotations

from bengala.models import PlayerScore


def _medal(position: int) -> str:
    """Return medal emoji for top 3 positions."""
    if position == 1:
        return "🥇"
    if position == 2:
        return "🥈"
    if position == 3:
        return "🥉"
    return ""


def _points_label(score: int) -> str:
    """Return 'ponto' or 'pontos' based on score."""
    return "ponto" if score == 1 else "pontos"


def format_final_scoreboard(
    forbidden_word: str,
    scores: list[PlayerScore],
) -> str:
    """Format the end-of-round scoreboard message."""
    lines: list[str] = [
        "🏆 Fim da rodada! Placar do dia:",
        f'🤫 A palavra proibida era: "{forbidden_word}"',
        "",
    ]

    if not scores:
        lines.append("Nenhum jogador participou desta rodada.")
    else:
        for i, score in enumerate(scores, 1):
            medal = _medal(i)
            prefix = f"{medal} " if medal else ""
            muted_tag = " (bengalado)" if score.muted else ""
            muted_icon = "🤡 " if score.muted else ""
            lines.append(
                f"{muted_icon}{prefix}{i}º — @{score.username} — "
                f"{score.score} {_points_label(score.score)}{muted_tag}"
            )

    lines.append("")
    lines.append("Boa sorte na próxima rodada! 🎮")
    return "\n".join(lines)


def format_partial_scoreboard(scores: list[PlayerScore]) -> str:
    """Format the in-progress scoreboard (no mute info revealed)."""
    lines: list[str] = ["📊 Placar parcial da rodada:", ""]

    if not scores:
        lines.append("Nenhum jogador participou ainda desta rodada.")
    else:
        for i, score in enumerate(scores, 1):
            medal = _medal(i)
            prefix = f"{medal} " if medal else ""
            lines.append(
                f"{prefix}{i}º — @{score.username} — "
                f"{score.score} {_points_label(score.score)}"
            )

    lines.append("")
    lines.append("A rodada continua! 🎮")
    return "\n".join(lines)


def format_rules() -> str:
    """Format the game rules message."""
    return (
        "📜 **Bengala — Regras do Jogo**\n"
        "\n"
        "🎯 **O que é?**\n"
        "Bengala é um jogo diário onde uma palavra proibida secreta é "
        "escolhida a cada dia. Converse normalmente, mas cuidado — se "
        "você disser a palavra proibida, será bengalado!\n"
        "\n"
        "🔤 **Como a palavra é escolhida?**\n"
        "A palavra proibida é selecionada automaticamente a partir das "
        "mensagens recentes do canal. Ninguém sabe qual é a palavra até "
        "o placar ser revelado no dia seguinte.\n"
        "\n"
        "🤡 **O que acontece se eu disser a palavra proibida?**\n"
        "Seu apelido no servidor vira `🤡 <seu nome> - bengalado` até o "
        "fim da rodada — todo mundo vai ver. O apelido original é "
        "restaurado quando uma nova rodada começa.\n"
        "\n"
        "📊 **Como os pontos são calculados?**\n"
        "Cada palavra única (com 4+ caracteres, excluindo stop words) "
        "que você enviar conta como 1 ponto. Jogadores bengalados "
        "também pontuam, com base nas mensagens enviadas antes de "
        "serem bengalados.\n"
        "\n"
        "⏰ **Quando o placar é revelado?**\n"
        "Todos os dias às 06h00 UTC, o placar da rodada anterior é "
        "divulgado, a palavra proibida é revelada, os apelidos são "
        "restaurados, e uma nova rodada começa automaticamente.\n"
        "\n"
        "📋 **Comandos disponíveis:**\n"
        "• `/rules` — Exibe estas regras\n"
        "• `/placar` — Mostra o placar parcial da rodada atual\n"
    )


def format_mute_notice() -> str:
    """Format the ephemeral punishment notification."""
    return (
        "🤡 Você foi bengalado!!! Que delicia!!! "
        "Seu apelido agora tem um palhaço grudado nele até o fim da "
        "rodada — todo mundo vai ver. Só você está vendo esta "
        "mensagem, mas o apelido... esse não tem como esconder."
    )


def format_already_muted_notice() -> str:
    """Format the ephemeral notice for already-punished players."""
    return (
        "😂 Você tentou dizer a palavra proibida de novo... "
        "mas já está bengalado! Olha só o seu apelido, palhaço!"
    )


def format_secret_word(word: str) -> str:
    """Format the ephemeral secret word reveal for admins."""
    return (
        f'🤫 A palavra proibida de hoje é: **"{word}"**. '
        f"Só você está vendo esta mensagem."
    )


def format_no_active_round() -> str:
    """Format message when no round is active."""
    return "⚠️ Nenhuma rodada ativa no momento. Nenhuma palavra foi selecionada ainda."


def format_no_permission() -> str:
    """Format message for unauthorized access."""
    return "❌ Você não tem permissão para usar este comando."


def format_restart_confirmation() -> str:
    """Format the ephemeral restart confirmation for admins."""
    return (
        "✅ Jogo reiniciado com sucesso! A próxima palavra foi selecionada. "
        "O próximo ciclo automático ocorre às 06h00 UTC."
    )
