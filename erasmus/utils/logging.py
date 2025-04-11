"""Centralized logging configuration for Erasmus.

This module provides a consistent logging setup across the application with:
- Configurable log levels
- Contextual logging with thread and process info
- Log rotation
- Performance tracking
- Debug logging with rich formatting
"""

import logging
import logging.handlers
import sys
import time
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler

# Configure console for rich output
console = Console()

class LogContext:
    """Context manager for tracking operation timing and context."""

    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"Starting {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if exc_type:
            self.logger.error(
                f"{self.operation} failed after {duration:.2f}s",
                exc_info=(exc_type, exc_val, exc_tb),
            )
        else:
            self.logger.debug(f"Completed {self.operation} in {duration:.2f}s")

def get_logger(
    name: str,
    level: str | int = "INFO",
    log_file: Path | None = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Logger name, typically __name__
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file to log to
        max_bytes: Maximum size of each log file
        backup_count: Number of backup files to keep

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s [%(process)d:%(thread)d] %(name)s - %(levelname)s - %(message)s',
    )
    console_formatter = logging.Formatter(
        '%(message)s',  # Rich handler adds its own formatting
    )

    # Add console handler with rich formatting
    console_handler = RichHandler(
        rich_tracebacks=True,
        show_time=True,
        show_path=True,
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger

def log_execution(level: str = "DEBUG") -> Callable:
    """Decorator to log function execution with timing.

    Args:
        level: Log level for the timing message

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = logging.getLogger(func.__module__)
            log_level = getattr(logging, level.upper())

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.log(
                    log_level,
                    f"{func.__name__} completed in {duration:.2f}s",
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"{func.__name__} failed after {duration:.2f}s: {e!s}",
                    exc_info=True,
                )
                raise
        return wrapper
    return decorator

def init_logging(
    level: str | int = "INFO",
    log_dir: Path | None = None,
) -> None:
    """Initialize global logging configuration.

    Args:
        level: Default log level
        log_dir: Directory for log files
    """
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "erasmus.log"
    else:
        log_file = None

    # Configure root logger
    root_logger = get_logger(
        "erasmus",
        level=level,
        log_file=log_file,
    )

    # Log startup information
    root_logger.info("Initializing Erasmus logging system")
    root_logger.debug(f"Python version: {sys.version}")
    root_logger.debug(f"Log level: {logging.getLevelName(root_logger.level)}")
    if log_file:
        root_logger.debug(f"Log file: {log_file}")
