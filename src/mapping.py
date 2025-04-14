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
from pathlib import Path
from typing import Dict, Optional, Set, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default mappings for common packages where import name differs from package name
DEFAULT_MAPPINGS = {
    # Computer Vision
    "cv2": "opencv-python",
    "cv": "opencv-python",
    # Data Science
    "np": "numpy",
    "numpy": "numpy",  # Added explicit numpy mapping
    "pd": "pandas",
    "plt": "matplotlib",
    "sns": "seaborn",
    "sklearn": "scikit-learn",
    "skimage": "scikit-image",
    # Web Development
    "bs4": "beautifulsoup4",
    "bs": "beautifulsoup4",
    "django": "django",
    "flask": "flask",
    "requests": "requests",
    # Utilities
    "PIL": "pillow",
    "PIL.Image": "pillow",
    "yaml": "pyyaml",
    "lxml": "lxml",
    "jinja2": "jinja2",
    "jinja": "jinja2",
    # Testing
    "pytest": "pytest",
    "nose": "nose",
    "unittest": "unittest",  # Part of stdlib
    # Documentation
    "sphinx": "sphinx",
    "docutils": "docutils",
    # Development Tools
    "black": "black",
    "flake8": "flake8",
    "mypy": "mypy",
    "isort": "isort",
    "pylint": "pylint",
    # Database
    "sqlalchemy": "sqlalchemy",
    "sqlite3": "sqlite3",  # Part of stdlib
    "psycopg2": "psycopg2-binary",
    "pymongo": "pymongo",
    # Networking
    "socket": "socket",  # Part of stdlib
    "urllib": "urllib3",
    "httplib": "http.client",  # Part of stdlib
    # GUI
    "tkinter": "tk",  # Part of stdlib
    "PyQt5": "PyQt5",
    "PySide2": "PySide2",
    "wx": "wxPython",
    # Machine Learning
    "tensorflow": "tensorflow",
    "tf": "tensorflow",
    "torch": "torch",
    "transformers": "transformers",
    "keras": "keras",
    # Data Processing
    "nltk": "nltk",
    "spacy": "spacy",
    "gensim": "gensim",
    "scipy": "scipy",
    # Visualization
    "plotly": "plotly",
    "bokeh": "bokeh",
    "altair": "altair",
    # API Development
    "fastapi": "fastapi",
    "starlette": "starlette",
    "uvicorn": "uvicorn",
    # Async
    "asyncio": "asyncio",  # Part of stdlib
    "aiohttp": "aiohttp",
    "tornado": "tornado",
    # Serialization
    "json": "json",  # Part of stdlib
    "pickle": "pickle",  # Part of stdlib
    "msgpack": "msgpack",
    # Cryptography
    "crypto": "pycryptodome",
    "cryptography": "cryptography",
    # Audio/Video
    "pyaudio": "pyaudio",
    "moviepy": "moviepy",
    "pygame": "pygame",
    # Image Processing
    "imageio": "imageio",
    "pillow": "pillow",
    # CLI
    "click": "click",
    "typer": "typer",
    "argparse": "argparse",  # Part of stdlib
    # Configuration
    "configparser": "configparser",  # Part of stdlib
    "toml": "toml",
    "pyyaml": "pyyaml",
    # Date/Time
    "datetime": "datetime",  # Part of stdlib
    "time": "time",  # Part of stdlib
    "pytz": "pytz",
    # File System
    "os": "os",  # Part of stdlib
    "pathlib": "pathlib",  # Part of stdlib
    "shutil": "shutil",  # Part of stdlib
    # Regular Expressions
    "re": "re",  # Part of stdlib
    # Math
    "math": "math",  # Part of stdlib
    "random": "random",  # Part of stdlib
    "statistics": "statistics",  # Part of stdlib
    # Collections
    "collections": "collections",  # Part of stdlib
    "itertools": "itertools",  # Part of stdlib
    "functools": "functools",  # Part of stdlib
    # Concurrency
    "threading": "threading",  # Part of stdlib
    "multiprocessing": "multiprocessing",  # Part of stdlib
    # Debugging
    "pdb": "pdb",  # Part of stdlib
    "logging": "logging",  # Part of stdlib
    "traceback": "traceback",  # Part of stdlib
    # Type Hints
    "typing": "typing",  # Part of stdlib
    # Other
    "six": "six",
    "tqdm": "tqdm",
    "rich": "rich",
    "colorama": "colorama",
    "pygments": "pygments",
}

# Custom mappings that can be added by users
_custom_mappings: Dict[str, str] = {}


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


def get_package_name(import_name: str) -> str:
    """
    Get the PyPI package name for a given import name.

    Args:
        import_name: The name used in import statements.

    Returns:
        The name of the package on PyPI.

    Example:
        >>> get_package_name("cv2")
        'opencv-python'
        >>> get_package_name("numpy")
        'numpy'
    """
    # Check custom mappings first
    if import_name in _custom_mappings:
        return _custom_mappings[import_name]

    # Then check default mappings
    if import_name in DEFAULT_MAPPINGS:
        return DEFAULT_MAPPINGS[import_name]

    # If not found, assume the import name is the package name
    return import_name


def map_imports_to_packages(imports: Set[str]) -> Dict[str, str]:
    """
    Map a set of import names to their corresponding package names.

    Args:
        imports: A set of import names.

    Returns:
        A dictionary mapping import names to package names.

    Example:
        >>> imports = {"cv2", "numpy", "pandas"}
        >>> map_imports_to_packages(imports)
        {'cv2': 'opencv-python', 'numpy': 'numpy', 'pandas': 'pandas'}
    """
    return {imp: get_package_name(imp) for imp in imports}


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
    except Exception as e:
        logger.error(f"Error loading mappings from {file_path}: {e}")


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
    except Exception as e:
        logger.error(f"Error saving mappings to {file_path}: {e}")
        raise


def get_all_mappings() -> Dict[str, str]:
    """
    Get all mappings (default and custom).

    Returns:
        A dictionary containing all mappings.

    Example:
        >>> all_mappings = get_all_mappings()
        >>> print(f"Total mappings: {len(all_mappings)}")
    """
    # Start with default mappings
    all_mappings = DEFAULT_MAPPINGS.copy()
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
