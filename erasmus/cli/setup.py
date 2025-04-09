"""Setup command for environment configuration."""
import os
import re
from pathlib import Path
from typing import Dict, Optional, Callable

import click
from rich.console import Console
from rich.prompt import Prompt

console = Console()

def validate_ide_env(value: str) -> str:
    """Validate and transform IDE_ENV value."""
    # Convert to uppercase for consistency
    value = value.upper()
    
    # Check first letter and standardize
    if value.startswith('C'):
        return 'CURSOR'
    elif value.startswith('W'):
        return 'WINDSURF'
    else:
        raise ValueError("IDE_ENV must start with 'C' for Cursor or 'W' for Windsurf")

def validate_base_url(value: str) -> str:
    """Validate OPENAI_BASE_URL value."""
    # Allow localhost with optional port
    localhost_pattern = r'^https?://localhost(?::\d+)?(?:/.*)?$'
    # Standard URL pattern
    url_pattern = r'^https?://[a-zA-Z0-9.-]+(?::\d+)?(?:/.*)?$'
    
    if re.match(localhost_pattern, value) or re.match(url_pattern, value):
        return value
    raise ValueError("Invalid URL format. Must be a valid HTTP/HTTPS URL or localhost")

# Validation rules for specific fields
FIELD_VALIDATORS: Dict[str, Callable[[str], str]] = {
    'IDE_ENV': validate_ide_env,
    'OPENAI_BASE_URL': validate_base_url,
}

def read_env_example() -> Dict[str, str]:
    """Read default values from .env.example file."""
    defaults = {}
    example_path = Path(".env.example")
    
    if not example_path.exists():
        raise FileNotFoundError(".env.example not found. Please ensure it exists in the project root.")
        
    with example_path.open() as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                defaults[key.strip()] = value.strip()
                
    return defaults

def write_env_file(values: Dict[str, str]) -> None:
    """Write values to .env file."""
    env_path = Path(".env")
    
    # Ensure parent directory exists
    env_path.parent.mkdir(parents=True, exist_ok=True)
    
    with env_path.open('w') as f:
        for key, value in values.items():
            f.write(f"{key}={value}\n")

def create_default_env_example() -> None:
    """Create a default .env.example file."""
    with open(".env.example", "w") as f:
        f.write("IDE_ENV=CURSOR\n")
        f.write("GIT_TOKEN=\n")
        f.write("OPENAI_API_KEY=\n")
        f.write("OPENAI_BASE_URL=https://api.openai.com/v1\n")
        f.write("OPENAI_MODEL=gpt-4\n")

def prompt_for_values(defaults: Dict[str, str]) -> Dict[str, str]:
    """Prompt user for each environment variable, showing defaults."""
    values = {}
    
    console.print("\n[bold blue]Environment Configuration[/bold blue]")
    console.print("Press Enter to accept the default value or input a new value.\n")
    
    for key, default in defaults.items():
        while True:
            try:
                # Show default and get user input
                value = Prompt.ask(
                    f"[yellow]{key}[/yellow] (default: [green]{default}[/green])",
                    default=default
                )
                
                # Apply validation if exists for this field
                if key in FIELD_VALIDATORS:
                    value = FIELD_VALIDATORS[key](value)
                    
                values[key] = value
                break  # Break the loop if validation passes
                
            except ValueError as e:
                console.print(f"[red]Error: {str(e)}[/red]")
                console.print("Please try again.")
        
    return values

@click.command()
def setup():
    """Set up environment configuration with interactive prompts."""
    try:
        # Read defaults from .env.example
        try:
            defaults = read_env_example()
        except FileNotFoundError as e:
            console.print(f"\n[red]Error: {str(e)}[/red]")
            if click.confirm("Would you like to create a default .env.example?", default=False):
                create_default_env_example()
                console.print("[green].env.example created with default values.[/green]")
                defaults = read_env_example()
            else:
                console.print("[red]Setup cancelled. Please create .env.example and try again.[/red]")
                return
        
        # Validate defaults
        for key, value in defaults.items():
            if key in FIELD_VALIDATORS:
                try:
                    defaults[key] = FIELD_VALIDATORS[key](value)
                except ValueError as e:
                    console.print(f"[red]Warning: Default value for {key} is invalid: {str(e)}[/red]")
        
        # Check if .env already exists
        if Path(".env").exists():
            overwrite = Prompt.ask(
                "\n[yellow].env file already exists. Do you want to reconfigure?[/yellow]",
                choices=["y", "n"],
                default="n"
            )
            if overwrite.lower() != "y":
                console.print("[red]Setup cancelled.[/red]")
                return
                
        # Prompt for values
        values = prompt_for_values(defaults)
        
        # Write to .env file
        write_env_file(values)
        
        console.print("\n[green]Environment configuration completed successfully![/green]")
        console.print("The .env file has been created with your settings.")
        
    except Exception as e:
        console.print(f"\n[red]Error during setup: {str(e)}[/red]")
        return 1  # Return error code instead of raising 