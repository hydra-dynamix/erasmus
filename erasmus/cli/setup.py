"""Setup command for environment configuration."""

import re
from collections.abc import Callable
from pathlib import Path

import click
from rich.console import Console
from rich.prompt import Prompt

from erasmus.utils.env_manager import EnvironmentManager

console = Console()


def validate_base_url(value: str) -> str:
    """Validate and transform OPENAI_BASE_URL value."""
    if not value:
        return "https://api.openai.com/v1"

    # Ensure URL starts with http:// or https://
    if not value.startswith(("http://", "https://")):
        value = "https://" + value

    # Remove trailing slash
    return value.rstrip("/")


# Validation rules for specific fields
FIELD_VALIDATORS: dict[str, Callable[[str], str]] = {
    "OPENAI_BASE_URL": validate_base_url,
}


def read_env_example() -> dict[str, str]:
    """Read default values from .env.example file."""
    defaults = {}
    example_path = Path(".env.example")

    if not example_path.exists():
        raise FileNotFoundError(
            ".env.example not found. Please ensure it exists in the project root."
        )

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
        "IDE_ENV": f"Select IDE environment (C)ursor or (W)indsurf [{defaults.get('IDE_ENV', 'C')}]: ",
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
                    values[key] = value
                    break
                console.print(
                    "[red]Invalid IDE environment. Must start with 'C' for Cursor or 'W' for Windsurf[/red]"
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
    """Write environment variables to .env file."""
    env_path = Path(".env")

    # Read existing content if file exists
    existing_content = ""
    if env_path.exists():
        existing_content = env_path.read_text()

    # Prepare new content
    new_lines = []
    existing_vars = set()

    # Process existing content
    for line in existing_content.splitlines():
        if line.strip() and not line.startswith("#"):
            key = line.split("=", 1)[0].strip()
            existing_vars.add(key)
            if key in values:
                new_lines.append(f"{key}={values[key]}")
                del values[key]
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Add remaining new variables
    for key, value in values.items():
        if key not in existing_vars:
            new_lines.append(f"{key}={value}")

    # Write to file
    env_path.write_text("\n".join(new_lines))


@click.command()
def setup():
    """Set up environment configuration with interactive prompts."""
    try:
        # Read defaults from .env.example
        defaults = read_env_example()

        # Get prompts and values
        default_prompts = get_default_prompts(defaults)
        values = prompt_for_values(default_prompts, defaults)

        # Write to .env file
        write_env_file(values)

        # Update environment manager
        env_manager = EnvironmentManager()
        env_manager.set_ide_env(values.get("IDE_ENV", ""))

        # Now that IDE_ENV is set, run setup_project
        from erasmus.utils.context import setup_project

        setup_project()

        console.print("\n[green]Environment configuration completed successfully![/green]")
        console.print("The .env file has been created with your settings.")

    except Exception as e:
        console.print(f"\n[red]Error during setup: {e!s}[/red]")
        return 1  # Return error code instead of raising


if __name__ == "__main__":
    setup()
