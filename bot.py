"""
ربات تیزهوشان + پومودورو + تسک
اجرا: python bot.py (لوکال با polling) یا از طریق webhook روی Render (server.py)
"""
import os
import sqlite3
import asyncio
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters, ConversationHandler
)

TOKEN = os.environ.get("BOT_TOKEN")
DB_PATH = os.environ.get("DB_PATH", "bot_data.db")

# ---------------------------------------------------------------------------
# دیتابیس
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            name TEXT,
            joined_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            title TEXT,
            category TEXT DEFAULT 'شخصی',
            done INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS pomodoro_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            started_at TEXT,
            duration_minutes INTEGER,
            kind TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS skill_practice (
            chat_id INTEGER,
            skill TEXT,
            last_practiced TEXT,
            PRIMARY KEY (chat_id, skill)
        )
    """)
    conn.commit()
    conn.close()


def ensure_user(chat_id, name=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (chat_id, name, joined_at) VALUES (?, ?, ?)",
               (chat_id, name, datetime.now().isoformat()))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# برنامه ثابت تیزهوشان (طبق چیزی که چیدیم)
# ---------------------------------------------------------------------------
FIXED_CLASSES = [
    # (روز هفته پایتون: شنبه=5, یکشنبه=6, دوشنبه=0 ... چون تقویم پایتون از دوشنبه=0 شروع میشه)
    # weekday(): دوشنبه=0, سه‌شنبه=1, چهارشنبه=2, پنجشنبه=3, جمعه=4, شنبه=5, یکشنبه=6
    {"weekday": 6, "name": "کلاس خلاقیت", "start": "19:30", "end": "21:30"},
    {"weekday": 1, "name": "کلاس هوش جامع", "start": "17:00", "end": "19:15"},
    {"weekday": 2, "name": "کلاس رفع اشکال هوش جامع", "start": "17:00", "end": "19:15"},
]

SKILL_AREAS = [
    "هوش منطقی", "عددی", "محاسباتی", "کلامی", "تصویری", "فضایی",
    "الگوها", "استدلال", "خلاقیت", "سرعت", "دقت", "تمرکز",
    "درک مطلب", "واژگان", "مدیریت زمان", "تست‌زنی"
]

WEEKDAY_FA = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]


def today_schedule_text():
    wd = datetime.now().weekday()
    todays = [c for c in FIXED_CLASSES if c["weekday"] == wd]
    lines = [f"📅 برنامه امروز ({WEEKDAY_FA[wd]}):\n"]
    if todays:
        for c in todays:
            lines.append(f"⏰ {c['start']} تا {c['end']} — {c['name']}")
    else:
        lines.append("امروز کلاس ثابتی نداری. وقت خوبیه برای جبران یا تمرین تیزهوشان.")
    lines.append("\n💡 یادت نره: ویدیو همیشه قبل از تکلیفه، و آزمون هوش جامع باید ۲۴ ساعت قبل از سه‌شنبه (قبل ساعت ۱۷:۰۰ سه‌شنبه) تموم شده باشه.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# دستورات پایه
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    name = update.effective_user.first_name or ""
    ensure_user(chat_id, name)
    text = (
        f"سلام {name}! 👋\n\n"
        "من ربات تیزهوشان + پومودورو + تسک هستم.\n\n"
        "📋 دستورات:\n"
        "/today — برنامه امروز\n"
        "/pomodoro — شروع تایمر پومودورو\n"
        "/addtask <عنوان> — اضافه کردن تسک\n"
        "/tasks — لیست تسک‌ها\n"
        "/stats — آمار هفتگی\n"
        "/skills — مهارت‌های تیزهوشان کمتر تمرین‌شده\n"
        "/badday — حالت روز بد (فقط ضروری‌ترین‌ها)\n"
        "/help — راهنما"
    )
    await update.message.reply_text(text)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def today_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(today_schedule_text())


async def badday_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wd = datetime.now().weekday()
    todays = [c for c in FIXED_CLASSES if c["weekday"] == wd]
    lines = ["🌧 حالت روز بد فعال شد.\n", "فقط این‌ها امروز مهمه:"]
    if todays:
        for c in todays:
            lines.append(f"✅ {c['name']} ({c['start']}-{c['end']})")
    lines.append("✅ اگه آزمون هوش جامع تا ۲۴ ساعت دیگه ددلاین داره، فقط همون رو انجام بده")
    lines.append("✅ خواب کافی — هدف امروز فقط حفظ استمراره، نه ۱۰۰٪ برنامه")
    await update.message.reply_text("\n".join(lines))


async def skills_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT skill, last_practiced FROM skill_practice WHERE chat_id=?", (chat_id,))
    practiced = {row["skill"]: row["last_practiced"] for row in c.fetchall()}
    conn.close()

    never = [s for s in SKILL_AREAS if s not in practiced]
    lines = ["🧠 وضعیت مهارت‌های تیزهوشان:\n"]
    if never:
        lines.append("هنوز تمرین نشده:")
        lines.extend(f"⚪ {s}" for s in never)
    if practiced:
        lines.append("\nتمرین‌شده:")
        for s, d in practiced.items():
            lines.append(f"🟢 {s} (آخرین بار: {d[:10]})")
    lines.append("\nبرای ثبت تمرین یک مهارت: /practice <نام مهارت>")
    await update.message.reply_text("\n".join(lines))


async def practice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("استفاده: /practice هوش منطقی")
        return
    skill = " ".join(context.args)
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO skill_practice (chat_id, skill, last_practiced)
                 VALUES (?, ?, ?)
                 ON CONFLICT(chat_id, skill) DO UPDATE SET last_practiced=excluded.last_practiced""",
              (chat_id, skill, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ ثبت شد: {skill}")


# ---------------------------------------------------------------------------
# تسک‌ها
# ---------------------------------------------------------------------------

async def addtask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("استفاده: /addtask تکلیف هوش جامع")
        return
    title = " ".join(context.args)
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO tasks (chat_id, title, created_at) VALUES (?, ?, ?)",
               (chat_id, title, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ تسک اضافه شد: {title}")


async def tasks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, title, done FROM tasks WHERE chat_id=? ORDER BY done, id DESC", (chat_id,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("هیچ تسکی نداری. با /addtask یکی اضافه کن.")
        return
    keyboard = []
    for row in rows:
        mark = "✅" if row["done"] else "⬜"
        keyboard.append([InlineKeyboardButton(f"{mark} {row['title']}", callback_data=f"tgl:{row['id']}"),
                          InlineKeyboardButton("🗑", callback_data=f"del:{row['id']}")])
    await update.message.reply_text("📋 تسک‌های تو:", reply_markup=InlineKeyboardMarkup(keyboard))


async def task_button_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, task_id = query.data.split(":")
    conn = get_db()
    c = conn.cursor()
    if action == "tgl":
        c.execute("UPDATE tasks SET done = 1 - done WHERE id=?", (task_id,))
    elif action == "del":
        c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    chat_id = query.message.chat_id
    c.execute("SELECT id, title, done FROM tasks WHERE chat_id=? ORDER BY done, id DESC", (chat_id,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        await query.edit_message_text("هیچ تسکی نمونده. 🎉")
        return
    keyboard = []
    for row in rows:
        mark = "✅" if row["done"] else "⬜"
        keyboard.append([InlineKeyboardButton(f"{mark} {row['title']}", callback_data=f"tgl:{row['id']}"),
                          InlineKeyboardButton("🗑", callback_data=f"del:{row['id']}")])
    await query.edit_message_text("📋 تسک‌های تو:", reply_markup=InlineKeyboardMarkup(keyboard))


# ---------------------------------------------------------------------------
# پومودورو
# ---------------------------------------------------------------------------

POMODORO_MIN = 25
BREAK_MIN = 5

async def pomodoro_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO pomodoro_sessions (chat_id, started_at, duration_minutes, kind) VALUES (?, ?, ?, ?)",
               (chat_id, datetime.now().isoformat(), POMODORO_MIN, "focus"))
    conn.commit()
    conn.close()

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⏹ لغو", callback_data="pomo_cancel")]])
    msg = await update.message.reply_text(
        f"🍅 تایمر {POMODORO_MIN} دقیقه‌ای شروع شد. تمرکز کن!", reply_markup=keyboard
    )
    context.job_queue.run_once(
        pomodoro_done, when=POMODORO_MIN * 60,
        chat_id=chat_id, data={"message_id": msg.message_id, "kind": "focus"}
    )


async def pomodoro_done(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    kind = job.data["kind"]
    if kind == "focus":
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("☕️ شروع استراحت", callback_data="pomo_break")]])
        await context.bot.send_message(chat_id, "✅ ۲۵ دقیقه تمرکز تموم شد! وقت استراحته.", reply_markup=keyboard)
    else:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🍅 شروع پومودورو بعدی", callback_data="pomo_start")]])
        await context.bot.send_message(chat_id, "⏰ استراحت تموم شد. آماده‌ای برای دور بعد؟", reply_markup=keyboard)


async def pomodoro_button_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    if data == "pomo_cancel":
        for job in context.job_queue.get_jobs_by_name(str(chat_id)):
            job.schedule_removal()
        await query.edit_message_text("❌ تایمر لغو شد.")

    elif data == "pomo_break":
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⏹ لغو", callback_data="pomo_cancel")]])
        await query.edit_message_text(f"☕️ استراحت {BREAK_MIN} دقیقه‌ای شروع شد.", reply_markup=keyboard)
        context.job_queue.run_once(
            pomodoro_done, when=BREAK_MIN * 60,
            chat_id=chat_id, data={"kind": "break"}
        )

    elif data == "pomo_start":
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO pomodoro_sessions (chat_id, started_at, duration_minutes, kind) VALUES (?, ?, ?, ?)",
                   (chat_id, datetime.now().isoformat(), POMODORO_MIN, "focus"))
        conn.commit()
        conn.close()
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⏹ لغو", callback_data="pomo_cancel")]])
        await query.edit_message_text(f"🍅 تایمر {POMODORO_MIN} دقیقه‌ای شروع شد. تمرکز کن!", reply_markup=keyboard)
        context.job_queue.run_once(
            pomodoro_done, when=POMODORO_MIN * 60,
            chat_id=chat_id, data={"kind": "focus"}
        )


