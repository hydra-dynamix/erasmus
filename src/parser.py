"""
Import Parser Module.

This module provides functionality to parse Python files and extract imports
using the AST module. It can also strip import statements from the source code
while preserving the rest of the functionality.

Usage:
    from parser import extract_imports, strip_imports, parse_file

    # Extract imports from a file
    imports = parse_file('path/to/file.py')

    # Extract imports from source code
    imports = extract_imports(source_code)

    # Strip imports from source code
    stripped_code = strip_imports(source_code)
"""

import ast
import logging
import textwrap
from pathlib import Path
from typing import Set, Tuple, List, Optional, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImportSet:
    """Manages a set of imports and their modules."""

    def __init__(self):
        """Initialize empty import sets."""
        self.imports: Dict[str, Set[str]] = {}  # library -> set of imported items
        self.from_imports: Dict[str, Set[str]] = {}  # module -> set of imported names
        self.import_as: Dict[str, str] = {}  # alias -> original name

    def add_import(self, name: str, alias: Optional[str] = None):
        """Add a direct import."""
        base_module = name.split(".")[0]
        if base_module not in self.imports:
            self.imports[base_module] = set()
        self.imports[base_module].add(name)
        if alias:
            self.import_as[alias] = name

    def add_from_import(self, module: str, names: List[str]):
        """Add a from-style import."""
        if module not in self.from_imports:
            self.from_imports[module] = set()
        self.from_imports[module].update(names)

    def get_all_base_modules(self) -> Set[str]:
        """Get all base module names."""
        modules = set(self.imports.keys())
        modules.update(mod.split(".")[0] for mod in self.from_imports)
        return modules

    def format_imports(self, group_by_type: bool = True) -> List[str]:
        """Format imports as strings."""
        result = []

        # Handle direct imports
        for module, names in sorted(self.imports.items()):
            for name in sorted(names):
                alias = next(
                    (alias for alias, orig in self.import_as.items() if orig == name), None
                )
                if alias:
                    result.append(f"import {name} as {alias}")
                else:
                    result.append(f"import {name}")

        # Handle from-imports
        for module, names in sorted(self.from_imports.items()):
            if "*" in names:
                result.append(f"from {module} import *")
            else:
                # Group names by their aliases
                named_imports = []
                for name in sorted(names):
                    alias = next(
                        (alias for alias, orig in self.import_as.items() if orig == name), None
                    )
                    if alias:
                        named_imports.append(f"{name} as {alias}")
                    else:
                        named_imports.append(name)
                result.append(f"from {module} import {', '.join(named_imports)}")

        return result


def normalize_import_name(name: str) -> str:
    """
    Normalize an import name by removing version suffixes and converting to lowercase.

    Args:
        name: The import name to normalize.

    Returns:
        The normalized import name.

    Example:
        >>> normalize_import_name("numpy>=1.20.0")
        'numpy'
    """
    # Remove version constraints
    name = name.split(">=")[0].split("<=")[0].split("==")[0].split("!=")[0]
    # Remove any remaining whitespace
    name = name.strip()
    return name


def extract_imports(source: str) -> ImportSet:
    """
    Extract import statements from source code.

    Args:
        source: Python source code as a string

    Returns:
        ImportSet containing all imports
    """
    imports = ImportSet()
    try:
        # Parse the source code
        tree = ast.parse(source)

        # Extract imports from the AST
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.add_import(name.name, name.asname)
            elif isinstance(node, ast.ImportFrom):
                module = "." * (node.level or 0) + (node.module or "")
                names = []
                for name in node.names:
                    if name.name == "*":
                        names = ["*"]
                        break
                    names.append(name.name)
                    if name.asname:
                        imports.import_as[name.asname] = name.name
                imports.add_from_import(module, names)

    except SyntaxError as e:
        logger.warning(f"Syntax error in source code: {e}")
        # Try to extract imports even with syntax errors
        for line in source.splitlines():
            line = line.strip()
            if line.startswith(("import ", "from ")):
                # Remove any trailing comments
                line = line.split("#")[0].strip()
                if line.startswith("import "):
                    parts = line[7:].split(" as ")
                    if len(parts) > 1:
                        imports.add_import(parts[0].strip(), parts[1].strip())
                    else:
                        imports.add_import(parts[0].strip())
                else:  # from import
                    parts = line[5:].split(" import ")
                    if len(parts) == 2:
                        module = parts[0].strip()
                        names = [n.strip() for n in parts[1].split(",")]
                        imports.add_from_import(module, names)
    except Exception as e:
        logger.error(f"Error extracting imports: {e}")

    return imports


