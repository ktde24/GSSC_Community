import openai
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_chat_response(messages, model="gpt-4o-mini", temperature=0.3):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    print("RESPONSE >>>", response)  # or logging.info(response)
    return response.choices[0].message.content.strip()
