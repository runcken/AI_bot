import logging
import os
import random
import requests
import sys

import vk_api as vk
from vk_api.longpoll import VkLongPoll, VkEventType
from environs import Env
from google.cloud import dialogflow


class TelegramLogsHandler(logging.Handler):
    def __init__(self, tg_token, chat_id):
        super().__init__()
        self.tg_token = tg_token
        self.chat_id = chat_id
        self.setLevel(logging.ERROR)
        self._is_sending = False
        self.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )

    def emit(self, record):
        if self._is_sending or not self.chat_id:
            return

        try:
            self._is_sending = True

            log_entry = self.format(record)

            if len(log_entry) > 4096:
                log_entry = log_entry[:4090] + "\n[обрыв]"

            text = f"Ошибка VK Бота:\n{log_entry}"

            url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

        except Exception as e:
            print(f"CRITICAL: Не удалось отправить лог в Telegram: {e}")
        finally:
            self._is_sending = False


def detect_intent_texts(project_id, session_id, text, language_code):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    text_input = dialogflow.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(
        request={"session": session, "query_input": query_input}
    )
    return (
        response.query_result.fulfillment_text,
        response.query_result.intent.is_fallback)


def handle_message(event, vk_api, project_id, language_code):
    user_text = event.text
    session_id = str(event.user_id)

    logging.debug(f"Сообщение от VK пользователя {session_id}: {user_text}")

    fulfillment_text, is_fallback = detect_intent_texts(
        project_id,
        session_id,
        user_text,
        language_code
    )

    if is_fallback:
        logging.warning(f"DialogFlow вернул fallback для: '{user_text}'")
        return

    elif fulfillment_text:
        vk_api.messages.send(
            user_id=event.user_id,
            message=fulfillment_text,
            random_id=random.randint(1, 1000000)
        )
        logging.info(f"Ответ отправлен пользователю {session_id}")


def main():
    env = Env()
    env.read_env()

    vk_token = env.str('VK_TOKEN')
    project_id = env.str('PROJECT_ID')
    language_code = env.str('LANGUAGE_CODE')

    tg_token = env.str('TG_TOKEN')
    admin_chat_id = env.str('ADMIN_CHAT_ID')

    key_path = env.str('GOOGLE_APPLICATION_CREDENTIALS')
    if key_path:
        expanded_path = os.path.expanduser(key_path)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = expanded_path
        print(f"Установлен путь к ключу: {expanded_path}")
    else:
        print("GOOGLE_APPLICATION_CREDENTIALS не задан")

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    root_logger = logging.getLogger()

    if tg_token and admin_chat_id:
        tg_handler = TelegramLogsHandler(tg_token, admin_chat_id)
        root_logger.addHandler(tg_handler)
        print("Логирование ошибок в Telegram настроено.")

        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            requests.post(url, json={
                "chat_id": admin_chat_id,
                "text": "VK Бот запущен!\nМониторинг ошибок активен.",
                "parse_mode": "HTML"
            }, timeout=5)
        except Exception as e:
            print(f"Не удалось отправить приветственное сообщение в TG: {e}")
    else:
        print("TG_LOGS_TOKEN или ADMIN_CHAT_ID не заданы.")

    try:
        vk_session = vk.VkApi(token=vk_token)
        vk_api = vk_session.get_api()
        longpoll = VkLongPoll(vk_session)
        print("VK LongPoll подключен. Ожидание сообщений...")
    except Exception as e:
        logging.critical(f"Не удалось инициализировать VK API: {e}")
        if tg_token and admin_chat_id:
            try:
                requests.post(
                    f"https://api.telegram.org/bot{tg_token}/sendMessage",
                    json={
                        "chat_id": admin_chat_id,
                        "text": f"КРИТИЧЕСКИЙ СБОЙ ЗАПУСКА VK БОТА\n{e}",
                        "parse_mode": "HTML"
                    }
                )
            except Exception:
                pass
        return

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            try:
                handle_message(event, vk_api, project_id, language_code)
            except Exception as e:
                logging.error(f"Критическая ошибка в handle_message: {e}")


if __name__ == "__main__":
    main()
