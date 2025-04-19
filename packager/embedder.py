import base64
from pathlib import Path
from typing import Dict


def collect_erasmus_embedded_files(path_manager) -> Dict[str, str]:
    """
    Collect all files under .erasmus in the project root and return a dict of {relative_path: base64_content}.
    Uses the provided path manager for path resolution.
    """
    erasmus_dir = path_manager.get_erasmus_dir()
    project_root = path_manager.get_project_root()
    embedded = {}
    if not erasmus_dir.exists():
        return embedded

    def walk_dir(current_path: Path, rel_base: Path):
        for entry in current_path.iterdir():
            rel_path = rel_base / entry.name
            if entry.is_file():
                with open(entry, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                embedded[str(rel_path)] = encoded
            elif entry.is_dir():
                walk_dir(entry, rel_path)

    walk_dir(erasmus_dir, Path(".erasmus"))
    return embedded
