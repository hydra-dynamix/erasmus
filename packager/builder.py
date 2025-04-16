"""
Builder module for the Python Script Packager.

This module is responsible for merging stripped code bodies and imports into a single
executable script. It handles the formatting of import statements, preservation of code
structure, and generation of the final script with appropriate headers.
"""

import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple, Union, Optional, Any
import ast
import textwrap
from dataclasses import dataclass
import re

from .parser import extract_imports, ImportSet
from .stdlib import StdlibDetector, is_stdlib_module
from rich.console import Console
from rich.logging import RichHandler

logger = logging.getLogger(__name__)

# Initialize stdlib detector
stdlib_detector = StdlibDetector()
stdlib_detector.initialize()


@dataclass
class IndentNode:
    """Represents a node in the indentation tree.

    Each node can have:
    - content: The actual line content
    - children: Nested nodes representing indented blocks
    - parent: Reference to parent node
    - indent_level: The indentation level of this node
    - is_empty: Whether this node represents an empty line
    - original_indent: The original indentation of this node
    """

    content: str
    children: List["IndentNode"]
    parent: Optional["IndentNode"]
    indent_level: int
    is_empty: bool = False
    original_indent: str = ""

    def __init__(
        self,
        content: str,
        indent_level: int,
        parent: Optional["IndentNode"] = None,
        is_empty: bool = False,
        original_indent: str = "",
    ):
        self.content = content
        self.children = []
        self.parent = parent
        self.indent_level = indent_level
        self.is_empty = is_empty
        self.original_indent = original_indent

    def add_child(self, child: "IndentNode") -> None:
        """Add a child node to this node."""
        child.parent = self
        self.children.append(child)

    def get_all_lines(self) -> List[str]:
        """Get all lines in this node and its children, preserving relative indentation."""
        lines = []
        if self.is_empty:
            # For empty lines, preserve original indentation if any
            lines.append(self.original_indent)
        elif self.content:
            # For content lines, use normalized indentation
            indent = "    " * self.indent_level
            lines.append(indent + self.content)

        for child in self.children:
            lines.extend(child.get_all_lines())
        return lines


def build_indent_tree(lines: List[str]) -> IndentNode:
    """Build a tree structure from lines of code, where each level represents indentation.

    Args:
        lines: List of code lines to process

    Returns:
        Root node of the indentation tree
    """
    root = IndentNode("", 0)
    indent_stack = [(root, 0)]  # (node, indent_level)
    last_non_empty_indent = 0
    base_indent = None

    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # Handle empty lines
        if not stripped:
            # Empty lines inherit the indentation of the last non-empty line
            empty_node = IndentNode("", last_non_empty_indent, is_empty=True, original_indent=line)
            indent_stack[0][0].add_child(empty_node)
            continue

        # Track base indentation level
        if base_indent is None:
            base_indent = indent

        # Track non-empty indentation
        last_non_empty_indent = indent

        # Normalize indent relative to base_indent
        relative_indent = max(0, indent - base_indent)
        relative_indent = relative_indent // 4  # Convert to indentation levels

        # Pop stack until we find a parent with less indentation
        while indent_stack and indent_stack[-1][1] >= relative_indent:
            indent_stack.pop()

        # If stack is empty, use root
        if not indent_stack:
            indent_stack = [(root, 0)]

        parent, parent_indent = indent_stack[-1]

        # Create new node with normalized indentation
        new_node = IndentNode(stripped, relative_indent, parent)
        parent.add_child(new_node)

        # Update stack if this line might have children
        if stripped.endswith(":") or stripped.endswith("\\"):
            indent_stack.append((new_node, relative_indent))

    return root


