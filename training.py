import argparse
import os
import json
from environs import Env
from google.cloud import dialogflow


def create_intent(
        project_id,
        display_name,
        training_phrases_parts,
        message_texts):
    intents_client = dialogflow.IntentsClient()
    parent = dialogflow.AgentsClient.agent_path(project_id)

    training_phrases = []
    for training_phrases_part in training_phrases_parts:
        part = dialogflow.Intent.TrainingPhrase.Part(
            text=training_phrases_part
        )
        training_phrase = dialogflow.Intent.TrainingPhrase(parts=[part])
        training_phrases.append(training_phrase)

    text = dialogflow.Intent.Message.Text(text=[message_texts])
    message = dialogflow.Intent.Message(text=text)

    intent = dialogflow.Intent(
        display_name=display_name,
        training_phrases=training_phrases,
        messages=[message]
    )

    response = intents_client.create_intent(
        request={"parent": parent, "intent": intent}
    )

    return response


def create_intents_from_json(project_id, json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as file:
        intents = json.load(file)

    for intent_name, intent in intents.items():
        questions = intent['questions']
        answer = intent['answer']

        create_intent(
            project_id=project_id,
            display_name=intent_name,
            training_phrases_parts=questions,
            message_texts=answer
        )


def main():
    parser = argparse.ArgumentParser(
        description="Скрипт для создания интентов из json файла."
    )
    parser.add_argument(
        '--file',
        type=str,
        default='intents.json',
        help='Путь к файлу с интентами (по умолчанию: intents.json)'
    )
    args = parser.parse_args()

    env = Env()
    env.read_env()
    project_id = env.str('PROJECT_ID')
    json_file_path = args.file
    key_path = env.str('GOOGLE_APPLICATION_CREDENTIALS')

    if key_path:
        expanded_path = os.path.expanduser(key_path)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = expanded_path
        print(f"Установлен путь к ключу: {expanded_path}")
    else:
        print("GOOGLE_APPLICATION_CREDENTIALS не задан")
        return

    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            intents = json.load(file)

        print(f"Найдено интентов для создания: {len(intents)}")

        for intent_name, intent in intents.items():
            questions = intent['questions']
            answer = intent['answer']

            print(f"Создаю интент: {intent_name}")
            print(f" Вопросов: {len(questions)}")
            print(f" Ответ: {answer[:50]}...")

            create_intent(
                project_id=project_id,
                display_name=intent_name,
                training_phrases_parts=questions,
                message_texts=answer
            )

            print(f"Intent '{intent_name}' created successfully")

        print("\nВсе интенты успешно созданы!")

    except FileNotFoundError:
        print(f"Ошибка: Файл {json_file_path} не найден.")
    except json.JSONDecodeError:
        print(f"Ошибка: Неверный формат JSON в файле {json_file_path}.")
    except Exception as e:
        print(f"\nПроцесс прерван из-за ошибки: {e}")


if __name__ == "__main__":
    main()
