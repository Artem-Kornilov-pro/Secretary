# ai_handler.py
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from dotenv import load_dotenv
import os
import logging

# Настройка логирования
logging.basicConfig(
    filename='ai_handler.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Инициализация Google Generative AI
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    llm = GoogleGenerativeAI(model="gemini-1.5-pro-latest", google_api_key=GOOGLE_API_KEY)
    logging.info("Google Generative AI успешно инициализирован.")
except Exception as e:
    logging.error(f"Ошибка при инициализации Google Generative AI: {e}")
    llm = None

# Инициализация памяти для истории чата
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Схема для парсинга ответов
response_schemas = [
    ResponseSchema(name="action", description="Тип запроса: add, edit, delete, list, или none"),
    ResponseSchema(name="task", description="Текст новой задачи или изменения"),
    ResponseSchema(name="deadline", description="Дата и время дедлайна (если есть)"),
    ResponseSchema(name="task_id", description="ID задачи, если редактируется или удаляется (если есть)"),
]

try:
    parser = StructuredOutputParser.from_response_schemas(response_schemas)
    logging.info("Парсер успешно инициализирован.")
except Exception as e:
    logging.error(f"Ошибка при создании парсера: {e}")
    parser = None

def parse_user_request(user_input):
    """Парсит запрос пользователя и возвращает структурированный ответ."""
    if not llm or not parser:
        logging.error("Google Generative AI или парсер не инициализирован.")
        return {"action": "none", "task": "", "deadline": "", "task_id": ""}

    try:
        prompt = PromptTemplate.from_template(
            "Ты помощник по управлению задачами. Проанализируй сообщение и укажи его параметры.\n"
            "Сообщение: {user_input}\n"
            "Ответ должен быть в JSON: {format_instructions}"
        ).partial(format_instructions=parser.get_format_instructions())

        structured_chain = prompt | llm | parser
        result = structured_chain.invoke({"user_input": user_input})
        logging.info(f"Запрос пользователя успешно обработан: {user_input}")
        return result
    except Exception as e:
        logging.error(f"Ошибка при парсинге запроса пользователя: {e}")
        return {"action": "none", "task": "", "deadline": "", "task_id": ""}

def generate_ai_response(user_input, chat_history):
    """Генерирует ответ на вопрос пользователя с использованием ИИ."""
    if not llm:
        logging.error("Google Generative AI не инициализирован.")
        return "Извините, сервис ИИ временно недоступен."

    try:
        template = PromptTemplate.from_template(
            "Ты персональный ассистент. Пользователь задал вопрос: {question}.\n\n"
            "История чата:\n"
            "{chat_history}\n\n"
            "Ответь полезно и информативно."
        )
        chain = template | llm
        response = chain.invoke({"question": user_input, "chat_history": chat_history})
        logging.info(f"Ответ ИИ успешно сгенерирован для запроса: {user_input}")
        return response
    except Exception as e:
        logging.error(f"Ошибка при генерации ответа ИИ: {e}")
        return "Извините, произошла ошибка при обработке вашего запроса."