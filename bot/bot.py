"""Telegram bot for docsAI.

Primary use case: the user photographs paper documents and sends the photos here.
- A single photo -> ingested as a one-page document.
- An album (media group) -> collected and ingested as ONE multi-page document.
- A file attachment (pdf/txt/md) -> ingested as an electronic document.
- Any text message -> a question to the verified RAG pipeline.
"""

import asyncio
import logging
import os
import sys

import httpx
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("docsai-bot")

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
ALBUM_SETTLE_SECONDS = 2.5

# media_group_id -> list of (position, bytes); Telegram delivers album photos
# as separate messages, so we buffer them briefly and flush as one document.
_albums: dict[str, list[tuple[int, bytes]]] = {}
_album_locks: dict[str, asyncio.Lock] = {}


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


def format_ingest(data: dict) -> str:
    pages = data.get("pages", 1)
    lines = [
        f"✅ Сохранено: «{data['title']}»",
        f"Категория: {data['category']}, страниц: {pages}, платежей: {data['payments']}",
    ]
    for warning in data.get("warnings", []):
        lines.append(f"⚠️ {warning}")
    if pages > 1:
        lines.append(
            "ℹ️ Альбом = страницы ОДНОГО документа. Разные документы отправляйте "
            "отдельными сообщениями или альбомами."
        )
    return "\n".join(lines)


async def ingest(update: Update, uploads: list[tuple[str, bytes, str]]) -> None:
    """POST files to the backend and report the result."""
    if not update.message:
        return
    await update.message.reply_text(
        f"📷 Обрабатываю ({len(uploads)} стр.)… это может занять минуту."
    )
    form_files = [("files", (name, content, mime)) for name, content, mime in uploads]
    async with httpx.AsyncClient(timeout=600) as client:
        try:
            response = await client.post(f"{BACKEND_URL}/api/documents", files=form_files)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = None
            try:
                detail = exc.response.json().get("detail")
            except Exception:
                pass
            await update.message.reply_text(f"❌ Не удалось обработать: {detail or exc}")
            return
        except httpx.HTTPError:
            logger.exception("Ingest failed")
            await update.message.reply_text("❌ Сервер недоступен, попробуйте позже.")
            return
    await update.message.reply_text(format_ingest(response.json()))


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.photo:
        return
    photo = message.photo[-1]  # the largest size Telegram offers
    file = await photo.get_file()
    content = bytes(await file.download_as_bytearray())

    group_id = message.media_group_id
    if group_id is None:
        await ingest(update, [("photo.jpg", content, "image/jpeg")])
        return

    # Album: buffer pages, flush once the album stops arriving.
    lock = _album_locks.setdefault(group_id, asyncio.Lock())
    async with lock:
        pages = _albums.setdefault(group_id, [])
        pages.append((message.message_id, content))
        is_first = len(pages) == 1
    if is_first:
        asyncio.create_task(_flush_album(update, group_id))


async def _flush_album(update: Update, group_id: str) -> None:
    previous = -1
    while True:
        await asyncio.sleep(ALBUM_SETTLE_SECONDS)
        current = len(_albums.get(group_id, []))
        if current == previous:
            break
        previous = current
    lock = _album_locks.pop(group_id, None)
    if lock is None:
        return
    async with lock:
        pages = sorted(_albums.pop(group_id, []))
    uploads = [
        (f"page{i + 1}.jpg", content, "image/jpeg") for i, (_, content) in enumerate(pages)
    ]
    if uploads:
        await ingest(update, uploads)


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.document:
        return
    document = message.document
    file = await document.get_file()
    content = bytes(await file.download_as_bytearray())
    await ingest(
        update,
        [
            (
                document.file_name or "document",
                content,
                document.mime_type or "application/octet-stream",
            )
        ],
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("docsAI Telegram bot started (photos + files + questions)")
    app.run_polling()


if __name__ == "__main__":
    main()
