Telegram Bot for F1 QA

This file explains how to run the Telegram bot which wraps the F1 QA CLI.

Prerequisites
- A virtual environment (optional but recommended). 
- An OpenAI API key in an `.env` file with `OPENAI_API_KEY` set.
- A Telegram Bot token (create with BotFather) stored in `.env` as `TELEGRAM_BOT_TOKEN`.

Install

Activate the venv and install requirements:

```powershell
.\f1_qa\Scripts\Activate
pip install -r requirements.txt
```

Run

```powershell
python telegram_bot.py
```

Notes
- On startup the bot calls `prepare_embeddings()` which may take several minutes as it fetches pages and computes embeddings (these are memoized to `embeddings.db` and Wikipedia fetches are cached via `cache.db`).
- If you'd rather prepare embeddings separately before starting the bot, you can run `python -c "from F1_QA import prepare_embeddings; prepare_embeddings()"` once; the memoization will speed subsequent runs.
- The bot replies to plain text messages; use `/start` to see a greeting.

Commands
- `/ask <query>` — Ask a question (text or RAG). Example: `/ask Who won the 2022 drivers championship?`
- `/help` — Show usage instructions.
- You can also send plain-text questions without the `/ask` prefix.

Test Questions (try these):
- Who came in 2nd at the British Grand Prix in 2022?
- Who won the 2022 Monaco f1 Grand Prix?
- What happened in the first lap of the 2022 British Grand Prix?
- Who finished 9th in the French Grand Prix in 2022?
- Who won the F1 drivers championship in 2022?

Notes
- On startup the bot calls `prepare_embeddings()` which may take several minutes as it fetches pages and computes embeddings (these are memoized to `embeddings.db` and Wikipedia fetches are cached via `cache.db`).
- If you'd rather prepare embeddings separately before starting the bot, you can run `python -c "from F1_QA import prepare_embeddings; prepare_embeddings()"` once; the memoization will speed subsequent runs.
- The bot replies to plain text messages; use `/start` to see a greeting.
