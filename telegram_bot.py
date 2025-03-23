# telegram_bot.py
import os
import telebot
from ai_handler import parse_user_request, generate_ai_response, memory
from database import * #get_db_connection, init_db
from dotenv import load_dotenv
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
scheduler = BackgroundScheduler()
scheduler.start()

def add_task_from_ai(user_id, parsed_request):
    task_text = parsed_request.get("task", "")
    deadline = parsed_request.get("deadline", "")

    if not task_text or not deadline:
        bot.send_message(user_id, "⚠ Не хватает данных для создания задачи!")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, task, deadline, priority) VALUES (?, ?, ?, ?)",
                   (user_id, task_text, deadline, "средний"))
    conn.commit()
    cursor.close()
    bot.send_message(user_id, f"✅ Задача добавлена: {task_text} (до {deadline})")

def edit_task_from_ai(user_id, parsed_request):
    task_id = parsed_request.get("task_id")
    new_text = parsed_request.get("task")

    if not task_id or not new_text:
        bot.send_message(user_id, "⚠ Укажите ID задачи и новый текст!")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET task = ? WHERE id = ? AND user_id = ?", (new_text, task_id, user_id))
    conn.commit()
    cursor.close()
    bot.send_message(user_id, f"✏ Задача {task_id} обновлена: {new_text}")

def delete_task_from_ai(user_id, parsed_request):
    task_id = parsed_request.get("task_id")

    if not task_id:
        bot.send_message(user_id, "⚠ Укажите ID задачи для удаления!")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    conn.commit()
    cursor.close()
    bot.send_message(user_id, f"🗑 Задача {task_id} удалена!")

def list_tasks_from_ai(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, task, deadline, priority FROM tasks WHERE user_id = ? AND status != 'completed'", (user_id,))
    tasks = cursor.fetchall()
    cursor.close()

    if tasks:
        response = "📌 Ваши активные задачи:\n"
        for task in tasks:
            response += f"📝 {task[1]} | ⏳ {task[2]} | 🔥 {task[3]} (ID: {task[0]})\n"
        bot.send_message(user_id, response)
    else:
        bot.send_message(user_id, "🔹 У вас нет активных задач.")

@bot.message_handler(commands=["add_task"])
def add_task(message):
    log_activity(message.chat.id, "add_task")
    bot.send_message(message.chat.id, "Введите задачу в формате: Задача | Дата (YYYY-MM-DD HH:MM) | Приоритет (низкий/средний/высокий)")
    bot.register_next_step_handler(message, save_task)

@bot.message_handler(commands=["stats"])
def show_stats(message):
    user_id = message.chat.id
    task_count = get_user_statistics(user_id)
    bot.send_message(user_id, f"📊 Ваша статистика:\n- Количество задач: {task_count}")




def save_task(message):
    try:
        user_id = message.chat.id
        parts = message.text.split("|")
        task_text = parts[0].strip()
        deadline = parts[1].strip()
        priority = parts[2].strip()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (user_id, task, deadline, priority) VALUES (?, ?, ?, ?)", 
                       (user_id, task_text, deadline, priority))
        conn.commit()

        bot.send_message(user_id, "✅ Задача добавлена!")

        remind_time = (datetime.datetime.strptime(deadline, "%Y-%m-%d %H:%M") - datetime.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M")
        cursor.execute("INSERT INTO reminders (user_id, task_id, remind_time) VALUES (?, (SELECT id FROM tasks WHERE task = ?), ?)",
                       (user_id, task_text, remind_time))
        conn.commit()

    except Exception as e:
        bot.send_message(message.chat.id, "⚠ Ошибка! Проверьте формат.")

@bot.message_handler(commands=["list_tasks"])
def list_tasks(message):
    user_id = message.chat.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, task, deadline, priority FROM tasks WHERE user_id = ? AND status != 'completed'", (user_id,))
    tasks = cursor.fetchall()
    if tasks:
        response = "📌 Ваши активные задачи:\n"
        for task in tasks:
            response += f"📝 {task[1]} | ⏳ {task[2]} | 🔥 {task[3]}\n"
        bot.send_message(user_id, response)
    else:
        bot.send_message(user_id, "🔹 У вас нет активных задач.")

def send_reminders():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, task_id FROM reminders WHERE remind_time = ?", (now,))
    reminders = cursor.fetchall()

    for reminder in reminders:
        cursor.execute("SELECT task FROM tasks WHERE id = ?", (reminder[1],))
        task_text = cursor.fetchone()[0]
        bot.send_message(reminder[0], f"🔔 Напоминание! Через 30 минут: {task_text}")

    cursor.execute("DELETE FROM reminders WHERE remind_time = ?", (now,))
    conn.commit()

scheduler.add_job(send_reminders, IntervalTrigger(minutes=1))

@bot.message_handler(commands=["assistant"])
def assistant_handler(message):
    bot.send_message(message.chat.id, "🧠 Введите ваш вопрос:")
    bot.register_next_step_handler(message, process_ai_request)

def process_ai_request(message):
    user_id = message.chat.id
    user_input = message.text

    parsed_request = parse_user_request(user_input)
    action = parsed_request.get("action", "none")

    if action == "add":
        add_task_from_ai(user_id, parsed_request)
    elif action == "edit":
        edit_task_from_ai(user_id, parsed_request)
    elif action == "delete":
        delete_task_from_ai(user_id, parsed_request)
    elif action == "list":
        list_tasks_from_ai(user_id)
    else:
        chat_history = memory.load_memory_variables({}).get("chat_history", "")
        response = generate_ai_response(user_input, chat_history)
        memory.save_context({"question": user_input}, {"response": response})
        bot.send_message(user_id, response)

@bot.message_handler(commands=["complete_task"])
def complete_task(message):
    bot.send_message(message.chat.id, "Введите ID завершённой задачи:")
    bot.register_next_step_handler(message, mark_task_completed)

def mark_task_completed(message):
    try:
        task_id = int(message.text)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))
        conn.commit()
        bot.send_message(message.chat.id, "✅ Задача завершена!")
    except:
        bot.send_message(message.chat.id, "⚠ Ошибка! Введите правильный ID.")

@bot.message_handler(commands=["start"])
def start_message(message):
    bot.send_message(message.chat.id, "👋 Привет! Я ассистент для управления задачами.\n\n"
                                      "📌 Доступные команды:\n"
                                      "/add_task - Добавить задачу\n"
                                      "/list_tasks - Показать активные задачи\n"
                                      "/complete_task - Завершить задачу\n"
                                      "/assistant - Задать вопрос AI\n")

@bot.message_handler(func=lambda message: message.text and not message.text.startswith("/"))
def handle_general_messages(message):
    process_ai_request(message)