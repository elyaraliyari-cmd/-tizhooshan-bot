"""
سرور webhook برای اجرا روی Render (رایگان و ۲۴ ساعته).
Render این فایل رو اجرا می‌کنه، نه bot.py را مستقیم.
"""
import os
import asyncio
from flask import Flask, request

from telegram import Update
from bot import build_application, init_db

TOKEN = os.environ.get("BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")  # Render خودش این را می‌سازد

flask_app = Flask(__name__)
init_db()
telegram_app = build_application()

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(telegram_app.initialize())
loop.run_until_complete(telegram_app.start())

if RENDER_URL:
    webhook_url = f"{RENDER_URL}/webhook/{TOKEN}"
    loop.run_until_complete(telegram_app.bot.set_webhook(webhook_url))
    print(f"Webhook تنظیم شد: {webhook_url}")


@flask_app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run_coroutine_threadsafe(telegram_app.process_update(update), loop)
    return "ok"


@flask_app.route("/", methods=["GET"])
def health():
    return "Bot is running ✅"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)
