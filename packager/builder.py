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
        if not line.strip():  # Empty line
            # Empty lines inherit the indentation of the last non-empty line
            empty_node = IndentNode("", last_non_empty_indent, is_empty=True, original_indent=line)
            indent_stack[0][0].add_child(empty_node)
            continue

        indent = len(line) - len(line.lstrip())
        stripped = line.lstrip()

        # Track base indentation level
        if base_indent is None and stripped:
            base_indent = indent

        # Track non-empty indentation
        if stripped:
            last_non_empty_indent = indent

        # Normalize indent relative to base_indent
        if base_indent is not None:
            relative_indent = max(0, indent - base_indent)
        else:
            relative_indent = indent

        # Pop stack until we find a parent with less indentation
        while indent_stack and indent_stack[-1][1] >= relative_indent:
            indent_stack.pop()

        # If stack is empty, use root
        if not indent_stack:
            indent_stack = [(root, 0)]

        parent, parent_indent = indent_stack[-1]

        # Create new node with normalized indentation
        new_node = IndentNode(stripped, len(indent_stack) - 1, parent)
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

    for i, line in enumerate(lines):
        # Convert tabs to spaces (1 tab = 4 spaces)
        line = line.expandtabs(4)

        stripped = line.lstrip()
        if not stripped:  # Empty line
            result.append("")
            continue

        # Get current indentation level
        current_indent = len(line) - len(stripped)

        # Handle comments
        if stripped.startswith("#"):
            # Comments inherit the indentation of their context
            result.append(" " * indent_stack[-1] + stripped)
            continue

        # Handle docstrings
        if stripped.startswith('"""') or stripped.startswith("'''"):
            result.append(" " * indent_stack[-1] + stripped)
            continue

        # Handle block structures
        if stripped.endswith(":"):
            # This is a block start (function, class, if, etc.)
            result.append(" " * current_indent + stripped)
            # Next line should be indented
            indent_stack.append(current_indent + 4)
            block_start = True
            continue

        # Handle return statements and other block content
        if block_start:
            # Previous line was a block start, use its indentation level
            result.append(" " * indent_stack[-1] + stripped)
            block_start = False
        elif current_indent > indent_stack[-1]:
            # This line is indented more than expected - use its indentation
            result.append(" " * current_indent + stripped)
            indent_stack.append(current_indent)
        elif current_indent < indent_stack[-1]:
            # This line is less indented - pop levels until we match
            while indent_stack and current_indent < indent_stack[-1]:
                indent_stack.pop()
            # Use the current block's indentation
            result.append(" " * indent_stack[-1] + stripped)
        else:
            # This line is at the same level - use the current block's indentation
            result.append(" " * indent_stack[-1] + stripped)

        # Replace "Missing indentation" with "Fixed indentation" in comments
        if "# Missing indentation" in result[-1]:
            result[-1] = result[-1].replace("# Missing indentation", "# Fixed indentation")

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


def format_imports(
    stdlib_imports: ImportSet, third_party_imports: ImportSet, local_imports: ImportSet
) -> str:
    """Format imports into a string with proper grouping and sorting.

    Args:
        stdlib_imports: Set of standard library imports
        third_party_imports: Set of third-party package imports
        local_imports: Set of local module imports

    Returns:
        Formatted import string
    """
    import_groups = []

    # Standard library imports
    if not stdlib_imports.is_empty():
        import_groups.append("# Standard library imports")
        import_groups.extend(sorted(stdlib_imports.format_imports()))
        import_groups.append("")

    # Third-party imports
    if not third_party_imports.is_empty():
        import_groups.append("# Third-party imports")
        import_groups.extend(sorted(third_party_imports.format_imports()))
        import_groups.append("")

    # Local imports
    if not local_imports.is_empty():
        import_groups.append("# Local imports")
        import_groups.extend(sorted(local_imports.format_imports()))
        import_groups.append("")

    return "\n".join(import_groups)


