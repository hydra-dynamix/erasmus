# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "openai",
#     "python-dotenv",
# ]
# ///
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)
model = os.getenv("OPENAI_MODEL", "gpt-4.1")

messages = [
    {
        "role": "system",
        "content": "You are a helpful assistant.",
    },
    {
        "role": "user",
        "content": "Hello, how are you?",
    },
]

response = client.chat.completions.create(
    model=model,
    messages=messages,
    stream=True,
)

full_response = ""
for chunk in response:
    print(chunk.choices[0].delta.content, end="", flush=True)
    if chunk.choices[0].delta.content:
        full_response += chunk.choices[0].delta.content
