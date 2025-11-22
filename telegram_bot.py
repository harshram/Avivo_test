import logging
import os
from dotenv import load_dotenv
import asyncio

# APScheduler on some installs expects pytz timezones; patch its utility to accept zoneinfo
try:
    import apscheduler.util as _apsutil
    from pytz import timezone as _pytz_timezone, utc as _pytz_utc
    from datetime import tzinfo as _tzinfo

    _orig_astimezone = _apsutil.astimezone

    def _patched_astimezone(obj):
        # If it's a tzinfo but lacks pytz methods, try to convert by name
        if isinstance(obj, _tzinfo) and (not hasattr(obj, 'localize') or not hasattr(obj, 'normalize')):
            name = getattr(obj, 'zone', None) or getattr(obj, 'key', None) or str(obj)
            try:
                return _pytz_timezone(name)
            except Exception:
                return _pytz_utc
        return _orig_astimezone(obj)

    _apsutil.astimezone = _patched_astimezone
except Exception:
    # If apscheduler isn't installed or patch fails, continue without change
    pass

# Support both python-telegram-bot v13 (Updater/Filters) and v20+ (Application/filters)
try:
    # v13
    from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
    PTB_V20 = False
except Exception:
    # v20+
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
    PTB_V20 = True

from F1_QA import prepare_embeddings, answer_question

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global placeholders populated at startup
embeddings = None
sections = None


def start(update, context):
    update.message.reply_text(
        "Hello! I'm the F1 QA bot. Use /ask <your question> or send a plain question. Send /help for usage."
    )


if PTB_V20:
    async def start_async(update, context):
        await update.message.reply_text(
            "Hello! I'm the F1 QA bot. Use /ask <your question> or send a plain question. Send /help for usage."
        )


def help_command(update, context):
    help_text = (
        "F1 QA Bot usage:\n"
        "/ask <query> — Ask a question (RAG or direct).\n"
        "/help — Show this help message.\n"
        "You can also send a plain text question without /ask.\n\n"
        "Test questions you can try:\n"
        "- Who came in 2nd at the British Grand Prix in 2022?\n"
        "- Who won the 2022 Monaco f1 Grand Prix?\n"
        "- What happened in the first lap of the 2022 British Grand Prix?\n"
        "- Who finished 9th in the French Grand Prix in 2022?\n"
        "- Who won the F1 drivers championship in 2022?\n"
        "(Use `/ask <question>` or just send the question as a message.)"
    )
    update.message.reply_text(help_text)


if PTB_V20:
    async def help_async(update, context):
        help_text = (
            "F1 QA Bot usage:\n"
            "/ask <query> — Ask a question (RAG or direct).\n"
            "/help — Show this help message.\n"
            "You can also send a plain text question without /ask.\n\n"
            "Test questions you can try:\n"
            "- Who came in 2nd at the British Grand Prix in 2022?\n"
            "- Who won the 2022 Monaco f1 Grand Prix?\n"
            "- What happened in the first lap of the 2022 British Grand Prix?\n"
            "- Who finished 9th in the French Grand Prix in 2022?\n"
            "- Who won the F1 drivers championship in 2022?\n"
            "(Use `/ask <question>` or just send the question as a message.)"
        )
        await update.message.reply_text(help_text)


def ask_command(update, context):
    """Handle `/ask <query>` commands."""
    global embeddings
    text = update.message.text or ""
    parts = text.split(None, 1)
    if len(parts) < 2 or not parts[1].strip():
        update.message.reply_text("Usage: /ask <your question>")
        return

    question = parts[1].strip()
    update.message.reply_text("Looking that up... please wait.")
    try:
        answer = answer_question(question, embeddings, max_documents=5)
        for chunk in (answer[i : i + 4000] for i in range(0, len(answer), 4000)):
            update.message.reply_text(chunk)
    except Exception as e:
        logger.exception("Error while answering question")
        update.message.reply_text(f"Sorry, an error occurred: {e}")


if PTB_V20:
    async def ask_async(update, context):
        global embeddings
        text = update.message.text or ""
        parts = text.split(None, 1)
        if len(parts) < 2 or not parts[1].strip():
            await update.message.reply_text("Usage: /ask <your question>")
            return

        question = parts[1].strip()
        await update.message.reply_text("Looking that up... please wait.")
        try:
            loop = asyncio.get_running_loop()
            answer = await loop.run_in_executor(None, answer_question, question, embeddings, 5)
            for chunk in (answer[i : i + 4000] for i in range(0, len(answer), 4000)):
                await update.message.reply_text(chunk)
        except Exception as e:
            logger.exception("Error while answering question")
            await update.message.reply_text(f"Sorry, an error occurred: {e}")


def handle_text(update, context):
    global embeddings
    question = update.message.text
    update.message.reply_text("Looking that up... please wait.")
    try:
        answer = answer_question(question, embeddings, max_documents=5)
        # reply in parts if too long
        for chunk in (answer[i : i + 4000] for i in range(0, len(answer), 4000)):
            update.message.reply_text(chunk)
    except Exception as e:
        logger.exception("Error while answering question")
        update.message.reply_text(f"Sorry, an error occurred: {e}")


if PTB_V20:
    async def handle_text_async(update, context):
        global embeddings
        question = update.message.text
        await update.message.reply_text("Looking that up... please wait.")
        try:
            loop = asyncio.get_running_loop()
            answer = await loop.run_in_executor(None, answer_question, question, embeddings, 5)
            for chunk in (answer[i : i + 4000] for i in range(0, len(answer), 4000)):
                await update.message.reply_text(chunk)
        except Exception as e:
            logger.exception("Error while answering question")
            await update.message.reply_text(f"Sorry, an error occurred: {e}")


def main():
    global embeddings, sections
    load_dotenv(".env")

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment. Please set it in .env or your env.")
        return

    # Prepare embeddings at startup (may take time)
    logger.info("Preparing embeddings (this may take several minutes)...")
    try:
        embeddings, sections = prepare_embeddings()
    except Exception as e:
        logger.exception("Failed to prepare embeddings")
        return
    logger.info("Embeddings prepared. Starting bot...")

    if not PTB_V20:
        # python-telegram-bot v13 API
        updater = Updater(token=token, use_context=True)
        dp = updater.dispatcher

        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("help", help_command))
        dp.add_handler(CommandHandler("ask", ask_command))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

        updater.start_polling()
        logger.info("Bot started (ptb v13). Press Ctrl-C to stop.")
        updater.idle()
    else:
        # python-telegram-bot v20+ API (async)
        app = ApplicationBuilder().token(token).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("ask", ask_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        logger.info("Bot started (ptb v20+). Press Ctrl-C to stop.")
        app.run_polling()


if __name__ == "__main__":
    main()