def normalize_indentation(code: Union[str, List[str]]) -> List[str]:
    """Normalize indentation in Python code to use 4 spaces per level.

    Args:
        code: Python code as a string or list of lines

    Returns:
        List of lines with normalized indentation
    """
    # Convert string input to list of lines
    if isinstance(code, str):
        lines = code.splitlines()
    else:
        lines = code

    # Track indentation levels
    indent_stack = [0]  # Stack of indentation levels
    result = []
    block_start = False  # Track if previous line was a block start
    base_indent = None

    for i, line in enumerate(lines):
        # Convert tabs to spaces (1 tab = 4 spaces)
        line = line.expandtabs(4)

        stripped = line.lstrip()
        if not stripped:  # Empty line
            result.append("")
            continue

        # Get current indentation level
        current_indent = len(line) - len(stripped)

        # Track base indentation
        if base_indent is None:
            base_indent = current_indent

        # Normalize indentation relative to base
        relative_indent = max(0, current_indent - base_indent)
        indent_level = relative_indent // 4

        # Handle comments and docstrings
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            result.append(" " * (base_indent + (indent_level * 4)) + stripped)
            continue

        # Handle block structures
        if stripped.endswith(":"):
            # This is a block start (function, class, if, etc.)
            result.append(" " * (base_indent + (indent_level * 4)) + stripped)
            indent_stack.append(indent_level)
            block_start = True
            continue

        # Handle block content
        if block_start:
            # Previous line was a block start, use its indentation level
            result.append(" " * (base_indent + ((indent_stack[-1] + 1) * 4)) + stripped)
            block_start = False
        else:
            # Use current indentation level
            result.append(" " * (base_indent + (indent_level * 4)) + stripped)

        # Update indent stack
        while indent_stack and indent_level <= indent_stack[-1]:
            indent_stack.pop()
        indent_stack.append(indent_level)

    return result


def analyze_dependencies(files: List[Path]) -> Dict[Path, ImportSet]:
    """Analyze dependencies between files to determine stacking order.

    Args:
        files: List of Python files to analyze

    Returns:
        Dictionary mapping file paths to their import dependencies
    """
    dependencies = {}
    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            imports = extract_imports(content)
            dependencies[file] = imports
    return dependencies


def order_files(dependencies: Dict[Path, ImportSet], files: List[Path]) -> List[Path]:
    """Order files based on their dependencies.

    Args:
        dependencies: Dictionary of file dependencies
        files: List of files to order

    Returns:
        Ordered list of files with dependencies first
    """
    # Create a map of module names to files
    module_to_file = {}
    for file in files:
        module_name = file.stem
        if file.parent.name != "__pycache__":
            module_to_file[module_name] = file
            # Also map the parent directory name if it's a module
            if (file.parent / "__init__.py").exists():
                module_to_file[file.parent.name] = file.parent / "__init__.py"

    # Track processed files and their order
    processed = set()
    ordered = []
    visiting = set()  # Track files being visited to detect cycles

    def process_file(file: Path):
        if file in visiting:
            # Skip if we're already processing this file (cycle detected)
            return
        if file in processed:
            return

        visiting.add(file)

        # Process dependencies first
        file_imports = dependencies[file]
        for module in file_imports.get_all_base_modules():
            # Skip stdlib modules and self-imports
            if not stdlib_detector.is_stdlib_module(module) and module in module_to_file:
                dep_file = module_to_file[module]
                if dep_file != file and dep_file not in processed:
                    process_file(dep_file)

        visiting.remove(file)
        processed.add(file)
        ordered.append(file)

    # Process all files
    for file in files:
        if file not in processed:
            process_file(file)

    return ordered


def collect_all_imports(
    files: List[Union[str, Path]], base_path: Path
) -> Tuple[ImportSet, ImportSet, ImportSet]:
    """Collect and categorize all imports from the given files.

    Args:
        files: List of file paths to analyze
        base_path: Base path for resolving relative imports

    Returns:
        Tuple of (stdlib_imports, third_party_imports, local_imports)
    """
    stdlib_imports = ImportSet()
    third_party_imports = ImportSet()
    local_imports = ImportSet()

    for file in files:
        with open(file, "r") as f:
            source = f.read()

        imports = extract_imports(source)
        for imp in imports.get_all_imports():
            # Skip relative imports as they'll be converted to local
            if imp.startswith("."):
                continue

            # Split on first dot to get base package
            base_pkg = imp.split(".")[0]

            if is_stdlib_module(base_pkg):
                stdlib_imports.add_import(imp)
            else:
                # Check if it's a local module by looking for the file
                pkg_path = base_path / base_pkg.replace(".", "/")
                if pkg_path.exists() or (pkg_path.parent / f"{pkg_path.name}.py").exists():
                    local_imports.add_import(imp)
                else:
                    third_party_imports.add_import(imp)

    return stdlib_imports, third_party_imports, local_imports


