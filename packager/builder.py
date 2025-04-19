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
from dataclasses import dataclass, field
import re
import importlib.util
import toml
import subprocess
import base64

from packager.parser import (
    extract_imports,
    ImportSet,
    is_valid_python_file,
    parse_imports,
    extract_code_body,
)
from packager.stdlib import StdlibDetector, is_stdlib_module
from rich.console import Console
from rich.logging import RichHandler
from packager.collector import collect_python_files
from packager.mapping import map_imports_to_packages
from packager.paths import get_packager_path_manager
from packager.file_order import get_ordered_files
from packager.inliner import inline_module, get_public_symbols
from packager.embedder import collect_erasmus_embedded_files

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
    children: list["IndentNode"]
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

    def get_all_lines(self) -> list[str]:
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


def build_indent_tree(lines: list[str]) -> IndentNode:
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


def normalize_indentation(code: Union[str, list[str]]) -> list[str]:
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


def analyze_dependencies(files: list[Path]) -> dict[Path, ImportSet]:
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
            imports, _ = parse_imports(content)
            dependencies[file] = imports
    return dependencies


def order_files(dependencies: dict[Path, ImportSet], files: list[Path]) -> list[Path]:
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


def collect_python_files(
    paths: list[Union[str, Path]], exclude_patterns: Optional[list[str]] = None
) -> list[Path]:
    """Collect valid Python files from the given paths.

    Args:
        paths: List of paths to files or directories
        exclude_patterns: List of glob patterns to exclude

    Returns:
        List of valid Python file paths
    """
    py_files = []
    for path in paths:
        path = Path(path)
        if not path.exists():
            logger.error(f"Path does not exist: {path}")
            continue

        if path.is_file():
            if is_valid_python_file(path):
                py_files.append(path)
            else:
                logger.warning(f"Skipping invalid or non-Python file: {path}")
        else:
            # Find all .py files, excluding __pycache__ and dot directories
            for file in path.rglob("*.py"):
                if "__pycache__" not in str(file) and not any(
                    p.startswith(".") for p in file.parts
                ):
                    if is_valid_python_file(file):
                        py_files.append(file)
                    else:
                        logger.warning(f"Skipping invalid Python file: {file}")

    # Apply exclude patterns
    if exclude_patterns:
        py_files = [
            file
            for file in py_files
            if not any(fnmatch.fnmatch(str(file), pattern) for pattern in exclude_patterns)
        ]

    # Exclude test files and __main__.py from py_files
    py_files = [
        f
        for f in py_files
        if not (
            f.name.startswith("test_")
            or f.name == "__main__.py"
            or "/tests/" in str(f)
            or "\\tests\\" in str(f)
        )
    ]

    return py_files


