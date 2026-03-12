import logging
import os
import random
import sys
import threading
import time

import vk_api as vk
from vk_api.longpoll import VkLongPoll, VkEventType
from environs import Env
from google.cloud import dialogflow
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import telegram


class TelegramLogsHandler(logging.Handler):
    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.tg_bot = tg_bot
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

            text = f"Ошибка ({record.name}):\n{log_entry}"

            self.tg_bot.send_message(
                chat_id=self.chat_id,
                text=text,
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"CRITICAL: Failed to send log to Telegram: {e}")
        finally:
            self._is_sending = False


def setup_logging(bot_instance, chat_id):
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    root_logger = logging.getLogger()

    tg_handler = TelegramLogsHandler(bot_instance, chat_id)
    root_logger.addHandler(tg_handler)

    logging.info(
        "Логирование настроено. Ошибки будут дублироваться в Telegram."
    )


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
        response.query_result.intent.is_fallback
    )


def run_telegram_bot(tg_token, project_id, language_code, log_bot):
    if not tg_token:
        logging.warning("TG_TOKEN не задан, бот Telegram не запущен.")
        return

    def start(update, context):
        user = update.message.from_user
        update.message.reply_text(f'Здравствуйте, {user.first_name}!')
        logging.info(f"TG: Пользователь {user.id} запустил бота.")

    def handle_message(update, context):
        user_text = update.message.text
        session_id = str(update.effective_chat.id)

        logging.debug(f"TG: Получено сообщение от {session_id}: {user_text}")

        try:
            fulfillment_text, is_fallback = detect_intent_texts(
                project_id, session_id, user_text, language_code
            )

            if is_fallback:
                logging.warning(f"TG: Fallback ответ для '{user_text}'")
                update.message.reply_text("Извините, я не понял вопрос.")
            elif fulfillment_text:
                update.message.reply_text(fulfillment_text)
            else:
                update.message.reply_text("Извините, я не понял вопрос.")

        except Exception as e:
            logging.error(f"TG Dialogflow Error: {e}")
            update.message.reply_text("Произошла ошибка. Попробуйте позже.")

    def error_callback(update, context):
        logging.error(f"TG Global Error: {context.error}")

    updater = Updater(tg_token, use_context=True)
    dp = updater.dispatcher
    dp.bot_data['project_id'] = project_id
    dp.bot_data['language_code'] = language_code

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(
        MessageHandler(Filters.text & ~Filters.command, handle_message)
    )
    dp.add_error_handler(error_callback)

    logging.info("TG Bot: Запуск polling...")
    updater.start_polling()

    try:
        while True:
            if not updater.running:
                logging.warning("TG Bot: Polling остановлен")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("TG Bot: получен сигнал остановки внутри потока")
    finally:
        updater.stop()
        logging.info("TG Bot: Остановлен корректно")


def run_vk_bot(vk_token, project_id, language_code):
    if not vk_token:
        logging.warning("VK_TOKEN не задан, бот VK не запущен.")
        return

    try:
        vk_session = vk.VkApi(token=vk_token)
        vk_api = vk_session.get_api()
        longpoll = VkLongPoll(vk_session)
        logging.info("VK Bot: LongPoll подключен, ожидание сообщений...")

    except Exception as e:
        logging.critical(f"VK Bot: Не удалось инициализировать VK API: {e}")
        return

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_text = event.text
            session_id = str(event.user_id)

            logging.debug(f"VK: Сообщение от {session_id}: {user_text}")

            try:
                fulfillment_text, is_fallback = detect_intent_texts(
                    project_id, session_id, user_text, language_code
                )

                if is_fallback:
                    logging.warning(f"VK: Fallback ответ для '{user_text}'")

                elif fulfillment_text:
                    vk_api.messages.send(
                        user_id=event.user_id,
                        message=fulfillment_text,
                        random_id=random.randint(1, 1000000)
                    )

            except Exception as e:
                logging.error(f"VK Dialogflow Error: {e}")


def main():
    env = Env()
    env.read_env()

    PROJECT_ID = env.str('PROJECT_ID')
    LANGUAGE_CODE = env.str('LANGUAGE_CODE')
    ADMIN_CHAT_ID = env.str('ADMIN_CHAT_ID', default=None)

    TG_TOKEN = env.str('TG_TOKEN', default=None)

    VK_TOKEN = env.str('VK_TOKEN', default=None)

    key_path = env.str('GOOGLE_APPLICATION_CREDENTIALS', None)
    if key_path:
        expanded_path = os.path.expanduser(key_path)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = expanded_path
        if not ADMIN_CHAT_ID:
            print("ADMIN_CHAT_ID не задан. Логов в Telegram не будет!")

    log_bot = None
    if TG_TOKEN:
        try:
            log_bot = telegram.Bot(token=TG_TOKEN)
            log_bot.get_me()
            print("Бот для логирования инициализирован.")
        except Exception as e:
            print(f"Ошибка инициализации бота для логов: {e}")
            log_bot = None

    setup_logging(log_bot, ADMIN_CHAT_ID)

    if log_bot and ADMIN_CHAT_ID:
        try:
            log_bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(
                    "Сервис ботов запущен!\n\n"
                    "Telegram: Активен\n"
                    "VK:Активен\n"
                    "Ошибки будут приходить сюда."""
                )
            )
        except Exception:
            pass

    threads = []

    if TG_TOKEN:
        t_tg = threading.Thread(
            target=run_telegram_bot,
            args=(TG_TOKEN, PROJECT_ID, LANGUAGE_CODE, log_bot),
            name="TG_Bot_Thread",
            daemon=True
        )
        t_tg.start()
        threads.append(t_tg)

    if VK_TOKEN:
        t_vk = threading.Thread(
            target=run_vk_bot,
            args=(VK_TOKEN, PROJECT_ID, LANGUAGE_CODE),
            name="VK_Bot_Thread",
            daemon=True
        )
        t_vk.start()
        threads.append(t_vk)

    if not threads:
        logging.error("Не запущено ни одного бота. Проверьте токены в .env")
        return

    logging.info("Все боты запущены в отдельных потоках")

    try:
        while True:
            time.sleep(1)
            alive_threads = [t for t in threads if t.is_alive()]
            if not alive_threads:
                logging.critical(
                    "Все потоки ботов остановлены! Перезапуск процесса."
                )
                break
    except KeyboardInterrupt:
        logging.info(
            "Получен сигнал остановки (Ctrl+C). Завершение работы..."
        )
    except Exception as e:
        logging.critical(f"Критический сбой основного процесса: {e}")


if __name__ == "__main__":
    main()
