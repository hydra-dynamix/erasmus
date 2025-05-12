from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from typing import Any, Optional
from rich.logging import RichHandler
import logging
import os


# Singleton Console instance
def get_console() -> Console:
    if not hasattr(get_console, "_console"):
        get_console._console = Console()
    
    # Get log level from environment variable
    log_level = os.getenv("ERASMUS_LOG_LEVEL", "INFO").upper()
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    # Validate log level
    if log_level not in valid_levels:
        get_console._console.print(f"Invalid log level: {log_level}. Using INFO.", style="bold yellow")
        log_level = "INFO"
    
    # Check if debug mode is enabled
    debug_mode = os.getenv("ERASMUS_DEBUG", "").lower() in ["true", "1", "yes"]
    
    if debug_mode:
        # In debug mode, log to file with specified level
        log_file = os.getenv("ERASMUS_LOG_FILE", "erasmus.log")
        # get_console._console.print(f"Debug mode enabled. Logging to {log_file} with level {log_level}", style="bold green")
    # else:
        # Only show this message if someone is explicitly trying to use a non-default log level
        # if os.getenv("ERASMUS_LOG_LEVEL") and not debug_mode:
            # get_console._console.print("Set ERASMUS_DEBUG=True to enable file logging.", style="bold yellow")
    
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
        
        # Get log level from environment variable
        log_level_str = os.getenv("ERASMUS_LOG_LEVEL", "INFO").upper() 
        if not log_level_str: 
            log_level_str = self._interactive_prompt_for_level()
            env_path = Path.cwd() / ".env"
            with env_path.open("a") as f:
                f.write(f"ERASMUS_LOG_LEVEL=ERROR\nERASMUS_DEBUG=False\n")
            load_dotenv()

        # Map string log levels to logging constants
        log_level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        
        # Set log level (default to INFO if invalid)
        log_level = log_level_map.get(log_level_str, logging.INFO)
        self.log_level_str = log_level_str
        self.log_level = log_level
        self.setLevel(log_level)
        
        # Configure handler with rich tracebacks
        handler = RichHandler(rich_tracebacks=True, level=log_level)
        self.addHandler(handler)
        
        # Add file handler if debug mode is enabled
        debug_mode = os.getenv("ERASMUS_DEBUG", "").lower() in ["true", "1", "yes"]
        if debug_mode:
            log_file = os.getenv("ERASMUS_LOG_FILE", "erasmus.log")
            try:
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(log_level)
                file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                file_handler.setFormatter(file_formatter)
                self.addHandler(file_handler)
            except Exception as e:
                self.error(f"Failed to set up file logging: {e}")

    def _interactive_prompt_for_level(self):
        """Prompt user for log level interactively."""
        while True:
            level = input("Enter log level (DEBUG, INFO, WARNING, ERROR, CRITICAL): ").upper().slice(0, 1)
            if level in ["D", "I", "W", "E", "C"]:
                if level == "D":
                    return "DEBUG"
                elif level == "I":
                    return "INFO"
                elif level == "W":
                    return "WARNING"
                elif level == "E":
                    return "ERROR"
                elif level == "C":
                    return "CRITICAL"
            else:
                print("Invalid log level. Valid choices: DEBUG, INFO, WARNING, ERROR, CRITICAL.\nPlease try again.")

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
        if self.log_level <= logging.ERROR:
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
        if self.log_level <= logging.WARNING:
            # Ensure message string is properly formatted if args are present
            if args:
                message = message % args
            super().warning(message, exc_info=exc_info, **kwargs)

    def info(self, message: str, *args, exc_info=None, **kwargs):
        """Log an informational message.

        Args:
            message (str): Informational message to display.
            exc_info (bool, optional): Whether to include exception info. Defaults to None.
        """
        if self.log_level <= logging.INFO:
            # Ensure message string is properly formatted if args are present
            if args:
                message = message % args
            super().info(message, exc_info=exc_info, **kwargs)

    def debug(self, message: str, *args, exc_info=None, **kwargs):
        """Log a debug message.

        Args:
            message (str): Debug message to display.
            exc_info (bool, optional): Whether to include exception info. Defaults to None.
        """
        if self.log_level <= logging.DEBUG:
            # Ensure message string is properly formatted if args are present
            if args:
                message = message % args
            super().debug(message, exc_info=exc_info, **kwargs)

    def critical(self, message: str, *args, exc_info=None, **kwargs):
        """Log a critical message.

        Args:
            message (str): Critical message to display.
            exc_info (bool, optional): Whether to include exception info. Defaults to None.
        """
        if self.log_level <= logging.CRITICAL:
            # Ensure message string is properly formatted if args are present
            if args:
                message = message % args
            super().critical(message, exc_info=exc_info, **kwargs)

# Singleton logger instance
_console_logger = None

def get_console_logger() -> RichConsoleLogger:
    """Get a singleton instance of RichConsoleLogger with log level from environment variables.
    
    Environment variables:
        ERASMUS_LOG_LEVEL: Set the log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        ERASMUS_DEBUG: Enable debug mode with file logging (true, 1, yes)
        ERASMUS_LOG_FILE: Specify the log file path (default: erasmus.log)
    
    Returns:
        RichConsoleLogger: Configured logger instance
    """
    global _console_logger
    if _console_logger is None:
        _console_logger = RichConsoleLogger(__name__)
    return _console_logger

# console_logger = get_console_logger()
console = get_console()

if __name__ == "__main__":
    os.environ["ERASMUS_LOG_LEVEL"] = "DEBUG"
    os.environ["ERASMUS_DEBUG"] = "true"
    logger = get_console_logger()
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    print(logger.log_level)