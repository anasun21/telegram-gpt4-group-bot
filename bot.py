import os
import logging
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# Логи
logging.basicConfig(level=logging.INFO)

# Ключі
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Підключення до SQLite
conn = sqlite3.connect('session.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS sessions
             (chat_id INTEGER PRIMARY KEY, prompt TEXT, history TEXT)''')
conn.commit()

# ============================
# Команди
# ============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Вітаю! Я — GPT-4 фасилітатор. Використовуй /setprompt, щоб задати роль.\n/help — допомога.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/setprompt [текст] — задати роль бота\n"
        "/reset — очистити історію\n"
        "Просто пиши повідомлення!"
    )

async def setprompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = ' '.join(context.args)
    if not prompt:
        await update.message.reply_text("Будь ласка, введіть промт після команди.")
        return
    chat_id = update.effective_chat.id
    c.execute("INSERT OR REPLACE INTO sessions (chat_id, prompt, history) VALUES (?, ?, ?)", (chat_id, prompt, ""))
    conn.commit()
    await update.message.reply_text(f"✅ Новий промт встановлено!")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    c.execute("UPDATE sessions SET history = '' WHERE chat_id = ?", (chat_id,))
    conn.commit()
    await update.message.reply_text("🗑 Історію очищено.")

# ============================
# Обробник повідомлень
# ============================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_message = update.message.text

    # Отримати сесію
    c.execute("SELECT prompt, history FROM sessions WHERE chat_id = ?", (chat_id,))
    row = c.fetchone()

    if row:
        prompt, history = row
    else:
        prompt = "Ти — дружній GPT-4 асистент."
        history = ""
        c.execute("INSERT INTO sessions (chat_id, prompt, history) VALUES (?, ?, ?)", (chat_id, prompt, ""))
        conn.commit()

    # Формуємо повний контекст
    messages = []
    if prompt:
        messages.append({"role": "system", "content": prompt})

    if history:
        for line in history.split("|||"):
            if "::" in line:
    role, content = line.split("::", 1)
else:
    # Якщо нема ::, вважай це повідомлення від користувача
    role, content = "user", line
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})

    # Виклик OpenAI
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )

    reply = response.choices[0].message.content

    # Оновлюємо історію
    new_history = history + f"user::{user_message}|||assistant::{reply}|||"
    c.execute("UPDATE sessions SET history = ? WHERE chat_id = ?", (new_history, chat_id))
    conn.commit()

    await update.message.reply_text(reply)

# ============================
# Основна частина
# ============================

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("setprompt", setprompt))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == '__main__':
    main()