def format_imports(imports: ImportSet, group_imports: bool = True) -> str:
    """Format imports into a string.

    Args:
        imports: The ImportSet containing all imports to format
        group_imports: Whether to group imports by type (stdlib, third-party, local)

    Returns:
        A string containing all formatted imports
    """
    if not imports:
        return ""

    formatted = []

    def format_import(imp: str) -> str:
        if "." in imp and not imp.startswith("."):
            base, *parts = imp.split(".")
            if len(parts) == 1:
                return f"from {base} import {parts[0]}"
        return f"import {imp}"

    def format_relative_import(imp: str) -> str:
        """Format a relative import into a 'from ... import ...' statement.

        Args:
            imp: The relative import to format (e.g., '.local_module' or '.local.something')

        Returns:
            Formatted import statement
        """
        if imp == ".":
            return "from . import *"

        # Count leading dots
        dots = ""
        while imp.startswith("."):
            dots += "."
            imp = imp[1:]

        # Handle empty module name (just dots)
        if not imp:
            return f"from {'.' * len(dots)} import *"

        # Handle module path
        if "." in imp:
            module, name = imp.rsplit(".", 1)
            return f"from {dots}{module} import {name}"
        return f"from {dots}{imp} import *"

    if group_imports:
        # Standard library imports
        if imports.stdlib:
            formatted.append("# Standard library imports")
            formatted.extend(format_import(imp) for imp in sorted(imports.stdlib))
            formatted.append("")

        # Third-party imports
        if imports.third_party:
            formatted.append("# Third-party imports")
            formatted.extend(format_import(imp) for imp in sorted(imports.third_party))
            formatted.append("")

        # Local imports
        if imports.local:
            formatted.append("# Local imports")
            formatted.extend(format_import(imp) for imp in sorted(imports.local))
            formatted.append("")

        # Relative imports
        if imports.relative:
            formatted.append("# Relative imports")
            formatted.extend(format_relative_import(imp) for imp in sorted(imports.relative))
            formatted.append("")
    else:
        # All imports in alphabetical order
        all_imports = sorted(
            imports.stdlib | imports.third_party | imports.local | imports.relative
        )
        formatted.extend(format_import(imp) for imp in all_imports)
        formatted.append("")

    return "\n".join(formatted).strip()


def extract_code_body(
    files: Union[str, Path, List[Union[str, Path]]],
    preserve_comments: bool = True,
) -> str:
    """Extract code body from Python files, removing imports.

    Args:
        files: Path to Python file, directory, or list of files
        preserve_comments: Whether to keep comments in output

    Returns:
        Combined code body with imports removed
    """
    if isinstance(files, (str, Path)):
        files = [files]

    code_bodies = []
    for file in files:
        file = Path(file)
        if not file.exists():
            raise FileNotFoundError(f"File does not exist: {file}")

        if file.is_file():
            content = file.read_text()
            # Parse the file to get the AST
            try:
                tree = ast.parse(content)
            except SyntaxError:
                # If there's a syntax error, try to parse line by line
                lines = content.splitlines()
                valid_lines = []
                for line in lines:
                    try:
                        ast.parse(line)
                        valid_lines.append(line)
                    except SyntaxError:
                        continue
                content = "\n".join(valid_lines)
                tree = ast.parse(content)

            # Remove imports and get code body
            imports = extract_imports(content)
            code_body = content
            for imp in imports.get_all_imports():
                # Replace import statements with empty lines to preserve line numbers
                code_body = re.sub(
                    rf"^.*import.*{re.escape(imp)}.*$",
                    "",
                    code_body,
                    flags=re.MULTILINE,
                )
                # Also handle 'from x import y' style imports
                base_module = imp.split(".")[0]
                code_body = re.sub(
                    rf"^from\s+{re.escape(base_module)}\s+import.*$",
                    "",
                    code_body,
                    flags=re.MULTILINE,
                )

            # Clean up empty lines and preserve comments if requested
            lines = code_body.splitlines()
            cleaned_lines = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if not preserve_comments and stripped.startswith("#"):
                    continue
                # Preserve indentation and string literals
                cleaned_lines.append(line.rstrip())

            if cleaned_lines:
                header = "# Code from " + file.name
                if not preserve_comments:
                    # Only add the header if we're preserving comments
                    code_bodies.append("\n".join(cleaned_lines))
                else:
                    code_bodies.append(header + "\n" + "\n".join(cleaned_lines))

    return "\n\n".join(code_bodies)


