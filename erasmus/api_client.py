"""
OpenAI-compatible API client integration for Erasmus.
Wraps OpenAI API usage (see test.py) for local/remote inference.
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class ErasmusAPIClient:
    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(self, messages, stream=False, **kwargs):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=stream,
            **kwargs
        )
        if stream:
            return response  # caller handles streaming
        return response.choices[0].message.content
