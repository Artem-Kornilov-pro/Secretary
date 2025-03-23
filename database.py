import sqlite3
import os
from dotenv import load_dotenv
import logging
import datetime
load_dotenv()

DATABASE_NAME = os.getenv("DATABASE_NAME")

def get_db_connection():
    """Устанавливает соединение с базой данных с обработкой ошибок."""
    try:
        conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        logging.info("Соединение с базой данных установлено.")
        return conn
    except sqlite3.Error as e:
        logging.error(f"Ошибка подключения к базе данных: {e}")
        return None

def init_db():
    """Инициализирует базу данных с обработкой ошибок."""
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task TEXT,
            deadline TEXT,
            priority TEXT,
            status TEXT DEFAULT 'pending'
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_id INTEGER,
            remind_time TEXT
        )''')
        conn.commit()
        logging.info("База данных успешно инициализирована.")
    except sqlite3.Error as e:
        logging.error(f"Ошибка при инициализации базы данных: {e}")
    finally:
        conn.close()

def execute_query(query, params=(), fetch=False):
    """Выполняет SQL-запрос с обработкой ошибок."""
    conn = get_db_connection()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = None
        logging.info(f"Запрос выполнен: {query}")
        return result
    except sqlite3.Error as e:
        logging.error(f"Ошибка при выполнении запроса: {e}")
        return None
    finally:
        conn.close()


def log_activity(user_id, action):
    """Логирует активность пользователя."""
    query = "INSERT INTO activity_log (user_id, action, timestamp) VALUES (?, ?, ?)"
    params = (user_id, action, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    execute_query(query, params)

def get_user_statistics(user_id):
    """Возвращает статистику по пользователю."""
    query = "SELECT COUNT(*) FROM tasks WHERE user_id = ?"
    params = (user_id,)
    result = execute_query(query, params, fetch=True)
    if result:
        return result[0][0]  # Количество задач пользователя
    return 0