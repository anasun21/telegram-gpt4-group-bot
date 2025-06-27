import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from openai import OpenAI

# ЛОГИ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# КЛЮЧІ
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Клієнт OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Пам'ять для промпту
PROMPT_MEMORY = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_message = update.message.text

    # Якщо ще немає промпту — чекаємо першого
    if chat_id not in PROMPT_MEMORY:
        PROMPT_MEMORY[chat_id] = user_message
        await update.message.reply_text(
            f"✅ Промпт збережено! Тепер пишіть ваші питання."
        )
        return

    # Якщо промпт вже є — відправляємо у GPT-4
    conversation = f"{PROMPT_MEMORY[chat_id]}\n\nПитання: {user_message}\nВідповідь:"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": PROMPT_MEMORY[chat_id]},
            {"role": "user", "content": user_message}
        ]
    )

    answer = response.choices[0].message.content

    await update.message.reply_text(answer)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    app.add_handler(message_handler)
