import os
from pathlib import Path
import json
import logging
from ..utils.file_ops import safe_read_file, safe_write_file
from ..cli.setup import validate_ide_env


def start(self) -> None:
    """Start the Cursor IDE integration."""
    ide_env = validate_ide_env()
    rules_file = Path(f".{ide_env.lower()}rules")
    
    try:
        # Try to read existing rules
        content = safe_read_file(rules_file)
        json.loads(content)  # Validate JSON
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # Create empty rules file if it doesn't exist or is invalid
        logging.warning(f"Rules file error: {e}. Creating new rules file.")
        safe_write_file(rules_file, "{}")
    except Exception as e:
        logging.error(f"Unexpected error handling rules file: {e}")
        raise 