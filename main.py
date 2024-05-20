import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext
)
from chatgpt_client import request_chat_gpt

load_dotenv()

# Настройка логирования для отслеживания информации о работе бота
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Получение токена бота из переменной окружения
TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")

# Словари для хранения состояний и результатов пользователей
USER_STATE = {}
USER_LEVEL = {}
QUIZ_QUESTIONS = {}
QUIZ_SCORE = {}
QUIZ_ANSWERED = {}

# Определение состояний пользователя в боте
TRANSLATING, QUIZ, CONVERSATION, CHOOSING_LEVEL = range(4)

# Функции для управления состоянием пользователя
def set_user_state(user_id, state):
    USER_STATE[user_id] = state

def get_user_state(user_id):
    return USER_STATE.get(user_id, None)

def set_user_level(user_id, level):
    USER_LEVEL[user_id] = level

def get_user_level(user_id):
    return USER_LEVEL.get(user_id, "beginner")

def generate_quiz_questions():
    """Функция для генерации вопросов викторины."""
    questions = []
    base_words = ["apple", "house", "world", "discover", "beautiful"]
    for word in base_words:
        translation = request_chat_gpt(f"Translate the word '{word}' to Russian.")
        questions.append({"en": word, "ru": translation.strip()})
    return questions

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Перевод"],
        ["Викторина по словарному запасу"],
        ["Практика разговора"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    # Приветственное сообщение с описанием команд
    await update.message.reply_text(
        "Привет! Я бот, который поможет тебе учить английский язык.\n"
        "Выбери один из режимов или используй команды для управления мной:\n\n"
        "- /start - начать работу с ботом и показать это сообщение.\n"
        "- меню - показать главное меню для выбора режима работы.\n"
        "Режимы работы:\n"
        "1. Перевод: я переведу твои слова или фразы.\n"
        "2. Викторина по словарному запасу: проверь свои знания английских слов.\n"
        "3. Практика разговора: попрактикуемся в разговорном английском.",
        reply_markup=reply_markup
    )

# Функция для возврата пользователя в главное меню
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Перевод"],
        ["Викторина по словарному запасу"],
        ["Практика разговора"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    # Сообщение с выбором режима работы
    await update.message.reply_text("Выбери режим работы:", reply_markup=reply_markup)

# Обработчик входящих сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    text = update.message.text.lower()

    # Обработка команды выхода
    if text == '/menu' or text == 'меню':
        await menu(update, context)
        set_user_state(user_id, None)
        return

    # Диспетчеризация по состояниям пользователя
    if state == TRANSLATING:
        await translate_text(update, context)
    elif state == QUIZ:
        await check_quiz_answer(update, context)
    elif state == CONVERSATION:
        await continue_conversation(update, context)
    elif state == CHOOSING_LEVEL:
        await choose_quiz_level(update, context)
    else:
        await guide_user(update, context)

# Функция для направления пользователя в соответствующий раздел
async def guide_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text in ['/menu', 'меню']:
        await menu(update, context)
        set_user_state(update.effective_user.id, None)
        return

    if text == 'перевод':
        set_user_state(update.effective_user.id, TRANSLATING)
        await update.message.reply_text("Отправь мне слово или фразу для перевода на английский.")
    elif text == 'викторина по словарному запасу':
        set_user_state(update.effective_user.id, CHOOSING_LEVEL)
        await choose_level(update, context)
    elif text == 'практика разговора':
        set_user_state(update.effective_user.id, CONVERSATION)
        await start_conversation(update, context)
    else:
        await update.message.reply_text("Пожалуйста, выбери опцию из клавиатуры.")

# Функция для выбора уровня сложности викторины
async def choose_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text in ['/menu', 'меню']:
        await menu(update, context)
        set_user_state(update.effective_user.id, None)
        return

    keyboard = [
        ["Начальный"],
        ["Средний"],
        ["Продвинутый"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выбери уровень сложности для викторины:", reply_markup=reply_markup)

# Функция для установки уровня сложности и начала викторины
async def choose_quiz_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text in ['/menu', 'меню']:
        await menu(update, context)
        set_user_state(update.effective_user.id, None)
        return

    levels = {
        "начальный": "beginner",
        "средний": "intermediate",
        "продвинутый": "advanced"
    }
    if text in levels:
        set_user_level(update.effective_user.id, levels[text])
        set_user_state(update.effective_user.id, QUIZ)
        QUIZ_QUESTIONS[update.effective_user.id] = generate_quiz_questions()
        QUIZ_SCORE[update.effective_user.id] = 0
        QUIZ_ANSWERED[update.effective_user.id] = 0
        await send_quiz_question(update, context)
    else:
        await update.message.reply_text("Пожалуйста, выбери уровень сложности из предложенных опций.")

# Функция для отправки вопросов викторины
async def send_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    questions = QUIZ_QUESTIONS[user_id]
    answered = QUIZ_ANSWERED[user_id]

    if answered < 5:  # Ограничение на количество вопросов викторины
        question = questions[answered]
        context.user_data['quiz'] = question
        await update.message.reply_text(f"Как будет на английском: '{question['ru']}'?")
    else:
        # Вывод результатов викторины
        score = QUIZ_SCORE[user_id]
        await update.message.reply_text(f"Викторина окончена! Ты правильно ответил на {score} из 5 слов.")
        await menu(update, context)  # Возврат в меню

# Функция для проверки ответов на вопросы викторины
async def check_quiz_answer(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text.lower()

    if text in ['/menu', 'меню']:
        await menu(update, context)
        set_user_state(user_id, None)
        return

    correct_answer = context.user_data['quiz']['en'].lower()
    if text == correct_answer:
        QUIZ_SCORE[user_id] += 1
        await update.message.reply_text("Верно! 🎉")
    else:
        await update.message.reply_text(f"Неверно. Правильный ответ был: {correct_answer}.")

    QUIZ_ANSWERED[user_id] += 1
    # Переход к следующему вопросу
    await send_quiz_question(update, context)

# Функция для перевода текста
async def translate_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text in ['/menu', 'меню']:
        await menu(update, context)
        set_user_state(update.effective_user.id, None)
        return

    translation = request_chat_gpt(f"Translate '{update.message.text}' to English.")
    await update.message.reply_text(f"Перевод: {translation}")

# Функция для начала разговора на заданную тему
async def start_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text in ['/menu', 'меню']:
        await menu(update, context)
        set_user_state(update.effective_user.id, None)
        return

    response = request_chat_gpt(f"Let's practice conversation in English about the topic '{update.message.text}'.")
    await update.message.reply_text(response)

# Функция для продолжения разговора
async def continue_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text in ['/menu', 'меню']:
        await menu(update, context)
        set_user_state(update.effective_user.id, None)
        return

    response = request_chat_gpt(f"Continue the conversation: {update.message.text}")
    await update.message.reply_text(response)

# Главная функция для создания и запуска бота
def main():
    application = ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()

    # Добавление обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("exit", menu))  # Исправление обработчика команды /exit

    # Добавление обработчика текстовых сообщений
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(message_handler)

    # Запуск бота
    application.run_polling()

# Запуск основного процесса при выполнении скрипта
if __name__ == "__main__":
    main()
