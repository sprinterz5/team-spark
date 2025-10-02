
from __future__ import annotations

import logging
import os

import telebot
from telebot import types


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TOKEN_ENV_VAR = "TELEGRAM_BOT_TOKEN"
TEAM_APPLICATION_FORM_URL = os.getenv("TEAM_APPLICATION_FORM_URL", "https://example.com/apply")


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

def apply_to_team(bot: telebot.TeleBot, message: types.Message) -> None:
    """Send information and link for applying to the team."""
    response = (
        "🚀 <b>Ready to join Team Spark?</b>\n\n"
        "Fill out our application form and tell us about your skills, projects, and what excites you about working with the team."
    )
    bot.send_message(message.chat.id, response, reply_markup=_apply_markup())

    @bot.message_handler(commands=["start", "help"])
    def send_welcome(message: types.Message) -> None:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(
            types.KeyboardButton("Apply to Team"),
            types.KeyboardButton("Collaborate with Team"),
        )

        response = (
            "✨ <b>Welcome to Team Spark!</b>\n\n"
            "Choose an option below or use the commands:\n"
            "• /apply - Apply to join the team\n"
            "• /collaborate - Collaborate with Team Spark"
        )
        bot.send_message(message.chat.id, response, reply_markup=markup)

    @bot.message_handler(commands=["apply"])
    def handle_apply(message: types.Message) -> None:
        apply_to_team(bot, message)



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
