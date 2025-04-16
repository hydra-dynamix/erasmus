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
from typing import Set, Tuple, List, Optional, Dict, Union
from .stdlib import is_stdlib_module

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImportSet:
    """Manages categorized imports (stdlib, third-party, local, relative)."""

    def __init__(self):
        self.stdlib = set()
        self.third_party = set()
        self.local = set()
        self.relative = set()

    def update(self, other: "ImportSet") -> None:
        """Merge another ImportSet into this one."""
        self.stdlib.update(other.stdlib)
        self.third_party.update(other.third_party)
        self.local.update(other.local)
        self.relative.update(other.relative)

    def get_all_imports(self) -> Set[str]:
        """Return all imports across all categories."""
        return self.stdlib | self.third_party | self.local | self.relative

    def __eq__(self, other) -> bool:
        """Compare ImportSet with another ImportSet or regular set."""
        if isinstance(other, ImportSet):
            return self.get_all_imports() == other.get_all_imports()
        elif isinstance(other, set):
            return self.get_all_imports() == other
        return NotImplemented

    def __iter__(self):
        """Make ImportSet iterable by yielding all imports."""
        yield from self.get_all_imports()

    def __repr__(self) -> str:
        """Return string representation of ImportSet."""
        return f"ImportSet({self.get_all_imports()})"

    def __str__(self) -> str:
        """Return string representation of ImportSet."""
        return str(self.get_all_imports())

    def get_all_base_modules(self) -> Set[str]:
        """Return all base module names (first part of each import path).

        For example:
        - 'os.path' -> 'os'
        - 'numpy.array' -> 'numpy'
        - 'mypackage.submodule.func' -> 'mypackage'
        """
        base_modules = set()
        for imp in self.get_all_imports():
            # Split on first dot to get base package
            base_modules.add(imp.split(".")[0])
        return base_modules

    def is_empty(self) -> bool:
        """Check if all import sets are empty."""
        return not (self.stdlib or self.third_party or self.local or self.relative)

    def format_imports(self) -> str:
        """Format imports into a string with proper grouping and sorting."""
        sections = []
        if self.stdlib:
            sections.append("# Standard library imports")
            sections.extend(f"import {imp}" for imp in sorted(self.stdlib))
        if self.third_party:
            sections.append("# Third-party imports")
            sections.extend(f"import {imp}" for imp in sorted(self.third_party))
        if self.local:
            sections.append("# Local imports")
            sections.extend(f"import {imp}" for imp in sorted(self.local))
        if self.relative:
            sections.append("# Relative imports")
            sections.extend(f"from . import {imp}" for imp in sorted(self.relative))
        return "\n".join(sections)

    def add_import(self, imp: str) -> None:
        """Add an import to the appropriate category.

        Args:
            imp: Import statement to add
        """
        # Handle relative imports
        if imp.startswith("."):
            # For relative imports like '.local.something', store both '.local' and '.local.something'
            parts = imp.split(".")
            # Count leading dots
            dots = ""
            while parts and not parts[0]:
                dots += "."
                parts.pop(0)
            # Add each part of the path
            for i in range(len(parts)):
                if parts[i]:  # Skip empty parts (from consecutive dots)
                    self.relative.add(dots + ".".join(parts[: i + 1]))
            return

        # Get base module name
        base_module = imp.split(".")[0]

        # Check if it's a standard library module
        if is_stdlib_module(base_module):
            self.stdlib.add(imp)
            self.stdlib.add(base_module)
            return

        # Check if it's a local module
        # This is a simplified check - in a real implementation,
        # you might want to check against your project's module structure
        if base_module in ["__main__", "__init__"]:
            self.local.add(imp)
            return

        # Assume it's a third-party module
        self.third_party.add(imp)


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


