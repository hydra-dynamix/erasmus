from asyncio.log import logger
from pathlib import Path
from typing import Optional


class PackagerPathManager:
    """
    Centralized path manager for the packager. Handles project root, build directory, and source paths.
    """

    def __init__(self, project_root: Optional[Path] = None, build_dir: Optional[Path] = None):
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.build_dir = Path(build_dir or self.project_root / "build").resolve()
        self.erasmus_dir = self.project_root / ".erasmus"
        self.src_dir = self.project_root / "erasmus"

    def get_project_root(self) -> Path:
        return self.project_root

    def get_build_dir(self) -> Path:
        return self.build_dir

    def get_erasmus_dir(self) -> Path:
        return self.erasmus_dir

    def get_src_dir(self) -> Path:
        return self.src_dir

    def rel_to_project(self, path: Path) -> Path:
        """Get a path relative to the project root."""
        return path.resolve().relative_to(self.project_root)

    def abs_from_project(self, rel_path: str | Path) -> Path:
        """Get an absolute path from a project-root-relative path."""
        return (self.project_root / rel_path).resolve()

    def ensure_build_dir(self) -> None:
        self.build_dir.mkdir(parents=True, exist_ok=True)

    def build_order(self) -> list[Path]:
        order = [
            self.src_dir / "utils" / "logging.py",
            self.src_dir / "utils" / "paths.py",
            self.src_dir / "utils" / "sanatizer.py",
            self.src_dir / "utils" / "xml_parser.py",
            self.src_dir / "utils" / "rich_console.py",
            self.src_dir / "environment.py",
            self.src_dir / "context.py",
            self.src_dir / "protocol.py",
            self.src_dir / "file_monitor.py",
            self.src_dir / "cli" / "context_commands.py",
            self.src_dir / "cli" / "protocol_commands.py",
            self.src_dir / "cli" / "setup_commands.py",
            self.src_dir / "cli" / "main.py",
        ]
        build_order_list = []
        for file in order:
            if file.exists():
                build_order_list.append(file)
            else:
                logger.warning(f"File {file} does not exist, skipping")
        return build_order_list

    def get_release_path(self, library_name: str, version: str) -> Path:
        path = self.project_root / "releases" / library_name / version
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_dry_run_path(self, library_name: str) -> Path:
        path = self.project_root / "releases" / library_name / "0.0.0"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_unique_output_path(self, library_name: str, version: str) -> Path:
        base_dir = self.get_release_path(library_name, version)
        base_file = base_dir / f"{library_name}_v{version}.py"
        output_path = base_file
        suffix = 1
        while output_path.exists():
            output_path = base_dir / f"{library_name}_v{version}_{suffix}.py"
            suffix += 1
        return output_path


# Singleton accessor
_packager_path_manager = None


def get_packager_path_manager(
    project_root: Optional[Path] = None, build_dir: Optional[Path] = None
) -> PackagerPathManager:
    global _packager_path_manager
    if _packager_path_manager is None:
        _packager_path_manager = PackagerPathManager(project_root, build_dir)
    return _packager_path_manager
