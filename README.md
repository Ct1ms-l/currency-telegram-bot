# Telegram Currency Bot

Telegram бот для отслеживания курсов валют (EUR и USD к RUB). Бот предоставляет текущие курсы, а также позволяет настроить периодические уведомления.

## Возможности
- `/start` — начать работу с ботом.
- `/rates` — получить текущие курсы EUR и USD.
- `/notify` — настроить уведомления (ежедневно, еженедельно, ежемесячно).

## Установка
1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/your-username/currency_bot.git
   cd currency_bot
2. Создайте виртуальное окружение и установите зависимости:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   pip install -r requirements.txt

3. Получите токен бота у @BotFather в Telegram.
4. Создайте файл .env в корне проекта и добавьте токен:
BOT_TOKEN=your_bot_token_here
5. Запустите telegram_bot.py