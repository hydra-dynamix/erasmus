"""
Import to PyPI Package Mapping Module.

This module provides functionality to map Python import names to their corresponding
PyPI package names. It handles common aliases and special cases where the import
name differs from the package name.

Usage:
    from mapping import map_import_to_package, register_mapping, get_package_name

    # Map an import name to its package name
    package_name = get_package_name("cv2")
    # Returns: "opencv-python"

    # Register a custom mapping
    register_mapping("my_module", "my-package-name")
"""

import json
import logging
import os
import requests
from pathlib import Path
from typing import Dict, Optional, Set, Union
from dataclasses import dataclass
from packager.parser import ImportSet
from packaging.utils import canonicalize_name

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PackageMapping:
    """Mapping from import names to PyPI package names."""

    name: str
    package: str
    version: str | None = None


# Common mappings for packages where import name differs from package name
COMMON_MAPPINGS: dict[str, PackageMapping] = {
    "PIL": PackageMapping("PIL", "Pillow"),
    "sklearn": PackageMapping("sklearn", "scikit-learn"),
    "cv2": PackageMapping("cv2", "opencv-python"),
    "yaml": PackageMapping("yaml", "PyYAML"),
    "bs4": PackageMapping("bs4", "beautifulsoup4"),
    "lxml": PackageMapping("lxml", "lxml"),
    "pandas": PackageMapping("pandas", "pandas"),
    "numpy": PackageMapping("numpy", "numpy"),
    "matplotlib": PackageMapping("matplotlib", "matplotlib"),
    "seaborn": PackageMapping("seaborn", "seaborn"),
    "plotly": PackageMapping("plotly", "plotly"),
    "requests": PackageMapping("requests", "requests"),
    "aiohttp": PackageMapping("aiohttp", "aiohttp"),
    "fastapi": PackageMapping("fastapi", "fastapi"),
    "uvicorn": PackageMapping("uvicorn", "uvicorn"),
    "sqlalchemy": PackageMapping("sqlalchemy", "SQLAlchemy"),
    "pytest": PackageMapping("pytest", "pytest"),
    "black": PackageMapping("black", "black"),
    "flake8": PackageMapping("flake8", "flake8"),
    "mypy": PackageMapping("mypy", "mypy"),
    "isort": PackageMapping("isort", "isort"),
    "rich": PackageMapping("rich", "rich"),
    "typer": PackageMapping("typer", "typer"),
    "pydantic": PackageMapping("pydantic", "pydantic"),
}

# Custom mappings that can be added by users
_custom_mappings: dict[str, str] = {}

# Cache for PyPI package info
_pypi_cache: dict[str, str | None] = {}

# Cache for import to package mappings
_IMPORT_TO_PACKAGE: Dict[str, str] | None = None


def register_mapping(import_name: str, package_name: str) -> None:
    """
    Register a custom mapping from an import name to a package name.

    Args:
        import_name: The name used in import statements.
        package_name: The name of the package on PyPI.

    Example:
        >>> register_mapping("my_module", "my-package-name")
    """
    _custom_mappings[import_name] = package_name
    logger.info(f"Registered custom mapping: {import_name} -> {package_name}")


def query_pypi(module_name: str) -> str | None:
    """Query PyPI's JSON API to find the package name for a module.

    Args:
        module_name: The module name to look up

    Returns:
        The package name if found, None otherwise
    """
    if module_name in _pypi_cache:
        return _pypi_cache[module_name]

    try:
        # First try direct package name match
        response = requests.get(f"https://pypi.org/pypi/{module_name}/json")
        if response.status_code == 200:
            _pypi_cache[module_name] = module_name
            return module_name

        # Then try searching for packages that provide this module
        response = requests.get(f"https://pypi.org/search/?q={module_name}&format=json")
        if response.status_code == 200:
            results = response.json()
            for result in results.get("results", []):
                package_name = result["name"]
                # Check if this package provides the module
                pkg_response = requests.get(f"https://pypi.org/pypi/{package_name}/json")
                if pkg_response.status_code == 200:
                    pkg_data = pkg_response.json()
                    # Check if package provides this module
                    if any(module_name in pkg_data.get("info", {}).get("requires_dist", [])):
                        _pypi_cache[module_name] = package_name
                        return package_name

        _pypi_cache[module_name] = None
        return None
    except Exception as error:
        logger.warning(f"Error querying PyPI for {module_name}: {error}")
        return None


def _load_import_to_package() -> dict[str, str]:
    """Load and cache the import to package mappings.

    Returns:
        Dict mapping import names to PyPI package names
    """
    global _IMPORT_TO_PACKAGE

    if _IMPORT_TO_PACKAGE is not None:
        return _IMPORT_TO_PACKAGE

    # Start with common mappings
    _IMPORT_TO_PACKAGE = COMMON_MAPPINGS.copy()

    # Try to load additional mappings from a JSON file
    mappings_file = Path(__file__).parent / "import_mappings.json"
    if mappings_file.exists():
        try:
            with mappings_file.open() as f:
                additional_mappings = json.load(f)
                _IMPORT_TO_PACKAGE.update(additional_mappings)
        except Exception as error:
            logger.warning(f"Failed to load additional mappings from {mappings_file}: {error}")

    return _IMPORT_TO_PACKAGE


