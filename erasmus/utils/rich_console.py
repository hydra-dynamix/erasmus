from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from typing import Any, Optional
from rich.logging import RichHandler
import logging


# Singleton Console instance
def get_console() -> Console:
    if not hasattr(get_console, "_console"):
        get_console._console = Console()
    return get_console._console


def print_panel(content: str, title: str | None = None, style: str = "bold blue"):
    """Print a styled panel with optional title using Rich library.

    Args:
        content (str): The text content to display in the panel.
        title (str | None, optional): Title of the panel. Defaults to None.
        style (str, optional): Rich styling for the panel. Defaults to "bold blue".
    """
    console = get_console()
    panel = Panel(content, title=title, style=style)
    console.print(panel)


def print_table(headers: list[str], rows: list[list[Any]], title: str | None = None):
    """Print a formatted table using Rich library.

    Args:
        headers (list[str]): Column headers for the table.
        rows (list[list[Any]]): Data rows to display in the table.
        title (str | None, optional): Title of the table. Defaults to None.
    """
    console = get_console()
    table = Table(title=title)
    for header in headers:
        table.add_column(header)
    for row in rows:
        table.add_row(*[str(cell) for cell in row])
    console.print(table)


def print_syntax(code: str, language: str = "python", title: str | None = None):
    """Print code syntax highlighting using Rich library.

    Args:
        code (str): Source code to highlight.
        language (str, optional): Programming language for syntax highlighting. Defaults to "python".
        title (str | None, optional): Title for the syntax block. Defaults to None.
    """
    console = get_console()
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    if title:
        console.print(Panel(syntax, title=title))
    else:
        console.print(syntax)


class RichConsoleLogger(logging.Logger):
    def __init__(self, name: str):
        super().__init__(name)
        self.setLevel(logging.DEBUG)
        self.addHandler(RichHandler(rich_tracebacks=True))

    def success(self, message: str):
        """Print a success message in green color.

        Args:
            message (str): Success message to display.
        """
        self.info(f"[bold green]✔ {message}")

    def error(self, message: str):
        """Print an error message in red color.

        Args:
            message (str): Error message to display.
        """
        super().error(f"[bold red]✖ {message}")

    def warning(self, message: str):
        """Print a warning message in yellow color.

        Args:
            message (str): Warning message to display.
        """
        super().warning(f"[bold yellow]! {message}")

    def info(self, message: str):
        """Print an informational message in blue color.

        Args:
            message (str): Informational message to display.
        """
        super().info(f"[bold blue]ℹ {message}")


console_logger = RichConsoleLogger(__name__)


def get_console_logger() -> RichConsoleLogger:
    return console_logger