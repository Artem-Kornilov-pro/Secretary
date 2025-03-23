# ToDo + AI Assistant (Telegram Bot)

Этот проект представляет собой Telegram-бота для управления задачами (ToDo) с интеллектуальным помощником на основе Google Generative AI (Gemini). Бот позволяет добавлять, редактировать, удалять и просматривать задачи, а также задавать вопросы ИИ-ассистенту.

## Основные функции

- **Управление задачами**:
  - Добавление задач с указанием дедлайна и приоритета.
  - Редактирование и удаление задач.
  - Просмотр списка активных задач.
  - Отметка задач как завершенных.

- **Интеллектуальный помощник**:
  - Ответы на вопросы пользователя с использованием Google Generative AI.
  - Понимание естественного языка для работы с задачами (например, "Добавь задачу купить молоко до завтра").

- **Напоминания**:
  - Автоматические напоминания за 30 минут до дедлайна задачи.

- **База данных**:
  - Использование SQLite для хранения задач и напоминаний.

## Технологии

- **Python**: Основной язык программирования.
- **Telebot**: Библиотека для работы с Telegram API.
- **Google Generative AI (Gemini)**: ИИ для обработки естественного языка.
- **SQLite**: База данных для хранения задач и напоминаний.
- **Docker**: Контейнеризация приложения.
- **GitHub Actions**: Автоматизация CI/CD.

---

## Установка и запуск

### 1. Установка зависимостей

Убедитесь, что у вас установлен Python 3.9 или выше. Затем установите зависимости:

```bash
pip install -r requirements.txt
