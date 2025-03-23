# run_bot.py
from telegram_bot import bot
from database import init_db

if __name__ == "__main__":
    init_db()
    print("Бот запущен...")
    bot.polling(none_stop=True)
