import os
from dotenv import load_dotenv
import openai

load_dotenv()

openai.api_key = os.getenv('API_KEY')

path = os.path.dirname(__file__)
prompt_path = os.path.join(path, "prompt.txt")


if not os.path.exists(prompt_path):
    raise FileNotFoundError('No prompt.txt file found')

with open(prompt_path, 'r') as file:
    SYSTEM_PROMPT = file.read().replace('\n', ' ')


def chatgpt_response(prompt: str, memory):
    prompt = prompt.replace('<@1137755546007646291>', '')
    prompt = prompt.strip()
    memory.append({"role": "user", "content": prompt})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *memory],
        max_tokens=100,
        temperature=1
    )
    message_content = response['choices'][0]['message']
    memory.append(message_content.to_dict())
    return message_content['content']