def get_package_name(import_name: str) -> str | None:
    """Get the PyPI package name for an import name.

    Args:
        import_name: The import name to look up

    Returns:
        The PyPI package name, or None if not found or if it's a stdlib module
    """
    # Get the top-level module name
    top_module = import_name.split(".")[0]

    # Check the mapping
    mappings = _load_import_to_package()
    if top_module in mappings:
        mapping = mappings[top_module]
        # If it's a PackageMapping, return the .package attribute
        if isinstance(mapping, PackageMapping):
            return mapping.package
        # If it's a string (legacy/custom), return as is
        return mapping

    # If not in mappings, try to canonicalize the name
    # This handles cases where the import name matches the package name
    try:
        return canonicalize_name(top_module)
    except Exception:
        return None


def map_imports_to_packages(imports: Set[str]) -> dict[str, str]:
    """Map a set of import names to their corresponding PyPI package names.

    Args:
        imports: Set of import names to map

    Returns:
        Dict mapping import names to PyPI package names
    """
    result = {}
    for imp in imports:
        pkg_name = get_package_name(imp)
        if pkg_name is not None:
            result[imp] = pkg_name
    return result


def load_mappings_from_file(file_path: Union[str, Path]) -> None:
    """
    Load custom mappings from a JSON file.

    Args:
        file_path: Path to the JSON file containing mappings.

    Example:
        >>> load_mappings_from_file("custom_mappings.json")
    """
    file_path = Path(file_path)
    if not file_path.exists():
        logger.warning(f"Mappings file not found: {file_path}")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            mappings = json.load(f)

        for import_name, package_name in mappings.items():
            register_mapping(import_name, package_name)

        logger.info(f"Loaded {len(mappings)} mappings from {file_path}")
    except Exception as error:
        logger.error(f"Error loading mappings from {file_path}: {error}")


def save_mappings_to_file(file_path: Union[str, Path]) -> None:
    """
    Save custom mappings to a JSON file.

    Args:
        file_path: Path to save the JSON file.

    Raises:
        Exception: If the directory doesn't exist or there's an error saving the file.

    Example:
        >>> save_mappings_to_file("custom_mappings.json")
    """
    file_path = Path(file_path)

    # Check if directory exists
    if not file_path.parent.exists():
        logger.error(f"Directory {file_path.parent} does not exist")
        raise Exception(f"Directory {file_path.parent} does not exist")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(_custom_mappings, f, indent=4)
        logger.info(f"Saved {len(_custom_mappings)} mappings to {file_path}")
    except Exception as error:
        logger.error(f"Error saving mappings to {file_path}: {error}")
        raise


def get_all_mappings() -> dict[str, str]:
    """
    Get all mappings (default and custom).

    Returns:
        A dictionary containing all mappings.

    Example:
        >>> all_mappings = get_all_mappings()
        >>> print(f"Total mappings: {len(all_mappings)}")
    """
    # Start with default mappings
    all_mappings = {imp: pkg for imp, pkg in COMMON_MAPPINGS.items() if pkg.package}
    # Add custom mappings (these will override defaults if there are conflicts)
    all_mappings.update(_custom_mappings)
    return all_mappings


def clear_custom_mappings() -> None:
    """
    Clear all custom mappings.

    Example:
        >>> clear_custom_mappings()
    """
    _custom_mappings.clear()
    logger.info("Cleared all custom mappings")


def get_required_packages(import_set: ImportSet) -> dict[str, str | None]:
    """Get required PyPI packages from an ImportSet.

    Args:
        import_set: ImportSet containing categorized imports

    Returns:
        Dictionary mapping package names to versions (if available)
    """
    packages = {}

    # Process third-party imports
    for module in import_set.third_party:
        package_name = get_package_name(module)
        if package_name:
            packages[package_name] = None  # Version will be determined by uv

    # Process local imports that might be third-party packages
    for module in import_set.local:
        package_name = get_package_name(module)
        if package_name and package_name not in packages:
            packages[package_name] = None

    return packages


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import to PyPI Package Mapping Tool")
    parser.add_argument("--import-name", help="Import name to look up")
    parser.add_argument("--package-name", help="Package name to register")
    parser.add_argument("--register", action="store_true", help="Register a mapping")
    parser.add_argument("--load", help="Load mappings from a JSON file")
    parser.add_argument("--save", help="Save mappings to a JSON file")
    parser.add_argument("--list", action="store_true", help="List all mappings")
    parser.add_argument("--clear", action="store_true", help="Clear all custom mappings")

    args = parser.parse_args()

    if args.import_name and not args.register:
        package_name = get_package_name(args.import_name)
        print(f"Import name: {args.import_name}")
        print(f"Package name: {package_name}")

    if args.register and args.import_name and args.package_name:
        register_mapping(args.import_name, args.package_name)
        print(f"Registered: {args.import_name} -> {args.package_name}")

    if args.load:
        load_mappings_from_file(args.load)

    if args.save:
        save_mappings_to_file(args.save)

    if args.list:
        all_mappings = get_all_mappings()
        print(f"Total mappings: {len(all_mappings)}")
        for imp, pkg in sorted(all_mappings.items()):
            print(f"{imp} -> {pkg}")

    if args.clear:
        clear_custom_mappings()
        print("Cleared all custom mappings")
