"""
IDE Integration Package
===================

This package provides integration with various IDEs, handling context
synchronization and IDE-specific requirements.
"""

from .cursor_integration import CursorContextManager

__all__ = ['CursorContextManager']
