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
                and isinstance(node.body[0].value, (ast.Str, ast.Constant))
                and isinstance(node.body[0].value.value, str)  # make sure it's a string
            ):
                doc_node = node.body[0]
                self.docstring_ranges.append((doc_node.lineno, doc_node.end_lineno))

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


def extract_imports(source: str) -> ImportSet:
    """Extract imports from Python source code using AST."""
    imports = ImportSet()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.stdlib.add(name.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:  # Relative import
                for name in node.names:
                    imports.relative.add(name.name)
            else:
                for name in node.names:
                    imports.third_party.add(f"{node.module}.{name.name}")

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


def parse_file(file_path: Union[str, Path]) -> Tuple[ImportSet, str]:
    """Parse a Python file and extract imports and code body.

    Args:
        file_path: Path to Python file

    Returns:
        Tuple of (ImportSet, stripped_code)
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    return extract_code_body(source)


def parse_multiple_files(file_paths: List[Union[str, Path]]) -> Tuple[Set[str], List[str]]:
    """Parse multiple Python files and combine their imports and code bodies.

    Args:
        file_paths: List of paths to Python files

    Returns:
        Tuple of (combined_imports, stripped_files)
    """
    all_imports = ImportSet()
    stripped_files = []

    for file_path in file_paths:
        try:
            imports, stripped = parse_file(file_path)
            all_imports.update(imports)
            stripped_files.append(stripped)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            continue

    return all_imports.get_all_imports(), stripped_files


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
