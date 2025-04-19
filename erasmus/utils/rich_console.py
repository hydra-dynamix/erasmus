from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from typing import Any, Optional


# Singleton Console instance
def get_console() -> Console:
    if not hasattr(get_console, "_console"):
        get_console._console = Console()
    return get_console._console


def print_panel(content: str, title: Optional[str] = None, style: str = "bold blue"):
    console = get_console()
    panel = Panel(content, title=title, style=style)
    console.print(panel)


def print_table(headers: list[str], rows: list[list[Any]], title: Optional[str] = None):
    console = get_console()
    table = Table(title=title)
    for header in headers:
        table.add_column(header)
    for row in rows:
        table.add_row(*[str(cell) for cell in row])
    console.print(table)


def print_syntax(code: str, language: str = "python", title: Optional[str] = None):
    console = get_console()
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    if title:
        console.print(Panel(syntax, title=title))
    else:
        console.print(syntax)


def print_success(message: str):
    console = get_console()
    console.print(f"[bold green]✔ {message}")


def print_error(message: str):
    console = get_console()
    console.print(f"[bold red]✖ {message}")


def print_warning(message: str):
    console = get_console()
    console.print(f"[bold yellow]! {message}")


def print_info(message: str):
    console = get_console()
    console.print(f"[bold blue]ℹ {message}")