# ---------------------------------------------------------------------------
# آمار
# ---------------------------------------------------------------------------

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM pomodoro_sessions WHERE chat_id=? AND kind='focus' AND started_at>=?",
               (chat_id, week_ago))
    pomo_count = c.fetchone()["cnt"]
    c.execute("SELECT COUNT(*) as cnt FROM tasks WHERE chat_id=? AND done=1 AND created_at>=?",
               (chat_id, week_ago))
    done_count = c.fetchone()["cnt"]
    c.execute("SELECT COUNT(*) as cnt FROM tasks WHERE chat_id=? AND done=0", (chat_id,))
    pending_count = c.fetchone()["cnt"]
    conn.close()

    text = (
        "📊 آمار این هفته:\n\n"
        f"🍅 پومودورو انجام‌شده: {pomo_count}\n"
        f"✅ تسک تکمیل‌شده: {done_count}\n"
        f"⬜ تسک باقی‌مانده: {pending_count}"
    )
    await update.message.reply_text(text)


# ---------------------------------------------------------------------------
# یادآوری خودکار روزانه (کلاس امروز + هشدار آزمون)
# ---------------------------------------------------------------------------

async def daily_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT chat_id FROM users")
    users = c.fetchall()
    conn.close()
    text = today_schedule_text()
    wd = datetime.now().weekday()
    # یادآوری اضافه برای دوشنبه (آزمون فردا سه‌شنبه ۱۷:۰۰)
    if wd == 0:
        text += "\n\n⚠️ یادت باشه: آزمون هوش جامع باید تا فردا (سه‌شنبه) قبل از ساعت ۱۷:۰۰ تموم شده باشه!"
    for u in users:
        try:
            await context.bot.send_message(u["chat_id"], text)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# راه‌اندازی اپلیکیشن (قابل استفاده هم برای polling، هم برای webhook)
# ---------------------------------------------------------------------------

def build_application():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده است.")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("today", today_cmd))
    app.add_handler(CommandHandler("badday", badday_cmd))
    app.add_handler(CommandHandler("skills", skills_cmd))
    app.add_handler(CommandHandler("practice", practice_cmd))
    app.add_handler(CommandHandler("addtask", addtask_cmd))
    app.add_handler(CommandHandler("tasks", tasks_cmd))
    app.add_handler(CommandHandler("pomodoro", pomodoro_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))

    app.add_handler(CallbackQueryHandler(task_button_cb, pattern="^(tgl|del):"))
    app.add_handler(CallbackQueryHandler(pomodoro_button_cb, pattern="^pomo_"))

    # یادآوری روزانه ساعت ۸ صبح (به وقت سرور UTC؛ در server.py توضیح داده می‌شود)
    app.job_queue.run_daily(daily_reminder_job, time=datetime.strptime("04:30", "%H:%M").time())

    return app


if __name__ == "__main__":
    init_db()
    application = build_application()
    print("ربات با polling در حال اجراست...")
    application.run_polling()
