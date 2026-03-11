import logging
import os
import random

import vk_api as vk
from vk_api.longpoll import VkLongPoll, VkEventType
from environs import Env
from google.cloud import dialogflow


def detect_intent_texts(project_id, session_id, text, language_code):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    text_input = dialogflow.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(
        request={"session": session, "query_input": query_input}
    )
    return response.query_result.fulfillment_text


def handle_message(event, vk_api, project_id, language_code):
    user_text = event.text
    session_id = str(event.user_id)

    try:
        fulfillment_text = detect_intent_texts(
            project_id,
            session_id,
            user_text,
            language_code
        )
        if fulfillment_text:
            vk_api.messages.send(
                user_id=event.user_id,
                message=fulfillment_text,
                random_id=random.randint(1, 1000)
            )
        else:
            vk_api.messages.send(
                user_id=event.user_id,
                message="Извините, я не понял вопрос.",
                random_id=random.randint(1, 1000)
            )
    except Exception as e:
        logging.error(f"Ошибка при вызове Dialogflow: {e}")
        vk_api.messages.send(
            user_id=event.user_id,
            message="Произошла ошибка. Попробуйте позже.",
            random_id=random.randint(1, 1000)
        )


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    env = Env()
    env.read_env()
    vk_token = env.str('VK_TOKEN')
    project_id = env.str('PROJECT_ID')
    key_path = env.str('GOOGLE_APPLICATION_CREDENTIALS', None)

    if key_path:
        expanded_path = os.path.expanduser(key_path)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = expanded_path
        print(f"Установлен путь к ключу: {expanded_path}")
    else:
        print("GOOGLE_APPLICATION_CREDENTIALS не задан")

    language_code = env.str('LANGUAGE_CODE')
    vk_session = vk.VkApi(token=vk_token)
    vk_api = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)

    print("VK бот с DialogFlow запущен...")

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            handle_message(event, vk_api, project_id, language_code)


if __name__ == "__main__":
    main()
