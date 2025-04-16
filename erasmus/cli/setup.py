"""Setup command for environment configuration."""

import re
from collections.abc import Callable
from pathlib import Path
import os

import click
from rich.console import Console
from rich.prompt import Prompt

from erasmus.utils.env_manager import EnvironmentManager

console = Console()

# Export validators for external import (tests)
__all__ = ["validate_base_url", "validate_ide_env"]


def validate_base_url(value: str) -> str:
    """Validate and transform OPENAI_BASE_URL value."""
    import re
    if not value:
        return "https://api.openai.com/v1"

    # Ensure URL starts with http:// or https://
    if not value.startswith(("http://", "https://")):
        value = "https://" + value

    # Remove trailing slash
    value = value.rstrip("/")

    # Strict validation: must start with http(s):// and host must contain a dot (.) or be localhost
    url_pattern = re.compile(r"^https?://((localhost)(:\d+)?|([\w\-]+\.)+[\w\-]+(:\d+)?)(/.*)?$", re.IGNORECASE)
    if not url_pattern.match(value):
        raise ValueError(f"Invalid OPENAI_BASE_URL: {value}")
    return value


def validate_ide_env(value: str) -> str:
    """Validate and normalize IDE_ENV value ('windsurf' or 'cursor')."""
    if not value:
        raise ValueError("IDE_ENV cannot be empty")
    v = value.lower()
    if v == "windsurf" or v.startswith("w"):
        return "windsurf"
    if v == "cursor" or v.startswith("c"):
        return "cursor"
    raise ValueError(f"Invalid IDE_ENV: {value}. Must be 'windsurf' or 'cursor'.")

# Validation rules for specific fields
FIELD_VALIDATORS: dict[str, Callable[[str], str]] = {
    "OPENAI_BASE_URL": validate_base_url,
    "IDE_ENV": validate_ide_env,
}


def read_env_example() -> dict[str, str]:
    """Read default values from .env.example file. If missing, prompt to create a default."""
    import click
    defaults = {}
    example_path = Path(".env.example")

    if not example_path.exists():
        if click.confirm(".env.example not found. Would you like to create a default .env.example file?", default=True):
            # Provide sensible defaults
            defaults = {
                "IDE_ENV": "cursor",
                "GIT_TOKEN": "",
                "OPENAI_API_KEY": "sk-1234",
                "OPENAI_BASE_URL": "https://api.openai.com/v1",
                "OPENAI_MODEL": "gpt-4",
            }
            content = "\n".join(f"{k}={v}" for k, v in defaults.items()) + "\n"
            example_path.write_text(content)
            # Do NOT exit; allow setup to continue
            return defaults
        else:
            click.echo("Setup cancelled. .env.example is required.")
            raise SystemExit(1)

    with example_path.open() as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                defaults[key.strip()] = value.strip()

    return defaults


def get_default_prompts(defaults: dict[str, str]) -> dict[str, str]:
    """Get prompts for each environment variable."""
    return {
        "IDE_ENV": f"Select IDE environment (C)ursor or (W)indsurf (enter 'C' or 'W') [{defaults.get('IDE_ENV', 'C')}]: ",
        "GIT_TOKEN": f"Enter Git token [{defaults.get('GIT_TOKEN', '')}]: ",
        "OPENAI_API_KEY": f"Enter OpenAI API key [{defaults.get('OPENAI_API_KEY', '')}]: ",
        "OPENAI_BASE_URL": f"Enter OpenAI base URL [{defaults.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')}]: ",
        "OPENAI_MODEL": f"Enter OpenAI model [{defaults.get('OPENAI_MODEL', 'gpt-4')}]: ",
    }


def prompt_for_values(prompts: dict[str, str], defaults: dict[str, str]) -> dict[str, str]:
    """Prompt for environment variable values."""
    values = {}
    for key, prompt in prompts.items():
        while True:
            value = Prompt.ask(prompt, default=defaults.get(key, ""))

            # Special handling for IDE_ENV
            if key == "IDE_ENV":
                value = value.lower()
                if value.startswith(("c", "w")):
                    values[key] = value[0]  # Just take the first character
                    break
                console.print(
                    "[red]Invalid IDE environment. Please enter 'C' for Cursor or 'W' for Windsurf[/red]"
                )
                continue

            # Apply field-specific validation if available
            if key in FIELD_VALIDATORS:
                try:
                    value = FIELD_VALIDATORS[key](value)
                except ValueError as e:
                    console.print(f"[red]{str(e)}[/red]")
                    continue

            values[key] = value
            break

    return values


def write_env_file(values: dict[str, str]) -> None:
    """Write environment variables to .env file, always overwriting with provided values."""
    env_path = Path(".env")
    content = "\n".join(f"{k}={v}" for k, v in values.items()) + "\n"
    env_path.write_text(content)


def setup_env() -> None:
    """Set up environment variables and project structure."""
    try:
        # Initialize environment manager
        env_manager = EnvironmentManager()

        # Read defaults from .env.example
        defaults = read_env_example()

        # Get prompts for each environment variable
        prompts = get_default_prompts(defaults)

        # Prompt for values
        values = prompt_for_values(prompts, defaults)

        # Set environment variables
        for key, value in values.items():
            if key == "IDE_ENV":
                # Only set if not already set or if explicitly changed
                current_ide_env = env_manager.ide_env
                if not current_ide_env or current_ide_env.lower() != value.lower():
                    env_manager.set_ide_env(value)
            else:
                env_manager.set_env_var(key, value)

        # Setup project structure first
        from erasmus.utils.paths import PathManager

        path_manager = PathManager()
        path_manager.ensure_directories()

        # Set default agent to Orchestration Agent
        from erasmus.utils.protocols.manager import ProtocolManager
        import asyncio

        async def set_default_agent():
            protocol_manager = await ProtocolManager.create()
            await protocol_manager.activate_protocol("Orchestration Agent")

        # Get the current event loop or create a new one
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the async function in the event loop
        loop.run_until_complete(set_default_agent())

        console.print("✨ Environment setup complete")
        console.print("✨ Default agent set to Orchestration Agent")

    except Exception as e:
        console.print(f"❌ Environment setup failed: {e}", style="red")
        raise SystemExit(1)


if __name__ == "__main__":
    # Only run as a command when executed directly
    from erasmus.cli.commands import cli

    cli()