def build_script(
    files: List[Union[str, Path]],
    base_path: Optional[Path] = None,
    preserve_comments: bool = True,
    group_imports: bool = True,
) -> Tuple[ImportSet, str]:
    """Build a single script from multiple Python files.

    Args:
        files: List of Python files to combine
        base_path: Base path for resolving relative imports
        preserve_comments: Whether to preserve comments and docstrings
        group_imports: Whether to group imports by type

    Returns:
        Tuple of (ImportSet, script_content)
    """
    if base_path is None:
        base_path = Path.cwd()

    # Convert string paths to Path objects
    py_files = [Path(f) for f in files if Path(f).suffix == ".py"]

    # Extract imports and code
    imports = ImportSet()
    for file in py_files:
        try:
            content = file.read_text()
            imports.update(extract_imports(content))
        except Exception as e:
            logger.error(f"Error processing file {file}: {e}")
            continue

    # Generate script content
    script_lines = [
        "#!/usr/bin/env python3",
        "# -*- coding: utf-8 -*-",
        '"""',
        "Auto-generated script by Python Script Packager",
        '"""',
        "",
        format_imports(imports, group_imports),
        "",
        "# Generated code",
        extract_code_body(py_files, preserve_comments),
    ]

    return imports, "\n".join(script_lines)


def generate_script(
    input_path: Union[str, Path, List[Union[str, Path]]],
    output_file: Optional[Union[str, Path]] = None,
    preserve_comments: bool = True,
    group_imports: bool = True,
) -> str:
    """Generate a standalone script from Python files.

    Args:
        input_path: Path to Python file, directory, or list of files
        output_file: Optional path to write output
        preserve_comments: Whether to keep comments in output
        group_imports: Whether to group imports by type

    Returns:
        Generated script content
    """
    # Convert input_path to list of Path objects
    if isinstance(input_path, (str, Path)):
        input_path = [input_path]

    py_files = []
    for path in input_path:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Input path does not exist: {path}")

        if path.is_file():
            py_files.append(path)
        else:
            py_files.extend(path.glob("**/*.py"))

    if not py_files:
        raise ValueError(f"No Python files found in {input_path}")

    # Extract imports and code
    imports = ImportSet()
    for file in py_files:
        content = file.read_text()
        file_imports = extract_imports(content)
        imports.update(file_imports)

    code_body = extract_code_body(py_files, preserve_comments)

    # Generate script content
    script_lines = [
        "#!/usr/bin/env python3",
        "# -*- coding: utf-8 -*-",
        '"""',
        "Auto-generated script by Python Script Packager",
        '"""',
        "",
        format_imports(imports, group_imports),
        "",
        "# Generated code",
        code_body,
    ]

    script_content = "\n".join(script_lines)

    # Write to file if specified
    if output_file:
        output_file = Path(output_file)
        if output_file.is_dir():
            # If output_file is a directory, create a default output file
            output_file = output_file / "output.py"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(script_content)

    return script_content


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Build a single executable script from multiple Python files"
    )
    parser.add_argument("input", help="Path to a Python file or directory containing Python files")
    parser.add_argument("-o", "--output", help="Path to save the generated script")
    parser.add_argument(
        "--no-comments", action="store_true", help="Do not preserve comments and docstrings"
    )
    parser.add_argument(
        "--no-group-imports", action="store_true", help="Do not group imports by type"
    )

    args = parser.parse_args()

    try:
        script = generate_script(
            args.input,
            args.output,
            preserve_comments=not args.no_comments,
            group_imports=not args.no_group_imports,
        )

        if not args.output:
            print(script)

    except Exception as e:
        logger.error(f"Error generating script: {e}")
        sys.exit(1)
