"""Telegram bot: forwards questions to the docsAI backend and replies with the
verified answer, sources, and confidence score."""

import logging
import os
import sys

import httpx
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("docsai-bot")

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


def format_answer(data: dict) -> str:
    lines = [data["answer"], ""]
    if data.get("sources"):
        lines.append("📄 Источники:")
        for s in data["sources"]:
            location = f", стр. {s['page']}" if s.get("page") else ""
            section = f" — {s['section']}" if s.get("section") else ""
            lines.append(f"• {s['document_title']}{section}{location}")
    lines.append(f"\n🎯 Уверенность: {data.get('confidence', 0)}%")
    for warning in data.get("warnings", []):
        lines.append(f"⚠️ {warning}")
    return "\n".join(lines)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    async with httpx.AsyncClient(timeout=300) as client:
        try:
            response = await client.post(
                f"{BACKEND_URL}/api/query", json={"question": update.message.text}
            )
            response.raise_for_status()
        except httpx.HTTPError:
            logger.exception("Backend query failed")
            await update.message.reply_text("Не удалось получить ответ, попробуйте позже.")
            return
    await update.message.reply_text(format_answer(response.json()))


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        logger.info("TELEGRAM_BOT_TOKEN is not set — bot disabled, exiting.")
        sys.exit(0)
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("docsAI Telegram bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
