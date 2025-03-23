import telebot
import sqlite3
import datetime
import google.generativeai as genai
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from langchain_google_genai import GoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory



memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# 🔹 Настройки API
TELEGRAM_BOT_TOKEN = "7799726378:AAHy0ADffhV-XWay0v8xN0Hsag2dJDKSnYA"
GOOGLE_API_KEY = "AIzaSyAKsoeU1KVPNhE9jBWoDJRi0Y7SgF9By_0"

# 🔹 Инициализация Telebot и Langchain
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
genai.configure(api_key=GOOGLE_API_KEY)
llm = GoogleGenerativeAI(model="gemini-1.5-pro-latest", google_api_key=GOOGLE_API_KEY)

# 🔹 Подключение к БД и создание таблиц
conn = sqlite3.connect("tasks.db", check_same_thread=False)
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



def add_task_from_ai(user_id, parsed_request):
    """Добавляет новую задачу в базу данных."""
    task_text = parsed_request.get("task", "")
    deadline = parsed_request.get("deadline", "")

    if not task_text or not deadline:
        bot.send_message(user_id, "⚠ Не хватает данных для создания задачи!")
        return

    conn = sqlite3.connect("tasks.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, task, deadline, priority) VALUES (?, ?, ?, ?)",
                   (user_id, task_text, deadline, "средний"))
    conn.commit()
    cursor.close()
    
    bot.send_message(user_id, f"✅ Задача добавлена: {task_text} (до {deadline})")


def edit_task_from_ai(user_id, parsed_request):
    """Редактирует существующую задачу."""
    task_id = parsed_request.get("task_id")
    new_text = parsed_request.get("task")

    if not task_id or not new_text:
        bot.send_message(user_id, "⚠ Укажите ID задачи и новый текст!")
        return

    conn = sqlite3.connect("tasks.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET task = ? WHERE id = ? AND user_id = ?", (new_text, task_id, user_id))
    conn.commit()
    cursor.close()

    bot.send_message(user_id, f"✏ Задача {task_id} обновлена: {new_text}")


