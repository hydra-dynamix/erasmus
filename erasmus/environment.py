"""Environment configuration management."""

import re
import os
from pathlib import Path
from typing_extensions import Callable
from pydantic import BaseModel, ConfigDict
from getpass import getpass
from dotenv import load_dotenv

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
    default: any = None
    validator: Callable[[any], bool] | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def is_sensitive(self) -> bool:
        """Check if this variable is sensitive."""
        return is_sensitive_variable(self.name)


class EnvironmentConfig(BaseModel):
    """Manages environment configuration with validation."""

    definitions: dict[str, VariableDefinition] = {}
    _variables: dict[str, any] = {}

    def list_variables(self):
        """List all currently defined environment variables.

        Returns:
            list: A list of dictionaries containing variable details.
        """
        for name, definition in self._definitions.items():
            if definition.is_sensitive:
                print(f"{name}: ****")
            else:
                print(f"{name}: {self._variables[name]}")

    def define_required(self, name: str, type_: type, **kwargs) -> None:
        """Define a required environment variable."""
        self._definitions[name] = VariableDefinition(name=name, type=type_, required=True, **kwargs)

    def define_optional(self, name: str, type_: type, **kwargs) -> None:
        """Define an optional environment variable."""
        self._definitions[name] = VariableDefinition(
            name=name, type=type_, required=False, **kwargs
        )

    def set(self, name: str, value: str) -> None:
        """Set an environment variable value."""
        if name not in self._definitions:
            raise EnvironmentError(f"Variable {name} not defined")

        definition = self._definitions[name]
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

    def get(self, name: str, default: any = None) -> any:
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
        definition = self._definitions[name]

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
        for name, definition in self._definitions.items():
            if name in os.environ:
                self.set(name, os.environ[name])

    def prompt_for_missing(self) -> None:
        """Prompt for missing required variables."""
        for name, definition in self._definitions.items():
            if definition.required and name not in self._variables:
                if definition.is_sensitive:
                    value = getpass(f"Enter {name}: ")
                else:
                    value = input(f"Enter {name}: ")
                self.set(name, value)

    def validate(self) -> None:
        """Validate all environment variables according to their definitions."""
        for variable_key, variable_definition in self._definitions.items():
            variable_value = self._variables.get(variable_key)
            if variable_definition.required and variable_value is None:
                raise EnvironmentError(f"Missing required environment variable: {variable_key}")
            if variable_value is not None:
                if not isinstance(variable_value, variable_definition.type):
                    raise TypeError(
                        f"Environment variable '{variable_key}' should be of type {variable_definition.type.__name__}"
                    )
                if variable_definition.validator and not variable_definition.validator(
                    variable_value
                ):
                    raise ValueError(
                        f"Environment variable '{variable_key}' failed custom validation."
                    )

    def merge(self, other: "EnvironmentConfig") -> None:
        """Merge another environment configuration into this one."""
        # First merge definitions
        for name, definition in other._definitions.items():
            if name not in self._definitions:
                self._definitions[name] = definition

        # Then merge values
        for name, value in other._variables.items():
            self.set(name, str(value))
