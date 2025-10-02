"""Telegram bot for team-spark onboarding tasks.

This script uses pytelegrambotapi (telebot) to provide helpers that let
interested users apply to the team, contact admins, or collaborate with the
team on behalf of other clubs or student organizations.
"""
from __future__ import annotations

import logging
import os
from typing import Iterable

import telebot
from telebot import types


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TOKEN_ENV_VAR = "TELEGRAM_BOT_TOKEN"
TEAM_APPLICATION_FORM_URL = os.getenv("TEAM_APPLICATION_FORM_URL", "https://example.com/apply")
ADMIN_USERNAMES: Iterable[str] = tuple(
    username.strip() for username in os.getenv("TEAM_ADMIN_USERNAMES", "@team_admin").split(",") if username.strip()
)
COLLAB_FORM_URL = os.getenv("TEAM_COLLAB_FORM_URL", "https://example.com/collaborate")


def create_bot(token: str | None = None) -> telebot.TeleBot:
    """Create and return a configured TeleBot instance."""
    token = token or os.getenv(TOKEN_ENV_VAR)
    if not token:
        raise RuntimeError(
            f"Telegram bot token is required. Set the {TOKEN_ENV_VAR} environment variable or pass the token explicitly."
        )

    bot = telebot.TeleBot(token, parse_mode="HTML")
    return bot


def _apply_markup() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("Apply to Team Spark", url=TEAM_APPLICATION_FORM_URL))
    return markup


def _collab_markup() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("Collaboration Request", url=COLLAB_FORM_URL))
    return markup


def apply_to_team(bot: telebot.TeleBot, message: types.Message) -> None:
    """Send information and link for applying to the team."""
    response = (
        "🚀 <b>Ready to join Team Spark?</b>\n\n"
        "Fill out our application form and tell us about your skills, projects, and what excites you about working with the team."
    )
    bot.send_message(message.chat.id, response, reply_markup=_apply_markup())


def contact_admins(bot: telebot.TeleBot, message: types.Message) -> None:
    """Share direct contact options for team administrators."""
    if ADMIN_USERNAMES:
        admin_list = "\n".join(f"• {username}" for username in ADMIN_USERNAMES)
    else:
        admin_list = "No admins configured yet."

    response = (
        "👋 <b>Need to speak with an admin?</b>\n\n"
        "Reach out to us directly on Telegram:\n"
        f"{admin_list}\n\n"
        "You can send us a message with your questions, partnership ideas, or any support you need."
    )
    bot.send_message(message.chat.id, response)


def collaborate_with_team(bot: telebot.TeleBot, message: types.Message) -> None:
    """Provide collaboration information for other clubs or organizations."""
    response = (
        "🤝 <b>Collaborate with Team Spark</b>\n\n"
        "Are you part of another club or student organization? Let’s build something together!\n"
        "Share your proposal and we'll get back to you soon."
    )
    bot.send_message(message.chat.id, response, reply_markup=_collab_markup())


def register_handlers(bot: telebot.TeleBot) -> None:
    """Register command handlers on the provided bot instance."""

    @bot.message_handler(commands=["start", "help"])
    def send_welcome(message: types.Message) -> None:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(
            types.KeyboardButton("Apply to Team"),
            types.KeyboardButton("Contact Admins"),
            types.KeyboardButton("Collaborate with Team"),
        )

        response = (
            "✨ <b>Welcome to Team Spark!</b>\n\n"
            "Choose an option below or use the commands:\n"
            "• /apply - Apply to join the team\n"
            "• /admins - Contact the admins\n"
            "• /collaborate - Collaborate with Team Spark"
        )
        bot.send_message(message.chat.id, response, reply_markup=markup)

    @bot.message_handler(commands=["apply"])
    def handle_apply(message: types.Message) -> None:
        apply_to_team(bot, message)

    @bot.message_handler(commands=["admins"])
    def handle_admins(message: types.Message) -> None:
        contact_admins(bot, message)

    @bot.message_handler(commands=["collaborate"])
    def handle_collaborate(message: types.Message) -> None:
        collaborate_with_team(bot, message)

    @bot.message_handler(func=lambda message: message.text and message.text.lower() == "apply to team")
    def handle_text_apply(message: types.Message) -> None:
        apply_to_team(bot, message)

    @bot.message_handler(func=lambda message: message.text and message.text.lower() == "contact admins")
    def handle_text_admins(message: types.Message) -> None:
        contact_admins(bot, message)

    @bot.message_handler(func=lambda message: message.text and message.text.lower() == "collaborate with team")
    def handle_text_collaborate(message: types.Message) -> None:
        collaborate_with_team(bot, message)


def main() -> None:
    """Entry point to run the Telegram bot."""
    try:
        bot = create_bot()
    except RuntimeError as exc:
        logger.error("%s", exc)
        raise

    register_handlers(bot)
    logger.info("Bot is starting polling...")
    bot.infinity_polling()


if __name__ == "__main__":
    main()