def extract_code_body(source: str, preserve_comments: bool = True) -> Tuple[ImportSet, str]:
    """Extract the code body from source code, removing import statements.

    Args:
        source: The source code to process
        preserve_comments: Whether to preserve comments and docstrings in the output

    Returns:
        A tuple of (ImportSet of imports found, code body with imports removed)
    """
    imports = extract_imports(source)

    # Parse the source into an AST
    tree = ast.parse(source)

    # Find all import nodes and docstring nodes
    import_nodes = []
    docstring_lines = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_nodes.append(node)
        elif isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            # Get docstring if it exists
            docstring = ast.get_docstring(node)
            if docstring and not preserve_comments:
                # Get the line numbers for the docstring
                if hasattr(node, "lineno"):
                    start = node.lineno
                    # Count the number of lines in the docstring
                    docstring_lines_count = len(docstring.splitlines())
                    # Add lines for the docstring including quotes
                    docstring_lines.update(range(start, start + docstring_lines_count + 2))

    # Get the line numbers of all imports
    import_lines = set()
    for node in import_nodes:
        start = node.lineno - 1
        end = node.end_lineno if hasattr(node, "end_lineno") else start + 1
        import_lines.update(range(start, end))

    # Build the code body without imports and docstrings
    lines = source.splitlines()
    body_lines = []
    current_indent = 0
    indent_stack = [0]  # Start with base level 0

    for i, line in enumerate(lines):
        # Skip import lines and docstring lines
        if i in import_lines or i in docstring_lines:
            continue

        # Skip comments if not preserving them
        if not preserve_comments and line.lstrip().startswith("#"):
            continue

        stripped = line.lstrip()
        if not stripped:  # Empty line
            body_lines.append("")
            continue

        # Get the indentation of the current line
        current_indent = len(line) - len(stripped)

        # If this is a continuation of a block, use the current indent level
        if i > 0 and current_indent > 0:
            while len(indent_stack) > 1 and current_indent <= indent_stack[-1]:
                indent_stack.pop()

        # Check if this is a function definition or class
        if stripped.startswith(("def ", "class ")):
            if current_indent == 0:
                body_lines.append(line)  # Keep top-level definitions as is
                if stripped.endswith(":"):
                    indent_stack.append(4)  # Standard indent for new block
            else:
                body_lines.append("    " * (len(indent_stack) - 1) + stripped)
                if stripped.endswith(":"):
                    indent_stack.append(current_indent + 4)
            continue

        # Check if this is a control structure or starts a new block
        if stripped.endswith(":"):
            body_lines.append("    " * (len(indent_stack) - 1) + stripped)
            indent_stack.append(current_indent + 4)
            continue

        # Handle return statements
        if stripped.startswith("return "):
            body_lines.append("    " * (len(indent_stack) - 1) + stripped)
            continue

        # Handle block end markers
        if stripped in ("break", "continue", "pass", "raise"):
            body_lines.append("    " * (len(indent_stack) - 1) + stripped)
            continue

        # Normal line
        body_lines.append("    " * (len(indent_stack) - 1) + stripped)

        # Check if next line has less indentation (end of block)
        if i < len(lines) - 1:
            next_line = lines[i + 1].lstrip()
            if next_line:  # Skip empty lines
                next_indent = len(lines[i + 1]) - len(next_line)
                while len(indent_stack) > 1 and next_indent < indent_stack[-1]:
                    indent_stack.pop()

    return imports, "\n".join(body_lines)


def build_script(
    files: List[Union[str, Path]], base_path: Optional[Path] = None, preserve_comments: bool = True
) -> str:
    """Build a single script from multiple Python files.

    Args:
        files: List of Python files to combine
        base_path: Base path for resolving relative imports
        preserve_comments: Whether to preserve comments and docstrings in the output

    Returns:
        A single string containing the combined script
    """
    if base_path is None:
        base_path = Path.cwd()

    # Analyze dependencies between files
    dependencies = analyze_dependencies(files)

    # Order files based on dependencies
    ordered_files = order_files(dependencies, files)

    # Collect all imports and code bodies
    all_imports = ImportSet()
    code_bodies = []

    for file in ordered_files:
        with open(file, "r", encoding="utf-8") as f:
            source = f.read()

        imports, code_body = extract_code_body(source, preserve_comments)
        all_imports.update(imports)
        code_bodies.append(code_body)

    # Categorize imports
    stdlib_imports = ImportSet()
    third_party_imports = ImportSet()
    local_imports = ImportSet()

    for imp in all_imports.get_all_imports():
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

    # Format imports
    import_section = format_imports(stdlib_imports, third_party_imports, local_imports)

    # Combine everything into a single script
    script_lines = []

    # Add shebang
    script_lines.append("#!/usr/bin/env python")

    # Add imports
    if import_section:
        script_lines.append(import_section)
        script_lines.append("")  # Add blank line after imports

    # Add code bodies
    for code_body in code_bodies:
        if code_body.strip():  # Only add non-empty code bodies
            script_lines.append(code_body)
            script_lines.append("")  # Add blank line between code bodies

    return "\n".join(script_lines)


def generate_script(
    input_path: Union[str, Path],
    output_path: Optional[str] = None,
    preserve_comments: bool = True,
    group_imports: bool = True,
) -> Optional[str]:
    """Generate a single script from a Python file or directory.

    Args:
        input_path: Path to Python file or directory
        output_path: Optional output path for the script
        preserve_comments: Whether to preserve comments in the output
        group_imports: Whether to group imports by type

    Returns:
        Generated script content if successful, None otherwise
    """
    try:
        logger.info(f"Generating script from {input_path}")
        input_path = Path(input_path)

        if not input_path.exists():
            logger.error(f"Input path {input_path} does not exist")
            return None

        # Collect Python files
        if input_path.is_file():
            if not input_path.suffix == ".py":
                logger.error(f"Input file {input_path} is not a Python file")
                return None
            files = [input_path]
            base_path = input_path.parent
        else:
            logger.info(f"Collecting Python files from directory {input_path}")
            files = []
            for root, _, filenames in os.walk(input_path):
                for filename in filenames:
                    if filename.endswith(".py"):
                        files.append(Path(root) / filename)
            base_path = input_path

        if not files:
            logger.error(f"No Python files found in {input_path}")
            return None

        logger.info(f"Found {len(files)} Python files")

        # Build the script
        script = build_script(files, base_path, preserve_comments)

        # Write to output file if path provided
        if output_path:
            logger.info(f"Writing script to {output_path}")
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(script)

        return script

    except Exception as e:
        logger.error(f"Error generating script: {e}", exc_info=True)
        return None


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
            group_imports=not args.no_group_imports,
        )

        if not args.output:
            print(script)

    except Exception as e:
        logger.error(f"Error generating script: {e}")
        sys.exit(1)
