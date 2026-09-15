# Орёл или Решка — Telegram bot

## Railway
Set environment variable `BOT_TOKEN` to the new token from BotFather.
Start command: `python bot.py` (Railway will also detect the Procfile).

Stats are stored in SQLite. For durable production storage on Railway, attach a Volume and set `DB_PATH=/data/stats.db`.
