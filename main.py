"""Telegram bot for Team Spark onboarding and contact flows."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, Tuple

import telebot
from telebot import types


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TOKEN_ENV_VAR = "TELEGRAM_BOT_TOKEN"
TEAM_APPLICATION_FORM_URL = os.getenv("TEAM_APPLICATION_FORM_URL", "https://example.com/apply")
ADMIN_REGISTRATION_PASSWORD = os.getenv("TEAM_ADMIN_PASSWORD", "change-me")


@dataclass
class ContactThread:
    """Data tracked for a message exchanged between a visitor and the team."""

    user_chat_id: int
    user_message_id: int
    user_name: str
    message_text: str


@dataclass
class CollaborateFormSession:
    """State collected while guiding a collaborator through the intake form."""

    chat_id: int
    user_id: int
    name: str | None = None
    organization: str | None = None
    idea: str | None = None
    timeline: str | None = None
    contact_info: str | None = None


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


def register_handlers(bot: telebot.TeleBot) -> None:
    """Register command handlers on the provided bot instance."""

    admin_ids: set[int] = set()
    contact_threads: Dict[Tuple[int, int], ContactThread] = {}
    collaborate_sessions: Dict[int, CollaborateFormSession] = {}

    def _is_admin(user_id: int) -> bool:
        return user_id in admin_ids

    @bot.message_handler(commands=["start", "help"])
    def send_welcome(message: types.Message) -> None:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(
            types.KeyboardButton("Apply to Team"),
            types.KeyboardButton("Contact Team"),
            types.KeyboardButton("Collaborate with Team"),
        )

        response = (
            "✨ <b>Welcome to Team Spark!</b>\n\n"
            "Choose an option below or use the commands:\n"
            "• /apply - Apply to join the team\n"
            "• /contact &lt;message&gt; - Reach the coordination team\n"
            "• /collaborate - Collaborate with Team Spark"
        )
        bot.send_message(message.chat.id, response, reply_markup=markup)

    @bot.message_handler(commands=["apply"])
    def handle_apply(message: types.Message) -> None:
        apply_to_team(bot, message)

    @bot.message_handler(commands=["register"])
    def handle_register(message: types.Message) -> None:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "Please provide the password: /register &lt;password&gt;.")
            return

        password = parts[1].strip()
        if password != ADMIN_REGISTRATION_PASSWORD:
            bot.reply_to(message, "That password does not match our records.")
            return

        admin_ids.add(message.from_user.id)
        bot.reply_to(message, "You are now registered to receive team messages.")

    def _ensure_text(message: types.Message, next_handler, session: CollaborateFormSession) -> None:
        if message.content_type != "text" or not message.text:
            retry = bot.send_message(message.chat.id, "Please send a text response so we can continue.")
            bot.register_next_step_handler(
                retry,
                lambda msg, nh=next_handler, sess=session: _ensure_text(msg, nh, sess),
            )
            return
        next_handler(message, session)

    def _broadcast_to_admins(origin_message: types.Message, summary: str, ack_text: str) -> None:
        user = origin_message.from_user
        user_chat_id = origin_message.chat.id
        user_name = user.full_name or user.username or "Someone"

        bot.send_message(user_chat_id, ack_text)

        if not admin_ids:
            bot.send_message(
                user_chat_id,
                "We currently don't have anyone available, but your message has been saved. We'll reach out soon!",
            )
            return

        for admin_id in admin_ids:
            forwarded = bot.send_message(admin_id, summary)
            contact_threads[(forwarded.chat.id, forwarded.message_id)] = ContactThread(
                user_chat_id=user_chat_id,
                user_message_id=origin_message.message_id,
                user_name=user_name,
                message_text=summary,
            )

    @bot.message_handler(commands=["contact"])
    def handle_contact(message: types.Message) -> None:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            bot.reply_to(message, "Please send your request as /contact &lt;message&gt; so we can forward it.")
            return

        user = message.from_user
        user_name = user.full_name or user.username or "Someone"
        details = parts[1].strip()
        summary = (
            "📨 <b>New contact request</b>\n\n"
            f"From: {user_name} (ID: {user.id})\n"
            f"Chat ID: {message.chat.id}\n\n"
            f"Message: {details}\n\n"
            "Reply to this message to reach them through the bot."
        )

        _broadcast_to_admins(
            origin_message=message,
            summary=summary,
            ack_text="Thanks! Your message is on its way to the coordination team.",
        )

    @bot.message_handler(func=lambda msg: msg.text and msg.text.lower() == "apply to team")
    def handle_text_apply(message: types.Message) -> None:
        apply_to_team(bot, message)

    def _send_collaboration(session: CollaborateFormSession, origin_message: types.Message) -> None:
        collaborate_sessions.pop(session.user_id, None)
        user = origin_message.from_user
        user_name = user.full_name or user.username or "Someone"
        summary = (
            "🤝 <b>New collaboration request</b>\n\n"
            f"From: {user_name} (ID: {session.user_id})\n"
            f"Chat ID: {session.chat_id}\n\n"
            f"Name: {session.name}\n"
            f"Organization: {session.organization}\n"
            f"Idea: {session.idea}\n"
            f"Timeline: {session.timeline}\n"
            f"Contact info: {session.contact_info}\n\n"
            "Reply to this message to follow up with them."
        )

        _broadcast_to_admins(
            origin_message=origin_message,
            summary=summary,
            ack_text="Thanks! The team will review your collaboration idea and reply here soon.",
        )

    def _capture_timeline(message: types.Message, session: CollaborateFormSession) -> None:
        session.timeline = message.text.strip()
        prompt = bot.send_message(
            session.chat_id,
            "Great! What's the best way for us to reach you (email, Telegram @, etc.)?",
        )
        bot.register_next_step_handler(prompt, lambda msg: _ensure_text(msg, _capture_contact_info, session))

    def _capture_contact_info(message: types.Message, session: CollaborateFormSession) -> None:
        session.contact_info = message.text.strip()
        _send_collaboration(session, message)

    def _capture_idea(message: types.Message, session: CollaborateFormSession) -> None:
        session.idea = message.text.strip()
        prompt = bot.send_message(
            session.chat_id,
            "When would you like to collaborate?",
        )
        bot.register_next_step_handler(prompt, lambda msg: _ensure_text(msg, _capture_timeline, session))

    def _capture_organization(message: types.Message, session: CollaborateFormSession) -> None:
        session.organization = message.text.strip()
        prompt = bot.send_message(
            session.chat_id,
            "Awesome! Share a quick overview of your collaboration idea.",
        )
        bot.register_next_step_handler(prompt, lambda msg: _ensure_text(msg, _capture_idea, session))

    def _capture_name(message: types.Message, session: CollaborateFormSession) -> None:
        session.name = message.text.strip()
        prompt = bot.send_message(
            session.chat_id,
            "Which club, organization, or group are you representing?",
        )
        bot.register_next_step_handler(prompt, lambda msg: _ensure_text(msg, _capture_organization, session))

    @bot.message_handler(commands=["collaborate"])
    def handle_collaborate(message: types.Message) -> None:
        user_id = message.from_user.id
        if user_id in collaborate_sessions:
            bot.reply_to(message, "You're already filling out a collaboration request. Please finish that first.")
            return

        session = CollaborateFormSession(
            chat_id=message.chat.id,
            user_id=user_id,
        )
        collaborate_sessions[user_id] = session
        prompt = bot.reply_to(
            message,
            "Let's plan something together! First, what's your name?",
        )
        bot.register_next_step_handler(prompt, lambda msg: _ensure_text(msg, _capture_name, session))

    @bot.message_handler(func=lambda msg: msg.text and msg.text.lower() == "contact team")
    def handle_text_contact(message: types.Message) -> None:
        bot.reply_to(message, "Use /contact &lt;message&gt; to reach the coordination team.")

    @bot.message_handler(func=lambda msg: msg.text and msg.text.lower() == "collaborate with team")
    def handle_text_collaborate(message: types.Message) -> None:
        handle_collaborate(message)

    @bot.message_handler(content_types=["text"])
    def handle_admin_reply(message: types.Message) -> None:
        if not message.reply_to_message:
            return

        if not _is_admin(message.from_user.id):
            return

        thread_key = (message.reply_to_message.chat.id, message.reply_to_message.message_id)
        thread = contact_threads.get(thread_key)
        if not thread:
            return

        bot.send_message(thread.user_chat_id, f"💬 Team Spark: {message.text}")
        bot.reply_to(message, "Sent to the requester.")


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
