"""Version management system for the watcher project."""
import json
import re
from datetime import datetime
from pathlib import Path


class VersionManager:
    """Manages version information and updates for the project."""

    VERSION_FILE = Path(__file__).parent.parent / "version.json"
    VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

    def __init__(self):
        self.version_data = self._load_version_data()

    def _load_version_data(self) -> dict:
        """Load version data from file or create default."""
        if self.VERSION_FILE.exists():
            with open(self.VERSION_FILE) as f:
                return json.load(f)
        return {
            "version": "0.0.1",
            "last_updated": datetime.now().isoformat(),
            "changes": [],
        }

    def _save_version_data(self):
        """Save version data to file."""
        with open(self.VERSION_FILE, 'w') as f:
            json.dump(self.version_data, f, indent=2)

    def get_current_version(self) -> str:
        """Get the current version string."""
        return self.version_data["version"]

    def parse_version(self, version: str) -> tuple[int, int, int] | None:
        """Parse version string into major, minor, patch tuple."""
        match = self.VERSION_PATTERN.match(version)
        if not match:
            return None
        return tuple(map(int, match.groups()))

    def increment_version(self, increment_type: str = "patch") -> str:
        """Increment version number based on type (major, minor, patch)."""
        current = self.parse_version(self.get_current_version())
        if not current:
            return self.get_current_version()

        major, minor, patch = current
        if increment_type == "major":
            major += 1
            minor = patch = 0
        elif increment_type == "minor":
            minor += 1
            patch = 0
        else:  # patch
            patch += 1

        new_version = f"{major}.{minor}.{patch}"
        self.version_data["version"] = new_version
        self.version_data["last_updated"] = datetime.now().isoformat()
        self._save_version_data()
        return new_version

    def add_change(self, change: str, change_type: str = "patch"):
        """Add a change entry and update version."""
        self.version_data["changes"].append({
            "description": change,
            "type": change_type,
            "timestamp": datetime.now().isoformat(),
        })
        self.increment_version(change_type)
        self._save_version_data()

    def get_changelog(self) -> list:
        """Get the list of changes."""
        return self.version_data["changes"]
