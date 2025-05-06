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


def print_panel(content: str, title: str | None = None, style: str = "bold blue", border_style: str | None = None):
    """Print a styled panel with optional title using Rich library.

    Args:
        content (str): The text content to display in the panel.
        title (str | None, optional): Title of the panel. Defaults to None.
        style (str, optional): Rich styling for the panel's content. Defaults to "bold blue".
        border_style (str | None, optional): Styling for the panel's border. Defaults to None.
    """
    console = get_console()
    
    # Ensure style is a non-None string
    style = style or "bold blue"
    
    # If border_style is None, use the same style as content
    border_style = border_style or style
    
    panel = Panel(content, title=title, style=style, border_style=border_style)
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

    def success(self, message: str, *args, **kwargs):
        """Log a success message (custom level).

        Args:
            message (str): Success message to display.
        """
        if args:
            message = message % args
        # Standard logging doesn't have a 'success' level by default.
        # We can use INFO level or define a custom level.
        # For simplicity, using INFO with a prefix or special formatting if RichHandler supports it.
        # Or, keep custom print if that's preferred over standard logging levels for this.
        # Let's assume we want it to go through the logging system, so use INFO.
        super().info(f"✔ {message}", **kwargs) # RichHandler will colorize based on level

    def error(self, message: str, *args, exc_info=None, **kwargs):
        """Log an error message.

        Args:
            message (str): Error message to display.
            exc_info (bool, optional): Whether to include exception info. Defaults to None.
        """
        # Ensure message string is properly formatted if args are present
        if args:
            message = message % args
        super().error(message, exc_info=exc_info, **kwargs)

    def warning(self, message: str, *args, exc_info=None, **kwargs):
        """Log a warning message.

        Args:
            message (str): Warning message to display.
            exc_info (bool, optional): Whether to include exception info. Defaults to None.
        """
        if args:
            message = message % args
        super().warning(message, exc_info=exc_info, **kwargs)

    def info(self, message: str, *args, exc_info=None, **kwargs):
        """Log an informational message.

        Args:
            message (str): Informational message to display.
            exc_info (bool, optional): Whether to include exception info. Defaults to None.
        """
        if args:
            message = message % args
        super().info(message, exc_info=exc_info, **kwargs)


console_logger = RichConsoleLogger(__name__)


def get_console_logger() -> RichConsoleLogger:
    return console_logger