def strip_imports(source: str, preserve_comments: bool = True) -> str:
    """
    Remove import statements from Python source code while preserving the rest.

    Args:
        source: Python source code as a string.
        preserve_comments: Whether to preserve comments and docstrings.

    Returns:
        The source code with import statements removed.

    Example:
        >>> source = '''
        ... import os
        ... def main():
        ...     print(os.getcwd())
        ... '''
        >>> strip_imports(source)
        'def main():\n    print(os.getcwd())\n'
    """
    try:
        # Dedent the source code to handle indentation
        source = textwrap.dedent(source)
        tree = ast.parse(source, mode="exec")

        # If we want to preserve comments, we need to work with the original source
        if preserve_comments:
            # Split source into lines
            lines = source.splitlines()
            # Track which lines contain imports
            import_lines = set()

            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    # Get the line numbers (1-based in AST)
                    start = node.lineno - 1  # Convert to 0-based
                    end = node.end_lineno if hasattr(node, "end_lineno") else start + 1
                    for i in range(start, end):
                        import_lines.add(i)

            # Keep lines that aren't imports
            result_lines = [line for i, line in enumerate(lines) if i not in import_lines]
            return "\n".join(result_lines)
        else:
            # Find all import nodes
            import_nodes = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_nodes.append(node)

            # Create a new tree without import nodes
            new_body = []
            for node in tree.body:
                if node not in import_nodes:
                    new_body.append(node)

            # Create a new module with the filtered body
            new_tree = ast.Module(body=new_body, type_ignores=[])

            # Convert back to source
            return ast.unparse(new_tree)
    except SyntaxError as e:
        logger.warning(f"Could not strip imports due to syntax error: {e}")
        return source
    except Exception as e:
        logger.error(f"Error stripping imports: {e}")
        return source


def parse_file(file_path: str | Path, preserve_comments: bool = True) -> Tuple[Set[str], str]:
    """
    Parse a Python file to extract imports and strip them from the source.

    Args:
        file_path: Path to the Python file.
        preserve_comments: Whether to preserve comments and docstrings when stripping imports.

    Returns:
        A tuple containing:
        - A set of module names that are imported
        - The source code with import statements removed

    Example:
        >>> imports, stripped = parse_file("path/to/file.py")
        >>> print(f"Imports: {imports}")
        >>> print(f"Stripped code:\n{stripped}")
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        source = file_path.read_text(encoding="utf-8")
        imports = extract_imports(source)
        stripped = strip_imports(source, preserve_comments)
        return imports, stripped
    except Exception as e:
        logger.error(f"Error parsing file {file_path}: {e}")
        raise


def parse_multiple_files(file_paths: List[str | Path]) -> Tuple[Set[str], List[str]]:
    """
    Parse multiple Python files to extract imports and stripped code.

    Args:
        file_paths: List of paths to Python files.

    Returns:
        A tuple containing:
        - A set of all unique module names that are imported
        - A list of stripped source code for each file

    Example:
        >>> files = ["file1.py", "file2.py"]
        >>> imports, stripped_files = parse_multiple_files(files)
        >>> print(f"Total unique imports: {len(imports)}")
    """
    all_imports = set()
    stripped_files = []

    for file_path in file_paths:
        try:
            imports, stripped = parse_file(file_path)
            if imports:  # Only include files that were successfully parsed
                all_imports.update(imports)
                stripped_files.append(stripped)
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            continue

    return all_imports, stripped_files


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Parse Python files for imports")
    parser.add_argument("files", nargs="+", help="Python files to parse")
    parser.add_argument(
        "--preserve-comments",
        action="store_true",
        help="Preserve comments and docstrings when stripping imports",
    )
    args = parser.parse_args()

    try:
        imports, stripped_files = parse_multiple_files(args.files)
        print(f"\nImports found in {len(args.files)} files:")
        for imp in sorted(imports):
            print(f"  {imp}")

        print("\nStripped code for each file:")
        for file_path, stripped in zip(args.files, stripped_files):
            print(f"\n{file_path}:")
            print("-" * 40)
            print(stripped)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
