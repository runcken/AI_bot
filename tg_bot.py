import logging
import os
import sys
import telegram
from environs import Env
from google.cloud import dialogflow
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from dialogflow_service import detect_intent_texts


class TelegramLogsHandler(logging.Handler):
    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.tg_bot = tg_bot
        self.chat_id = chat_id
        self.setLevel(logging.ERROR)
        self._is_sending = False

    def emit(self, record):
        if self._is_sending:
            return

        try:
            self._is_sending = True
            log_entry = self.format(record)

            if len(log_entry) > 4096:
                log_entry = log_entry[:4090]

            self.tg_bot.send_message(
                chat_id=self.chat_id,
                text=f"Ошибка в работе бота:\n{log_entry}"
            )
        except Exception as e:
            print(f"Не удалось отправить лог в Telegram. Ошибка: {e}")
        finally:
            self._is_sending = False


def start(update, context):
    user = update.message.from_user
    update.message.reply_text(f'Здравствуйте, {user.first_name}!')


def handle_message(update, context):
    user_text = update.message.text
    raw_id = str(update.effective_chat.id)
    session_id = f"tg-{raw_id}"

    project_id = context.bot_data.get('project_id')
    if not project_id:
        logging.error("Конфигурация: PROJECT_ID отсутствует")
        update.message.reply_text("Ошибка конфигурации бота.")
        return

    language_code = context.bot_data.get('language_code')

    try:
        fulfillment_text = detect_intent_texts(
            project_id,
            session_id,
            user_text,
            language_code
        )
        if fulfillment_text:
            update.message.reply_text(fulfillment_text)
        else:
            update.message.reply_text("Извините, я не понял вопрос.")

    except Exception as e:
        logging.error(f"Dialogflow Error: {e}")
        update.message.reply_text("Произошла ошибка. Попробуйте позже.")


def main():
    env = Env()
    env.read_env()

    tg_token = env.str('TG_TOKEN')
    project_id = env.str('PROJECT_ID')
    language_code = env.str('LANGUAGE_CODE')
    admin_chat_id = env.str('ADMIN_CHAT_ID')

    key_path = env.str('GOOGLE_APPLICATION_CREDENTIALS')
    if key_path:
        expanded_path = os.path.expanduser(key_path)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = expanded_path
        print(f"Установлен путь к ключу: {expanded_path}")

    try:
        log_bot = telegram.Bot(token=tg_token)
        log_bot.get_me()
    except Exception as e:
        print(f"Не удалось создать бота для логов: {e}")
        return

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    root_logger = logging.getLogger()

    tg_handler = TelegramLogsHandler(log_bot, admin_chat_id)
    tg_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    )
    root_logger.addHandler(tg_handler)

    logging.info("Логгирование запущено.")

    updater = Updater(tg_token, use_context=True)
    dp = updater.dispatcher

    dp.bot_data['project_id'] = project_id
    dp.bot_data['language_code'] = language_code

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(
        MessageHandler(Filters.text & ~Filters.command, handle_message)
    )
    print('TG бот запущен (polling started)...')

    if admin_chat_id:
        try:
            log_bot.send_message(
                chat_id=admin_chat_id,
                text="TG бот запущен..."
            )
        except Exception as e:
            print(f"Не удалось отправить сообщение: {e}")

    try:
        updater.start_polling()
        updater.idle()
    except KeyboardInterrupt:
        logging.info("Остановка бота пользователем.")
    except Exception as e:
        logging.critical(f"Критический сбой бота: {e}")


if __name__ == '__main__':
    main()