def sanitize_docstrings(source: str, replacement: str = '""') -> str:
    """Remove or replace docstrings in Python code.

    Args:
        source: The Python code as a string
        replacement: The string to replace docstrings with (defaults to empty string)

    Returns:
        The code with docstrings replaced
    """

    class DocstringRemover(ast.NodeVisitor):
        def __init__(self):
            self.docstring_ranges = []

        def visit_FunctionDef(self, node):
            self._check_docstring(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            self._check_docstring(node)
            self.generic_visit(node)

        def visit_ClassDef(self, node):
            self._check_docstring(node)
            self.generic_visit(node)

        def visit_Module(self, node):
            self._check_docstring(node)
            self.generic_visit(node)

        def _check_docstring(self, node):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)  # make sure it's a string
            ):
                doc_node = node.body[0]
                self.docstring_ranges.append((doc_node.lineno, doc_node.end_lineno))

    try:
        # Find docstring line ranges using AST
        tree = ast.parse(source)
        remover = DocstringRemover()
        remover.visit(tree)

        # Convert to a lookup set
        doc_lines = set()
        for start, end in remover.docstring_ranges:
            doc_lines.update(range(start, end + 1))

        # Tokenize and reconstruct the source
        output = []
        last_line = 0
        lines = source.splitlines(keepends=True)
        for i, line in enumerate(lines, start=1):
            if i in doc_lines:
                # Replace only the first line of the docstring block with the replacement
                if i == min(r for r in doc_lines if r >= i):
                    indent = line[: len(line) - len(line.lstrip())]
                    output.append(f"{indent}{replacement}\n")
            elif i > last_line:
                output.append(line)

        return "".join(output)
    except SyntaxError:
        # If we can't parse the source, return it unchanged
        return source


def extract_imports(source: str) -> ImportSet:
    """Extract all imports from a Python source file.

    Args:
        source (str): The source code to parse.

    Returns:
        ImportSet: A set of all imports found in the source.
    """
    imports = ImportSet()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.add_import(name.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:  # Relative import
                module = "." * node.level + (node.module or "")
                for name in node.names:
                    imports.add_import(f"{module}.{name.name}")
            else:  # Absolute import
                module = node.module or ""
                for name in node.names:
                    imports.add_import(f"{module}.{name.name}")

    return imports


def extract_code_body(source: str, preserve_comments: bool = True) -> Tuple[ImportSet, str]:
    """Extract imports and return code body with imports removed.

    Args:
        source: Python source code as string
        preserve_comments: Whether to preserve comments in output

    Returns:
        Tuple of (ImportSet, stripped_code)
    """
    imports = extract_imports(source)

    # First sanitize docstrings
    source = sanitize_docstrings(source)

    # Then remove imports
    tree = ast.parse(source)
    lines = source.splitlines()
    import_lines = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_lines.update(range(node.lineno, node.end_lineno + 1))

    stripped_lines = []
    for i, line in enumerate(lines, 1):
        if i not in import_lines:
            stripped_lines.append(line)

    return imports, "\n".join(stripped_lines)


def parse_file(file_path: str) -> Tuple[Set[str], str]:
    """Parse a Python file and extract imports.

    Args:
        file_path: Path to the Python file

    Returns:
        Tuple of (set of imports, stripped source code)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")

    imports = extract_imports(source)
    stripped = strip_imports(source)

    # Convert to base names only for the return value
    base_imports = set()
    for imp in imports.get_all_imports():
        if imp.startswith("."):
            continue  # Skip relative imports
        base_name = imp.split(".")[0]
        base_imports.add(base_name)

    return base_imports, stripped


def parse_multiple_files(file_paths: List[str]) -> Tuple[Set[str], Dict[str, str]]:
    """Parse multiple Python files and extract imports.

    Args:
        file_paths: List of paths to Python files

    Returns:
        Tuple of (set of all imports, dict of stripped source code)
    """
    all_imports = set()
    stripped_files = {}

    for file_path in file_paths:
        try:
            imports, stripped = parse_file(file_path)
            all_imports.update(imports)
            stripped_files[file_path] = stripped
        except (FileNotFoundError, SyntaxError) as e:
            logger.warning(f"Error processing {file_path}: {e}")

    return all_imports, stripped_files


def strip_imports(source: str, preserve_comments: bool = True) -> str:
    """Strip import statements from source code while preserving other content.

    Args:
        source: Python source code as string
        preserve_comments: Whether to preserve comments in output

    Returns:
        Source code with imports removed
    """
    tree = ast.parse(source)
    lines = source.splitlines()
    import_lines = set()

    # Find all import lines
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # Handle multi-line imports
            import_lines.update(range(node.lineno, node.end_lineno + 1))

    # Rebuild source without imports
    result = []
    for i, line in enumerate(lines, 1):
        if i not in import_lines:
            if preserve_comments or not line.strip().startswith("#"):
                result.append(line)

    return "\n".join(result)


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
