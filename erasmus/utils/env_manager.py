"""Environment variable management."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from .path_constants import DEFAULT_IDE_ENV


class EnvironmentManager:
    """Singleton class for managing environment variables."""

    _instance: Optional["EnvironmentManager"] = None
    _ide_env: Optional[str] = None

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

    @property
    def ide_env(self) -> str:
        """Get the current IDE environment."""
        return self._ide_env

    def set_ide_env(self, value: str) -> None:
        """Set the IDE environment and update .env file."""
        value = value.lower()
        if not (value.startswith("c") or value.startswith("w")):
            raise ValueError("IDE_ENV must start with 'C' for cursor or 'W' for windsurf")

        # Update environment variable
        os.environ["IDE_ENV"] = value
        self._ide_env = value

        # Update .env file
        env_path = Path(".env")
        if env_path.exists():
            content = env_path.read_text()
            if "IDE_ENV=" in content:
                # Replace existing IDE_ENV
                lines = content.splitlines()
                new_lines = []
                for line in lines:
                    if line.startswith("IDE_ENV="):
                        new_lines.append(f"IDE_ENV={value}")
                    else:
                        new_lines.append(line)
                env_path.write_text("\n".join(new_lines))
            else:
                # Append IDE_ENV
                with env_path.open("a") as f:
                    f.write(f"\nIDE_ENV={value}\n")
        else:
            # Create new .env file
            env_path.write_text(f"IDE_ENV={value}\n")

    @property
    def is_cursor(self) -> bool:
        """Check if the current IDE is Cursor."""
        return self._ide_env.startswith("c")

    @property
    def is_windsurf(self) -> bool:
        """Check if the current IDE is Windsurf."""
        return self._ide_env.startswith("w")
