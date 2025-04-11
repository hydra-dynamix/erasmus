import json
import logging
from pathlib import Path

from ..cli.setup import validate_ide_env
from ..utils.file_ops import safe_read_file, safe_write_file


def start(self) -> None:
    """Start the cursor IDE integration."""
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
        logging.exception(f"Unexpected error handling rules file: {e}")
        raise
