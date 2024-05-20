import os
from openai import OpenAI

# Инициализация клиента OpenAI с использованием API-ключа из переменных окружения
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# Функция для запроса к ChatGPT с использованием модели GPT-3.5-turbo
def request_chat_gpt(user_message):
    try:
        # Создание запроса на генерацию завершения чата
        chat_completion = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Указание модели GPT-3.5-turbo
            messages=[
                {"role": "user", "content": user_message}  # Сообщение пользователя
            ]
        )
        # Корректный доступ к первому варианту ответа и его содержимому
        return chat_completion.choices[0].message['content']
    except Exception as e:
        print(f"An error occurred: {e}")
        return ""  # Возвращаем пустую строку или обрабатываем ошибку соответствующим образом
