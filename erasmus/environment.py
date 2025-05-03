"""Environment configuration management."""

import re
import os
import sys
from pathlib import Path
from typing_extensions import Callable
from pydantic import BaseModel, ConfigDict, Field
from getpass import getpass
from dotenv import load_dotenv
from typing import Optional, Dict, Any
from loguru import logger

load_dotenv()


class EnvironmentError(Exception):
    """Base exception for environment configuration errors."""

    pass


def is_sensitive_variable(name: str) -> bool:
    """
    Check if a variable name contains common sensitive terms.

    Args:
        name: The variable name to check

    Returns:
        True if the variable is likely sensitive, False otherwise
    """
    sensitive_terms = [
        "key",
        "token",
        "secret",
        "password",
        "credential",
        "auth",
        "api_key",
        "access_token",
        "private",
        "ssh",
        "certificate",
    ]

    name_lower = name.lower()
    return any(term in name_lower for term in sensitive_terms)


def mask_sensitive_value(value: str) -> str:
    """
    Mask a sensitive value for display.

    Args:
        value: The value to mask

    Returns:
        Masked value (first 2 chars + 3 stars)
    """
    if not value or len(value) <= 2:
        return "***"
    return value[:2] + "***"


class VariableDefinition(BaseModel):
    """Definition of an environment variable."""

    name: str
    type: type
    required: bool = True
    default: Any = None
    validator: Callable[[Any], bool] | None = None
    min_value: Any = None
    max_value: Any = None
    pattern: str | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def is_sensitive(self) -> bool:
        """Check if this variable is sensitive."""
        return is_sensitive_variable(self.name)


class EnvironmentConfig(BaseModel):
    """Manages environment configuration with validation."""

    definitions: Dict[str, VariableDefinition] = {}
    _variables: Dict[str, Any] = {}
    GITHUB_TOKEN: Optional[str] = Field(None, description="GitHub personal access token")
    ERASMUS_DEBUG: bool = Field(False, description="Enable debug logging")
    ERASMUS_LOG_LEVEL: str = Field(
        "INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    def list_variables(self):
        """List all currently defined environment variables.

        Returns:
            list: A list of dictionaries containing variable details.
        """
        for name, definition in self.definitions.items():
            if definition.is_sensitive:
                print(f"{name}: ****")
            else:
                print(f"{name}: {self._variables[name]}")

    def define_required(self, name: str, type_: type, **kwargs) -> None:
        """Define a required environment variable."""
        self.definitions[name] = VariableDefinition(name=name, type=type_, required=True, **kwargs)

    def define_optional(self, name: str, type_: type, **kwargs) -> None:
        """Define an optional environment variable."""
        self.definitions[name] = VariableDefinition(name=name, type=type_, required=False, **kwargs)

    def set(self, name: str, value: str) -> None:
        """Set an environment variable value."""
        if name not in self.definitions:
            raise EnvironmentError(f"Variable {name} not defined")

        definition = self.definitions[name]
        try:
            # Convert value to the specified type
            converted_value = definition.type(value)

            # Apply validation
            if definition.min_value is not None and converted_value < definition.min_value:
                raise EnvironmentError(
                    f"{name} must be greater than or equal to {definition.min_value}"
                )

            if definition.max_value is not None and converted_value > definition.max_value:
                raise EnvironmentError(
                    f"{name} must be less than or equal to {definition.max_value}"
                )

            if definition.pattern is not None and isinstance(converted_value, str):
                if not re.match(definition.pattern, converted_value):
                    raise EnvironmentError(f"{name} must match pattern {definition.pattern}")

            if definition.validator is not None and not definition.validator(converted_value):
                raise EnvironmentError(f"{name} failed custom validation")

            self._variables[name] = converted_value

        except (ValueError, TypeError) as e:
            raise EnvironmentError(f"Invalid value for {name}: {str(e)}")

    def get(self, name: str, default: Any = None) -> Any:
        """
        Get an environment variable value.

        Args:
            name: The variable name
            default: Default value if not found

        Returns:
            The variable value or default
        """
        if name not in self._variables:
            return default
        return self._variables[name]

    def get_masked(self, name: str) -> str:
        """
        Get a masked representation of a variable value.

        Args:
            name: The variable name

        Returns:
            Masked value if sensitive, actual value otherwise
        """
        if name not in self._variables:
            return ""

        value = self._variables[name]
        definition = self.definitions[name]

        if definition.is_sensitive and isinstance(value, str):
            return mask_sensitive_value(value)
        return str(value)

    def load_from_file(self, file_path: str | Path) -> None:
        """Load environment variables from a file."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise EnvironmentError(f"Environment file not found: {file_path}")

        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        name, value = line.split("=", 1)
                        name = name.strip()
                        value = value.strip()
                        self.set(name, value)
                    except ValueError:
                        continue

    def load_from_system(self) -> None:
        """Load environment variables from system environment."""
        for name, definition in self.definitions.items():
            if name in os.environ:
                self.set(name, os.environ[name])

    def prompt_for_missing(self) -> None:
        """Prompt for missing required variables."""
        for name, definition in self.definitions.items():
            if name not in self._variables and definition.required:
                if definition.is_sensitive:
                    value = getpass(f"Enter value for {name}: ")
                else:
                    value = input(f"Enter value for {name}: ")
                self.set(name, value)

    def validate(self) -> None:
        """Validate all required variables are set."""
        missing = []
        for name, definition in self.definitions.items():
            if definition.required and name not in self._variables:
                missing.append(name)

        if missing:
            raise EnvironmentError(f"Missing required variables: {', '.join(missing)}")

    def merge(self, other: "EnvironmentConfig") -> None:
        """
        Merge another config into this one.

        Args:
            other: The other config to merge
        """
        self.definitions.update(other.definitions)
        self._variables.update(other._variables)

    @classmethod
    def load(cls) -> "EnvironmentConfig":
        """Load environment configuration from environment variables."""
        env_vars = {
            "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN"),
            "ERASMUS_DEBUG": os.getenv("ERASMUS_DEBUG", "false").lower() == "true",
            "ERASMUS_LOG_LEVEL": os.getenv("ERASMUS_LOG_LEVEL", "INFO").upper(),
        }

        # Configure logging based on environment
        logger.remove()  # Remove default handler
        log_level = env_vars["ERASMUS_LOG_LEVEL"]
        if env_vars["ERASMUS_DEBUG"]:
            log_level = "DEBUG"

        # Add a new handler with the correct level
        logger.add(
            sys.stderr,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            filter=lambda record: record["level"].name >= log_level,
        )

        return cls(**env_vars)


# Global environment configuration instance
_env_config: Optional[EnvironmentConfig] = None


def get_env_config() -> EnvironmentConfig:
    """Get the environment configuration singleton."""
    global _env_config
    if _env_config is None:
        _env_config = EnvironmentConfig.load()
    return _env_config


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled."""
    return get_env_config().ERASMUS_DEBUG
