import sqlite3
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

# Настройка логирования для отладки
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения из .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")


# Инициализация базы данных
def init_db():
    """Инициализирует базу данных SQLite для хранения настроек пользователей."""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        notify_period TEXT
    )''')
    conn.commit()
    conn.close()


# Получение текущих курсов валют
def get_current_rates():
    """Получает текущие курсы EUR и USD к RUB с API Центрального банка РФ."""
    try:
        url = "http://www.cbr-xml-daily.ru/daily_json.js"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        eur = data['Valute']['EUR']['Value']
        usd = data['Valute']['USD']['Value']
        return eur, usd
    except requests.RequestException as e:
        logger.error(f"Ошибка при получении курсов валют: {e}")
        return None, None


# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start, регистрирует пользователя и отправляет приветствие."""
    user_id = update.effective_user.id
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, notify_period) VALUES (?, ?)", (user_id, None))
        conn.commit()
    finally:
        conn.close()

    await update.message.reply_text(
        "Привет! Я бот для отслеживания курсов валют.\n"
        "Команды:\n"
        "/rates — текущие курсы EUR и USD\n"
        "/notify — настроить уведомления"
    )


# Обработчик команды /rates
async def rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /rates, отправляет текущие курсы EUR и USD."""
    eur, usd = get_current_rates()
    if eur is None or usd is None:
        await update.message.reply_text("Не удалось получить курсы валют. Попробуйте позже.")
        return
    await update.message.reply_text(f"Текущие курсы:\nEUR: {eur:.2f} RUB\nUSD: {usd:.2f} RUB")


# Обработчик команды /notify
async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /notify, предлагает выбрать периодичность уведомлений."""
    keyboard = [
        [InlineKeyboardButton("Раз в день", callback_data="notify_daily"),
         InlineKeyboardButton("Раз в неделю", callback_data="notify_weekly"),
         InlineKeyboardButton("Раз в месяц", callback_data="notify_monthly")],
        [InlineKeyboardButton("Отключить", callback_data="notify_off")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите периодичность уведомлений:", reply_markup=reply_markup)


# Обработчик выбора периодичности уведомлений
async def notify_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор периодичности уведомлений и сохраняет настройки."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    period = query.data.split("_")[1] if "_" in query.data else None

    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE users SET notify_period = ? WHERE user_id = ?", (period, user_id))
        conn.commit()
    finally:
        conn.close()

    period_map = {
        "daily": "раз в день",
        "weekly": "раз в неделю",
        "monthly": "раз в месяц",
        "off": "отключены"
    }
    await query.message.reply_text(f"Уведомления установлены: {period_map.get(period, 'отключены')}")


# Функция отправки уведомлений
async def send_notifications(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет уведомления пользователям согласно их настройкам."""
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT user_id, notify_period FROM users WHERE notify_period IS NOT NULL")
        users = c.fetchall()
    finally:
        conn.close()

    now = datetime.now()
    for user_id, period in users:
        should_send = False
        if period == "daily":
            should_send = True
        elif period == "weekly" and now.weekday() == 0:  # Понедельник
            should_send = True
        elif period == "monthly" and now.day == 1:  # Первый день месяца
            should_send = True

        if should_send:
            eur, usd = get_current_rates()
            if eur is None or usd is None:
                logger.warning(f"Не удалось отправить уведомление для user_id {user_id}: курсы недоступны")
                continue
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Курсы валют:\nEUR: {eur:.2f} RUB\nUSD: {usd:.2f} RUB"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления для user_id {user_id}: {e}")


# Основная функция
def main():
    """Инициализирует и запускает бота."""
    init_db()
    if not TOKEN:
        raise ValueError("BOT_TOKEN not found in .env file")

    app = Application.builder().token(TOKEN).build()

    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rates", rates))
    app.add_handler(CommandHandler("notify", notify))
    app.add_handler(CallbackQueryHandler(notify_button, pattern="^notify_"))

    # Планировщик для уведомлений через job_queue
    app.job_queue.run_repeating(send_notifications, interval=3600, first=10)  # Каждые 60 минут, начиная через 10 секунд

    # Запуск бота
    try:
        app.run_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise
    finally:
        app.stop()


if __name__ == "__main__":
    main()