def delete_task_from_ai(user_id, parsed_request):
    """Удаляет задачу по ID."""
    task_id = parsed_request.get("task_id")

    if not task_id:
        bot.send_message(user_id, "⚠ Укажите ID задачи для удаления!")
        return

    conn = sqlite3.connect("tasks.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    conn.commit()
    cursor.close()

    bot.send_message(user_id, f"🗑 Задача {task_id} удалена!")



def list_tasks_from_ai(user_id):
    """Выводит список задач."""
    conn = sqlite3.connect("tasks.db", check_same_thread=False)
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


from langchain.output_parsers import StructuredOutputParser, ResponseSchema

# Описываем возможные намерения пользователя
response_schemas = [
    ResponseSchema(name="action", description="Тип запроса: add, edit, delete, list, или none"),
    ResponseSchema(name="task", description="Текст новой задачи или изменения"),
    ResponseSchema(name="deadline", description="Дата и время дедлайна (если есть)"),
    ResponseSchema(name="task_id", description="ID задачи, если редактируется или удаляется (если есть)"),
]

parser = StructuredOutputParser.from_response_schemas(response_schemas)

def parse_user_request(user_input):
    """Определяет, что хочет сделать пользователь (создать, изменить или удалить задачу)."""
    prompt = PromptTemplate.from_template(
        "Ты помощник по управлению задачами. Проанализируй сообщение и укажи его параметры.\n"
        "Сообщение: {user_input}\n"
        "Ответ должен быть в JSON: {format_instructions}"
    ).partial(format_instructions=parser.get_format_instructions())

    structured_chain = prompt | llm | parser
    result = structured_chain.invoke({"user_input": user_input})
    
    return result  # Вернёт словарь с action, task, deadline, task_id


# 📌 Функция добавления задачи
@bot.message_handler(commands=["add_task"])
def add_task(message):
    bot.send_message(message.chat.id, "Введите задачу в формате: Задача | Дата (YYYY-MM-DD HH:MM) | Приоритет (низкий/средний/высокий)")
    bot.register_next_step_handler(message, save_task)


def save_task(message):
    try:
        user_id = message.chat.id
        parts = message.text.split("|")
        task_text = parts[0].strip()
        deadline = parts[1].strip()
        priority = parts[2].strip()

        cursor.execute("INSERT INTO tasks (user_id, task, deadline, priority) VALUES (?, ?, ?, ?)", 
                       (user_id, task_text, deadline, priority))
        conn.commit()

        bot.send_message(user_id, "✅ Задача добавлена!")

        # Добавление напоминания за 30 минут
        remind_time = (datetime.datetime.strptime(deadline, "%Y-%m-%d %H:%M") - datetime.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M")
        cursor.execute("INSERT INTO reminders (user_id, task_id, remind_time) VALUES (?, (SELECT id FROM tasks WHERE task = ?), ?)",
                       (user_id, task_text, remind_time))
        conn.commit()

    except Exception as e:
        bot.send_message(message.chat.id, "⚠ Ошибка! Проверьте формат.")


# 📌 Функция просмотра задач (исключает завершённые)
@bot.message_handler(commands=["list_tasks"])
def list_tasks(message):
    user_id = message.chat.id
    cursor.execute("SELECT id, task, deadline, priority FROM tasks WHERE user_id = ? AND status != 'completed'", (user_id,))
    tasks = cursor.fetchall()

    if tasks:
        response = "📌 Ваши активные задачи:\n"
        for task in tasks:
            response += f"📝 {task[1]} | ⏳ {task[2]} | 🔥 {task[3]}\n"
        bot.send_message(user_id, response)
    else:
        bot.send_message(user_id, "🔹 У вас нет активных задач.")


# 📌 Функция напоминаний
def send_reminders():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute("SELECT user_id, task_id FROM reminders WHERE remind_time = ?", (now,))
    reminders = cursor.fetchall()

    for reminder in reminders:
        cursor.execute("SELECT task FROM tasks WHERE id = ?", (reminder[1],))
        task_text = cursor.fetchone()[0]
        bot.send_message(reminder[0], f"🔔 Напоминание! Через 30 минут: {task_text}")

    # Удаляем отправленные напоминания
    cursor.execute("DELETE FROM reminders WHERE remind_time = ?", (now,))
    conn.commit()


#scheduler.add_job(send_reminders, IntervalTrigger(minutes=1))   !!!



# 📌 Функция интеллектуального помощника (Теперь он видит задачи пользователя!)
# 📌 Функция интеллектуального помощника (Теперь он учитывает предыдущие вопросы!)
@bot.message_handler(commands=["assistant"])
def assistant_handler(message):
    bot.send_message(message.chat.id, "🧠 Введите ваш вопрос:")
    bot.register_next_step_handler(message, process_ai_request)


def process_ai_request(message):
    user_id = message.chat.id
    user_input = message.text

    # Определяем, что хочет сделать пользователь (задачи или просто ответ)
    parsed_request = parse_user_request(user_input)
    action = parsed_request.get("action", "none")

    # Если пользователь хочет работать с задачами
    if action == "add":
        add_task_from_ai(user_id, parsed_request)
    elif action == "edit":
        edit_task_from_ai(user_id, parsed_request)
    elif action == "delete":
        delete_task_from_ai(user_id, parsed_request)
    elif action == "list":
        list_tasks_from_ai(user_id)
    else:
        # Если это просто вопрос, отвечаем как обычный AI
        chat_history = memory.load_memory_variables({}).get("chat_history", "")

        template = PromptTemplate.from_template(
            "Ты персональный ассистент. Пользователь задал вопрос: {question}.\n\n"
            "История чата:\n"
            "{chat_history}\n\n"
            "Ответь полезно и информативно."
        )

        chain = template | llm

        response = chain.invoke({
            "question": user_input,
            "chat_history": chat_history  # Передаём историю чата
        })

        # Сохраняем новый диалог в память
        memory.save_context({"question": user_input}, {"response": response})

        bot.send_message(user_id, response)



# 📌 Функция завершения задачи
@bot.message_handler(commands=["complete_task"])
def complete_task(message):
    bot.send_message(message.chat.id, "Введите ID завершённой задачи:")
    bot.register_next_step_handler(message, mark_task_completed)


def mark_task_completed(message):
    try:
        task_id = int(message.text)
        cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))
        conn.commit()
        bot.send_message(message.chat.id, "✅ Задача завершена!")
    except:
        bot.send_message(message.chat.id, "⚠ Ошибка! Введите правильный ID.")


# 📌 Стартовое сообщение
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
    """Обрабатывает все текстовые сообщения, кроме команд, через ИИ"""
    process_ai_request(message)




if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.start()
    scheduler.add_job(send_reminders, IntervalTrigger(minutes=1))
    print("Бот запущен...")
    bot.polling(none_stop=True)
