# AI_bot
Bot for response on messages using DialogFlow, in Telegram and VK

It seems something like this:

![ai_bot](https://github.com/user-attachments/assets/394e47f7-89bb-43c9-a7a4-14d5beee620a)



## How to install

Clone repository to your local device. To avoid problems with installing required additinal packages, its strongly to use a virtual environment [virtualenv/venv](https://docs.python.org/3/library/venv.html), for example:

```bash
python3 -m venv myenv
source myenv/bin/activate
```

## Environment

### Requirements

Python3.12 should be already installed. Then use pip (or pip3, if there is a conflict with Python2) to install dependencies:

```bash
pip install -r requirements.txt
```

The script uses additinal packages:

- python-telegram-bot==13.7
- urllib3==1.26.18
- environs==14.5.0
- vk_api==11.10.0
- google-cloud-dialogflow==2.46.0
- google-cloud-api-keys==0.7.0

### Environment variables

- TG_TOKEN - tg bot's token
- ADMIN_CHAT_ID - user id for sending logs
- PROJECT_ID - project id in DialogFlow
- LANGUAGE_CODE - 'ru' for russian language
- GOOGLE_APPLICATION_CREDENTIALS - path to json file with google credentials
- VK_TOKEN - VK group token

1. Put `.env` file near `bot.py`.
2. `.env` contains text data without quotes.


## Run

Launch on Linux(Python 3) or Windows:

```bash
python3 bot.py
```

and you will communicate with a bot


## Notes

The file with the contents of these environment variables isnt included in the repository.

How to get them? Here [DialogFlow site](https://dialogflow.cloud.google.com/#/getStarted)

You will need a project in DialogFlow, [how to create it](https://docs.cloud.google.com/dialogflow/es/docs/quick/setup), and after [create agent](https://docs.cloud.google.com/dialogflow/es/docs/quick/build-agent).

And after that, create [Coogle Application Credentials](https://docs.cloud.google.com/dialogflow/es/docs/quick/setup#sdk)

After running this commands json file with credentials will be saved in your home folder.

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project PROJECT_ID
```

And you also reqiured DialogFlow token, for it run this script:

```python

from google.cloud import api_keys_v2
from google.cloud.api_keys_v2 import Key


def create_api_key(project_id: str, suffix: str) -> Key:
    """
    Creates and restrict an API key. Add the suffix for uniqueness.

    TODO(Developer):
    1. Before running this sample,
      set up ADC as described in https://cloud.google.com/docs/authentication/external/set-up-adc
    2. Make sure you have the necessary permission to create API keys.

    Args:
        project_id: Google Cloud project id.

    Returns:
        response: Returns the created API Key.
    """
    # Create the API Keys client.
    client = api_keys_v2.ApiKeysClient()

    key = api_keys_v2.Key()
    key.display_name = f"My first API key - {suffix}"

    # Initialize request and set arguments.
    request = api_keys_v2.CreateKeyRequest()
    request.parent = f"projects/{project_id}/locations/global"
    request.key = key

    # Make the request and wait for the operation to complete.
    response = client.create_key(request=request).result()

    print(f"Successfully created an API key: {response.name}")
    # For authenticating with the API key, use the value in "response.key_string".
    # To restrict the usage of this API key, use the value in "response.name".
    return response
```

## Project Goals

The code is written for educational purposes on online-course for web-developers dvmn.org.
