"""
CLI module for Erasmus.
"""

from erasmus.cli.main import app

def cli():
    """Entry point for the CLI."""
    app()

__all__ = ['app', 'cli'] 