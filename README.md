# Telegram Bot for F1 QA

This document explains how to run the Telegram bot that wraps the F1 QA CLI.

## Prerequisites
- **Virtual environment (recommended):** the repo includes a `f1_qa` venv you can use.
- **OpenAI API key:** set `OPENAI_API_KEY` in a `.env` file at the project root.
- **Telegram Bot token:** create a bot with BotFather and set `TELEGRAM_BOT_TOKEN` in `.env`.

## Install
1. Activate the virtual environment (PowerShell):

```powershell
.\f1_qa\Scripts\Activate
```

2. Install required packages:

```powershell
pip install -r requirements.txt
```

## Run

Start the bot:

```powershell
python telegram_bot.py
```

The bot will prepare embeddings on first run (may take several minutes). Embeddings and HTTP fetches are memoized to `embeddings.db` and `cache.db` to speed subsequent runs.

## Commands
- **/ask <query>** — Ask a question (RAG or direct). Example: `/ask Who won the 2022 drivers championship?`
- **/help** — Show usage instructions and sample test questions.
- You may also send plain-text questions without `/ask`.

## Test Questions (try these)
- Who came in 2nd at the British Grand Prix in 2022?
- Who won the 2022 Monaco F1 Grand Prix?
- What happened in the first lap of the 2022 British Grand Prix?
- Who finished 9th in the French Grand Prix in 2022?
- Who won the F1 drivers championship in 2022?

## Tips & Notes
- Preparing embeddings may take several minutes the first time.
- To precompute embeddings without starting the bot:

```powershell
python -c "from F1_QA import prepare_embeddings; prepare_embeddings()"
```

- Keep `embeddings.db` and `cache.db` (they speed up future runs).These files are added to .gitignore

## Screenshot  

  <img width="701" height="832" alt="image" src="https://github.com/user-attachments/assets/32696e3a-a57c-45a1-b015-f8f0a6e0304c" />