def collect_all_imports(
    files: list[Union[str, Path]], base_path: Path
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
        imports: ImportSet containing categorized imports
        group_imports: Whether to group imports by type

    Returns:
        Formatted import statements as a string
    """
    formatted = []
    seen_imports = set()  # Track imports to avoid duplicates

    def format_import(imp: str) -> str:
        """Format an import statement correctly."""
        # Skip relative imports
        if imp.startswith("."):
            return None

        # Skip if we've seen this import before
        base_name = imp.split(".")[0]
        if base_name in seen_imports:
            return None
        seen_imports.add(base_name)

        # Special case for timeit
        if imp == "logging.timeit":
            return None  # Do not emit import for logging.timeit

        if "." in imp:
            # For imports with dots, use 'from packager... import' syntax
            parts = imp.split(".")
            if len(parts) == 2:
                # Simple case: from a import b
                return f"from {parts[0]} import {parts[1]}"
            else:
                # Complex case: from a.b import c
                module = ".".join(parts[:-1])
                name = parts[-1]
                return f"from {module} import {name}"
        return f"import {imp}"

    if group_imports:
        # Standard library imports
        if imports.stdlib:
            formatted.append("# Standard library imports")
            for imp in sorted(imports.stdlib):
                stmt = format_import(imp)
                if stmt:
                    formatted.append(stmt)
            formatted.append("")

        # Third-party imports
        if imports.third_party:
            formatted.append("# Third-party imports")
            for imp in sorted(imports.third_party):
                stmt = format_import(imp)
                if stmt:
                    formatted.append(stmt)
            formatted.append("")

        # Local imports
        if imports.local:
            formatted.append("# Local imports")
            for imp in sorted(imports.local):
                stmt = format_import(imp)
                if stmt:
                    formatted.append(stmt)
            formatted.append("")
    else:
        # All imports in alphabetical order
        all_imports = sorted(imports.stdlib | imports.third_party | imports.local)
        for imp in all_imports:
            stmt = format_import(imp)
            if stmt:
                formatted.append(stmt)
        formatted.append("")

    return "\n".join(formatted).strip()


def extract_code_body(
    files: Union[str, Path, list[Union[str, Path]]],
    preserve_comments: bool = True,
    ignore_modules: set[str] = None,
) -> str:
    """Extract code body from Python files, removing imports.

    Args:
        files: Path to Python file, directory, or list of files
        preserve_comments: Whether to keep comments in output
        ignore_modules: Set of module names to ignore/remove imports for

    Returns:
        Combined code body with imports removed
    """
    if isinstance(files, (str, Path)):
        files = [files]

    # Track code sections to avoid duplicates
    seen_sections = set()
    code_bodies = []

    def hash_code(code: str) -> str:
        """Create a hash of the code, ignoring whitespace and comments."""
        # Remove comments and empty lines
        lines = []
        for line in code.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                # Normalize whitespace
                line = " ".join(line.split())
                lines.append(line)
        return hash("".join(lines))

    for file in files:
        file = Path(file)
        if not file.exists():
            raise FileNotFoundError(f"File does not exist: {file}")

        if file.is_file():
            content = file.read_text()
            # Try to parse the file
            try:
                tree = ast.parse(content)
                has_syntax_error = False
            except SyntaxError as e:
                has_syntax_error = True
                logger.warning(f"Syntax error in {file}: {e}")

            # Extract imports if possible
            try:
                import_set, _ = parse_imports(content)
                imports = import_set.get_all_imports()
            except SyntaxError:
                imports = set()

            # Remove imports from the content
            code_body = content
            # Remove ignored import statements
            if ignore_modules is not None:
                for mod in ignore_modules:
                    # Remove 'import mod', 'from packager. import mod', 'from packager.mod import ...', 'from mod import ...'
                    code_body = re.sub(
                        rf"^\s*import\s+{re.escape(mod)}(\s+as\s+\w+)?\s*$",
                        "",
                        code_body,
                        flags=re.MULTILINE,
                    )
                    code_body = re.sub(
                        rf"^\s*from\s+\.\s+import\s+{re.escape(mod)}.*$",
                        "",
                        code_body,
                        flags=re.MULTILINE,
                    )
                    code_body = re.sub(
                        rf"^\s*from\s+\.\s*{re.escape(mod)}\s+import.*$",
                        "",
                        code_body,
                        flags=re.MULTILINE,
                    )
                    code_body = re.sub(
                        rf"^\s*from\s+{re.escape(mod)}\s+import.*$",
                        "",
                        code_body,
                        flags=re.MULTILINE,
                    )
            # Remove any 'from packager.' or 'from erasmus.' or 'import .' lines
            code_body = re.sub(r"^\s*from\s+\.\s*.*$", "", code_body, flags=re.MULTILINE)
            code_body = re.sub(r"^\s*from\s+erasmus\..*$", "", code_body, flags=re.MULTILINE)
            code_body = re.sub(r"^\s*import\s+\..*$", "", code_body, flags=re.MULTILINE)
            for imp in imports:
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
                # Check for duplicate code sections
                code_section = "\n".join(cleaned_lines)
                code_hash = hash_code(code_section)

                if code_hash not in seen_sections:
                    seen_sections.add(code_hash)
                    header = "# Code from " + file.name
                    if has_syntax_error:
                        header += " (contains syntax errors)"
                    if preserve_comments:
                        code_bodies.append(header + "\n" + code_section)
                    else:
                        code_bodies.append(code_section)

    return "\n\n".join(code_bodies)


def build_script(
    imports: ImportSet,
    code_body: str,
) -> str:
    """Build a single script from imports and code body.

    Args:
        imports: ImportSet object containing categorized imports
        code_body: String containing the code body

    Returns:
        Generated script content
    """
    # Generate output script
    output = []

    # Add imports section
    output.append("# Standard library imports")
    for imp in sorted(imports.stdlib):
        output.append(f"import {imp}")

    output.append("\n# Third party imports")
    for imp in sorted(imports.third_party):
        output.append(f"import {imp}")

    # Add code body
    output.append("\n# Implementation")
    output.append(code_body)

    return "\n".join(output)


def resolve_local_imports(py_files, project_root):
    """Recursively resolve and order all local imports for inlining using topological sort."""
    from packager.parser import parse_imports
    import sys

    # Map module name to file path
    module_to_file = {}
    for file in py_files:
        rel_path = file.relative_to(project_root)
        module_name = ".".join(rel_path.with_suffix("").parts)
        module_to_file[module_name] = file

    # Build dependency graph
    dependencies = {mod: set() for mod in module_to_file}
    for mod, file in module_to_file.items():
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
        imports, _ = parse_imports(content)
        for imp in imports.local:
            if imp in module_to_file and imp != mod:
                dependencies[mod].add(imp)

    # Topological sort
    ordered = []
    temp_mark = set()
    perm_mark = set()

    def visit(mod):
        if mod in perm_mark:
            return
        if mod in temp_mark:
            raise RuntimeError(f"Circular dependency detected: {mod}")
        temp_mark.add(mod)
        for dep in dependencies[mod]:
            visit(dep)
        temp_mark.remove(mod)
        perm_mark.add(mod)
        ordered.append(module_to_file[mod])

    for mod in dependencies:
        if mod not in perm_mark:
            visit(mod)
    return ordered


def generate_script(
    paths: list[Union[str, Path]],
    output_path: Union[str, Path],
    preserve_comments: bool = True,
    exclude_patterns: Optional[list[str]] = None,
) -> Path:
    """Generate a script from Python files, inlining all local imports and placing them at the top."""
    # Initialize path manager
    path_manager = get_packager_path_manager()
    # Convert paths to Path objects
    py_files = collect_python_files(paths, exclude_patterns)
    # Exclude all __init__.py files
    py_files = [f for f in py_files if f.name != "__init__.py"]
    # Ensure all files are absolute paths
    py_files = [f.resolve() for f in py_files]
    if not py_files:
        raise ValueError("No Python files found in the specified paths")

    # Use path manager for project root
    project_root = path_manager.get_project_root()

    # Use file_order module for stacking
    ordered_files = get_ordered_files(py_files, path_manager)

    # Track which modules have been inlined
    inlined_modules = set()
    local_module_sections = []  # Store local modules to place at the top
    main_module_section = None
    for file in ordered_files:
        if file.name == "main.py":
            # Defer inlining main.py until the end
            code = inline_module(file, inlined_modules)
            main_module_section = f"\n# {file.name}\n{code}"
            continue
        rel_path = file.relative_to(project_root)
        module_name = ".".join(rel_path.with_suffix("").parts)
        if module_name in inlined_modules:
            continue
        inlined_modules.add(module_name)
        code = inline_module(file, inlined_modules)
        local_module_sections.append(f"\n# {file.name}\n{code}")
        # Inject public symbols into global namespace
        public_symbols = get_public_symbols(code)
        for symbol in public_symbols:
            local_module_sections.append(f"{symbol} = {symbol}")
    # Inline main.py last if present
    if main_module_section:
        local_module_sections.append(main_module_section)

    # Combine all code sections, with local modules at the top
    output_lines = []
    output_lines.extend(local_module_sections)
    output = "\n".join(output_lines)

    # Final pass: remove all 'from erasmus' and 'import erasmus' lines (anywhere in output)
    output = re.sub(r"^\s*from\s+erasmus[\w\.]*\s+import.*$", "", output, flags=re.MULTILINE)
    output = re.sub(r"^\s*import\s+erasmus[\w\.]*.*$", "", output, flags=re.MULTILINE)

    # Embed .erasmus files
    embedded_files = collect_erasmus_embedded_files(path_manager)
    embed_code = [
        "import os, base64",
        "def _extract_erasmus_embedded_files():",
        "    embedded = {}",
    ]
    for k, v in embedded_files.items():
        embed_code.append(f"    embedded[{repr(k)}] = {repr(v)}")
    embed_code += [
        '    if not os.path.exists(".erasmus"):',
        "        for rel_path, b64 in embedded.items():",
        "            out_path = os.path.join(os.getcwd(), rel_path)",
        "            os.makedirs(os.path.dirname(out_path), exist_ok=True)",
        '            with open(out_path, "wb") as f:',
        "                f.write(base64.b64decode(b64))",
        "    # else: do not overwrite",
        "",
        "_extract_erasmus_embedded_files()",
        "",
    ]
    # Prepend embed_code to output
    output = "\n".join(embed_code) + output

    # Append a single entry point at the end (call app() directly, no import)
    output += "\n\nif __name__ == '__main__':\n    app()\n"

    # Write output file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    # --- Add dependencies with uv ---
    pyproject_file = Path("pyproject.toml")
    if pyproject_file.exists():
        pyproject = toml.load(pyproject_file)
        dependencies = pyproject.get("project", {}).get("dependencies", [])
        for dep in dependencies:
            pkg = re.split(r"[>=<\[ ]", dep)[0].strip()
            print(f"Adding dependency with uv: {pkg}")
            subprocess.run(["uv", "add", "--script", str(output_path), pkg], check=True)
    else:
        print("pyproject.toml not found, skipping uv dependency injection.")

    logger.info(f"Generated script: {output_path}")
    return output_path


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
