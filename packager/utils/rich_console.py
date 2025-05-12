"""
Rich Console Utility for Advanced Terminal Output and Logging.

Provides enhanced console logging and formatting capabilities using the rich library.
"""

import logging
import json
from typing import Any

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.theme import Theme


# Custom theme for consistent styling
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "green",
    "code": "dim",
})

class RichConsoleLogger(Console):
    """
    Advanced logging utility with rich formatting and multiple output methods.
    """
    def __init__(
        self, 
        name: str = "hydra_dynamix", 
        log_level: int = logging.INFO,
        log_file: str | None = None,
    ):
        """
        Initialize a rich console logger.
        
        Args:
            name: Logger name
            log_level: Logging level (default: logging.INFO)
            log_file: Optional file path to save logs
        """
        # Create console with custom theme
        self.record_console = Console(theme=custom_theme, record=True)
        
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[
                RichHandler(
                    console=self, 
                    rich_tracebacks=True,
                    tracebacks_show_locals=True
                )
            ]
        )
        
        super().__init__(theme=custom_theme, record=True)
        # Create logger
        self.logger = logging.getLogger(name)
        
        # Optional file logging
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(file_handler)

    def info(self, message: str, **kwargs):
        """Log an informational message."""
        self.logger.info(message, **kwargs)
        self.print(f"[info]ℹ️ {message}[/info]")

    def success(self, message: str, **kwargs):
        """Log a success message."""
        self.logger.info(message, **kwargs)
        self.print(f"[success]✅ {message}[/success]")

    def warning(self, message: str, **kwargs):
        """Log a warning message."""
        self.logger.warning(message, **kwargs)
        self.print(f"[warning]⚠️ {message}[/warning]")

    def error(self, message: str, **kwargs):
        """Log an error message."""
        self.logger.error(message, **kwargs)
        self.print(f"[error]❌ {message}[/error]")

    def print_code(
        self, 
        code: str, 
        language: str = "python", 
        title: str | None = None
    ):
        """
        Print code with syntax highlighting.
        
        Args:
            code: Code to display
            language: Programming language for syntax highlighting
            title: Optional title for the code panel
        """
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        
        if title:
            panel = Panel(syntax, title=title, border_style="dim")
            self.print(panel)
        else:
            self.print(syntax)

    def print_table(
        self, 
        data: list[dict[str, Any]], 
        title: str | None = None
    ):
        """
        Create and print a formatted table.
        
        Args:
            data: List of dictionaries representing table rows
            title: Optional table title
        """
        if not data:
            self.warning("No data to display in table")
            return

        table = Table(title=title, show_header=True, header_style="bold magenta")
        
        # Add columns based on first dictionary's keys
        for key in data[0].keys():
            table.add_column(str(key))
        
        # Add rows
        for row in data:
            table.add_row(*[str(value) for value in row.values()])
        
        self.print(table)
    
    @staticmethod
    def print_json(data: dict[str, dict | str]) -> None:
        target_string = json.dumps(data, indent=4)
        console.print(str(target_string))

def get_console_logger(
    name: str = "hydra_dynamix", 
    log_level: int = logging.INFO,
    log_file: str | None = None
) -> RichConsoleLogger:
    """
    Factory function to create a RichConsoleLogger instance.
    
    Args:
        name: Logger name
        log_level: Logging level
        log_file: Optional log file path
    
    Returns:
        Configured RichConsoleLogger instance
    """
    return RichConsoleLogger(name, log_level, log_file)

# Global console logger for easy access
console = get_console_logger()