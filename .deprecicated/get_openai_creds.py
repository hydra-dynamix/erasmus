from dotenv import load_dotenv
from getpass import getpass
from pathlib import Path
import re

load_dotenv()

def is_valid_url(url: str) -> bool:
    """Basic URL validation using regex."""
    https_pattern = re.match(r'^https?://', url)
    http_pattern = re.match(r'^http?://', url)
    return https_pattern or http_pattern

def prompt_openai_credentials(env_path=".env"):
    """Prompt user for OpenAI credentials and save to .env"""
    api_key = getpass("Enter your OPENAI_API_KEY (input hidden): ")

    base_url = input("Enter your OPENAI_BASE_URL (default: https://api.openai.com/v1): ").strip()
    if not is_valid_url(base_url):
        print("Invalid URL or empty. Defaulting to https://api.openai.com/v1")
        base_url = "https://api.openai.com/v1"

    model = input("Enter your OPENAI_MODEL (default: gpt-4o): ").strip()
    if not model:
        model = "gpt-4o"

    env_content = (
        f"OPENAI_API_KEY={api_key}\n"
        f"OPENAI_BASE_URL={base_url}\n"
        f"OPENAI_MODEL={model}\n"
    )

    Path(env_path).write_text(env_content)
    print(f"✅ OpenAI credentials saved to {env_path}")

if __name__ == "__main__":
    prompt_openai_credentials()
