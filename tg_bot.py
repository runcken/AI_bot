import logging
import os
from environs import Env
from google.cloud import dialogflow
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


def start(update, context):
    user = update.message.from_user
    update.message.reply_text(f'Здравствуйте, {user.first_name}!')


def detect_intent_texts(project_id, session_id, text, language_code):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    text_input = dialogflow.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(
        request={"session": session, "query_input": query_input}
    )
    return response.query_result.fulfillment_text


def handle_message(update, context):
    user_text = update.message.text
    session_id = str(update.effective_chat.id)

    project_id = context.bot_data.get('project_id')
    if not project_id:
        update.message.reply_text("Ошибка конфигурации бота")
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
        logging.error(f"Ошибка при вызове Dialogflow: {e}")
        update.message.reply_text("Произошла ошибка. Попробуйте позже.")


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    env = Env()
    env.read_env()
    tg_token = env.str('TG_TOKEN')
    project_id = env.str('PROJECT_ID')
    language_code = env.str('LANGUAGE_CODE')

    key_path = env.str('GOOGLE_APPLICATION_CREDENTIALS')
    if key_path:
        expanded_path = os.path.expanduser(key_path)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = expanded_path
        print(f"Установлен путь к ключу: {expanded_path}")
    else:
        print("GOOGLE_APPLICATION_CREDENTIALS не задан")

    updater = Updater(tg_token, use_context=True)
    dp = updater.dispatcher

    dp.bot_data['project_id'] = project_id
    dp.bot_data['language_code'] = language_code

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(
        MessageHandler(Filters.text & ~Filters.command, handle_message)
    )

    print('Бот запущен...')
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
