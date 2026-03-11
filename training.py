import os
import json
from environs import Env
from google.cloud import dialogflow


def create_intent(project_id, display_name, training_phrases_parts, message_texts):
    """Create an intent of the given intent type."""
    intents_client = dialogflow.IntentsClient()
    parent = dialogflow.AgentsClient.agent_path(project_id)
    
    training_phrases = []
    for training_phrases_part in training_phrases_parts:
        part = dialogflow.Intent.TrainingPhrase.Part(text=training_phrases_part)
        training_phrase = dialogflow.Intent.TrainingPhrase(parts=[part])
        training_phrases.append(training_phrase)

    text = dialogflow.Intent.Message.Text(text=[message_texts])  # Обратите внимание: текст должен быть списком
    message = dialogflow.Intent.Message(text=text)

    intent = dialogflow.Intent(
        display_name=display_name, 
        training_phrases=training_phrases, 
        messages=[message]
    )

    response = intents_client.create_intent(
        request={"parent": parent, "intent": intent}
    )

    print(f"Intent '{display_name}' created successfully")
    return response


def create_intents_from_json(project_id, json_file_path):
    """
    Читает JSON-файл и создаёт интенты в DialogFlow
    
    Args:
        project_id: ID вашего проекта в Google Cloud
        json_file_path: путь к JSON-файлу с вопросами и ответами
    """
    # Читаем JSON-файл
    with open(json_file_path, 'r', encoding='utf-8') as file:
        intents_data = json.load(file)
    
    # Проходим по каждому интенту в JSON
    for intent_name, intent_data in intents_data.items():
        questions = intent_data['questions']
        answer = intent_data['answer']
        
        print(f"Создаю интент: {intent_name}")
        print(f"  Вопросов: {len(questions)}")
        print(f"  Ответ: {answer[:50]}...")  # Показываем первые 50 символов ответа
        
        try:
            create_intent(
                project_id=project_id,
                display_name=intent_name,
                training_phrases_parts=questions,
                message_texts=answer
            )
        except Exception as e:
            print(f"  Ошибка при создании интента '{intent_name}': {e}")
    
    print("\nВсе интенты успешно созданы!")


def main():
    env = Env()
    env.read_env()
    project_id = env.str('PROJECT_ID')
    json_file_path = "intents.json"
    key_path = env.str('GOOGLE_APPLICATION_CREDENTIALS')
    if key_path:
        expanded_path = os.path.expanduser(key_path)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = expanded_path
        print(f"Установлен путь к ключу: {expanded_path}")
    else:
        print("GOOGLE_APPLICATION_CREDENTIALS не задан")

    create_intents_from_json(project_id, json_file_path)


if __name__ == "__main__":
    main()
