import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
from oauth2client.service_account import ServiceAccountCredentials

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Состояния разговора
ASK_NAME, ASK_AGE, ASK_GOAL = range(3)

# Вставь сюда свой Telegram User ID
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID'))  # ← сюда вставь свой ID

# Функция записи в Google Sheets
def write_to_google_sheet(full_name, age, goal):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials_json = os.getenv('tgbot-458217-f3c934000e84.json')
    credentials_dict = json.loads(credentials_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

client = gspread.authorize(creds)
    
    sheet = client.open('Запись на тренировки').sheet1
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    data = [now, full_name, age, goal]
    sheet.append_row(data)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton('Забронировать')]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text('Привет! Нажмите "Забронировать", чтобы начать.', reply_markup=reply_markup)

# Нажал Забронировать
async def booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Пожалуйста, укажите ваше ФИО:')
    return ASK_NAME

# Получаем ФИО
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['full_name'] = update.message.text
    await update.message.reply_text('Спасибо! Теперь укажите ваш возраст:')
    return ASK_AGE

# Получаем возраст
async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['age'] = update.message.text
    
    # Выводим кнопки для целей
    goals_keyboard = [
        [KeyboardButton('Похудение'), KeyboardButton('Набор массы')],
        [KeyboardButton('Реабилитация'), KeyboardButton('Улучшение формы')]
    ]
    reply_markup = ReplyKeyboardMarkup(goals_keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text('Выберите цель ваших тренировок:', reply_markup=reply_markup)
    return ASK_GOAL

# Получаем цель
async def ask_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['goal'] = update.message.text

    # Сохраняем в Google Sheets
    write_to_google_sheet(
        context.user_data['full_name'],
        context.user_data['age'],
        context.user_data['goal']
    )

    # Отправляем клиенту подтверждение
    summary = (
        f"✅ Бронирование принято!\n\n"
        f"ФИО: {context.user_data['full_name']}\n"
        f"Возраст: {context.user_data['age']}\n"
        f"Цель: {context.user_data['goal']}\n\n"
        f"Скоро мы свяжемся с вами!"
    )
    await update.message.reply_text(summary)

    # Отправляем уведомление администратору
    admin_message = (
        f"📬 Новое бронирование!\n\n"
        f"ФИО: {context.user_data['full_name']}\n"
        f"Возраст: {context.user_data['age']}\n"
        f"Цель: {context.user_data['goal']}"
    )
    await context.bot.send_message(chat_id=433684845, text=admin_message)

    return ConversationHandler.END

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Бронирование отменено.')
    return ConversationHandler.END

# Основная функция запуска
def main():
    token = os.getenv('BOT_TOKEN')
    app = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^(Забронировать)$'), booking)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            ASK_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_goal)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(conv_handler)

    app.run_polling()

if __name__ == '__main__':
    main()
