"""
Erasmus - Development Context Management System
"""

from erasmus.cli import cli
from erasmus.protocol import ProtocolManager, ProtocolError
from erasmus.utils import get_path_manager

__version__ = "0.1.0"
__all__ = [
    "cli",
    "ContextManager",
    "ContextError",
    "ProtocolManager",
    "ProtocolError",
    "get_path_manager",
]
