"""IDE integration module."""

import json
import logging
from pathlib import Path

from erasmus.utils.paths import SetupPaths
from erasmus.utils.file_ops import safe_read_file, safe_write_file

logger = logging.getLogger(__name__)


def start() -> None:
    """Start the IDE integration."""
    setup_paths = SetupPaths.with_project_root(Path.cwd())
    rules_file = setup_paths.rules_file

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
