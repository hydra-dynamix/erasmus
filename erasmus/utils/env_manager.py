"""Environment variable management."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from .path_constants import DEFAULT_IDE_ENV
from rich.prompt import Prompt
from rich.console import Console

console = Console()


class EnvironmentManager:
    """Singleton class for managing environment variables."""

    _instance: Optional["EnvironmentManager"] = None
    _ide_env: Optional[str] = None
    _env_vars: Dict[str, str] = {}
    _api_key: Optional[str] = None
    _base_url: Optional[str] = None
    _model: Optional[str] = None

    def __new__(cls) -> "EnvironmentManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_environment()
        return cls._instance

    def _load_environment(self) -> None:
        """Load environment variables from .env file."""
        # Load .env file if it exists
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)

        # Set IDE environment
        self._ide_env = os.getenv("IDE_ENV", "").lower()
        if not self._ide_env:
            self._ide_env = DEFAULT_IDE_ENV

        # Load all environment variables
        self._env_vars = {key: os.getenv(key, "") for key in os.environ}

    @property
    def ide_env(self) -> str:
        """Get the current IDE environment."""
        return self._ide_env

    def set_ide_env(self, value: str) -> None:
        """Set the IDE environment and update .env file."""
        value = value.lower()
        if not (value.startswith("c") or value.startswith("w")):
            raise ValueError("IDE_ENV must start with 'C' for cursor or 'W' for windsurf")

        # Map to full IDE name
        if value.startswith("w"):
            value = "windsurf"
        elif value.startswith("c"):
            value = "cursor"

        # Update environment variable
        os.environ["IDE_ENV"] = value
        self._ide_env = value
        self._env_vars["IDE_ENV"] = value

        # Update .env file
        self._update_env_file()

    def set_env_var(self, key: str, value: str) -> None:
        """Set an environment variable and update .env file."""
        # Update environment variable
        os.environ[key] = value
        self._env_vars[key] = value

        # Update .env file
        self._update_env_file()

    def get_env_var(self, key: str, default: str = "") -> str:
        """Get an environment variable value."""
        return self._env_vars.get(key, default)

    def _update_env_file(self) -> None:
        """Update the .env file with all environment variables."""
        env_path = Path(".env")

        # Read existing content if file exists
        existing_content = {}
        if env_path.exists():
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        existing_content[key.strip()] = value.strip()

        # Update with current environment variables
        for key, value in self._env_vars.items():
            existing_content[key] = value

        # Write updated content
        content = []
        for key, value in existing_content.items():
            content.append(f"{key}={value}")

        # Write to file
        env_path.write_text("\n".join(content) + "\n")

    def prompt_for_ide_env(self) -> str:
        """Prompt the user for the IDE environment."""
        while not self.is_windsurf or not self.is_cursor:
            user_input = Prompt.ask("Enter the IDE environment (windsurf/cursor)")
            if user_input.lower().startswith("w"):
                self._ide_env = "windsurf"
            if user_input.lower().startswith("c"):
                self._ide_env = "cursor"
            console.print("[red]Invalid IDE environment. Please enter 'windsurf' or 'cursor'[/red]")
        return self._ide_env

    @property
    def is_cursor(self) -> bool:
        """Check if the current IDE is Cursor."""
        return self._ide_env.startswith("c")

    @property
    def is_windsurf(self) -> bool:
        """Check if the current IDE is Windsurf."""
        return self._ide_env.startswith("w")

    def prompt_for_openai_credentials(self) -> None:
        """Prompt the user for OpenAI credentials."""
        self._api_key = Prompt.ask("Enter your OpenAI API key")
        self._base_url = Prompt.ask("Enter your OpenAI base URL")
        self._model = Prompt.ask("Enter your OpenAI model")

    def get_openai_credentials():
        """Get OpenAI credentials from environment variables."""
        api_key = os.environ.get("OPENAI_API_KEY", "sk-1234")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        return api_key, base_url, model
