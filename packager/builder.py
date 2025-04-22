"""
Builder module for the Python Script Packager.

This module is responsible for merging stripped code bodies and imports into a single
executable script. It handles the formatting of import statements, preservation of code
structure, and generation of the final script with appropriate headers.
"""

import ast
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import toml

from packager.collector import collect_python_files
from packager.embedder import collect_erasmus_embedded_files
from packager.file_order import get_ordered_files
from packager.inliner import get_public_symbols, inline_module
from packager.parser import (
    ImportSet,
    extract_imports,
    parse_imports,
)
from packager.paths import get_packager_path_manager
from packager.stdlib import StdlibDetector, is_stdlib_module

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
    parent: Literal["IndentNode"] | None
    indent_level: int
    is_empty: bool = False
    original_indent: str = ""

    def __init__(
        self,
        content: str,
        indent_level: int,
        parent: Literal["IndentNode"] | None = None,
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
        if stripped.endswith((":", "\\")):
            indent_stack.append((new_node, relative_indent))

    return root


def normalize_indentation(code: str | list[str]) -> list[str]:
    """Normalize indentation in Python code to use 4 spaces per level.

    Args:
        code: Python code as a string or list of lines

    Returns:
        List of lines with normalized indentation
    """
    # Convert string input to list of lines
    lines = code.splitlines() if isinstance(code, str) else code

    # Track indentation levels
    indent_stack = [0]  # Stack of indentation levels
    result = []
    block_start = False  # Track if previous line was a block start
    base_indent = None

    for _, line in enumerate(lines):
        # Convert tabs to spaces (1 tab = 4 spaces)
        current_line = line.expandtabs(4)

        stripped = current_line.lstrip()
        if not stripped:  # Empty line
            result.append("")
            continue

        # Get current indentation level
        current_indent = len(current_line) - len(stripped)

        # Track base indentation
        if base_indent is None:
            base_indent = current_indent

        # Normalize indentation relative to base
        relative_indent = max(0, current_indent - base_indent)
        indent_level = relative_indent // 4

        # Handle comments and docstrings
        if stripped.startswith(("#", '"""', "'''")):
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
    dependencies: dict[Path, ImportSet] = {}
    for file in files:
        content = file.read_text("utf-8")
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


def collect_all_imports(
    files: list[str | Path],
    base_path: Path,
) -> tuple[ImportSet, ImportSet, ImportSet]:
    """Collect and categorize all imports from the given files.

    Args:
        files: List of file paths to analyze
        base_path: Base path for resolving relative imports

    Returns:
        tuple of (stdlib_imports, third_party_imports, local_imports)
    """
    stdlib_imports = ImportSet()
    third_party_imports = ImportSet()
    local_imports = ImportSet()

    for file in files:
        source = file.read_text("utf-8")

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
    seen_imports = set()

    def format_single_import(imp: str) -> str | None:
        """Format a single import statement."""
        if imp.startswith(".") or imp.split(".")[0] in seen_imports:
            return None

        seen_imports.add(imp.split(".")[0])

        if imp == "logging.timeit":
            return None

        if "." not in imp:
            return f"import {imp}"

        parts = imp.split(".")
        module = ".".join(parts[:-1])
        name = parts[-1]
        return f"from {module} import {name}"

    def format_import_group(imports_list: set[str], header: str) -> list[str]:
        """Format a group of imports with a header."""
        if not imports_list:
            return []

        group = [header]
        for imp in sorted(imports_list):
            stmt = format_single_import(imp)
            if stmt:
                group.append(stmt)
        group.append("")
        return group

    if group_imports:
        formatted.extend(format_import_group(imports.stdlib, "# Standard library imports"))
        formatted.extend(format_import_group(imports.third_party, "# Third-party imports"))
        formatted.extend(format_import_group(imports.local, "# Local imports"))
    else:
        all_imports = sorted(imports.stdlib | imports.third_party | imports.local)
        for imp in all_imports:
            stmt = format_single_import(imp)
            if stmt:
                formatted.append(stmt)
        formatted.append("")

    return "\n".join(formatted).strip()


def extract_code_body(
    files: str | Path | list[str | Path],
    preserve_comments: bool = True,
    ignore_modules: set[str] | None = None,
) -> str:
    """Extract code body from Python files, removing imports.

    Args:
        files: Path to Python file, directory, or list of files
        preserve_comments: Whether to keep comments in output
        ignore_modules: Set of module names to ignore/remove imports for

    Returns:
        Combined code body with imports removed
    """
    if isinstance(files, str | Path):
        files = [files]

    code_extractor = CodeExtractor(preserve_comments, ignore_modules)
    return code_extractor.process_files(files)


class CodeExtractor:
    """Helper class to extract and process code from files."""

    def __init__(self, preserve_comments: bool, ignore_modules: set[str] | None):
        self.preserve_comments = preserve_comments
        self.ignore_modules = ignore_modules
        self.seen_sections = set()
        self.code_bodies = []

    def process_files(self, files: list[str | Path]) -> str:
        """Process multiple files and combine their code bodies."""
        for file in files:
            if file.is_file():
                self._process_file(file)
        return "\n\n".join(self.code_bodies)

    def _process_file(self, file: Path) -> None:
        """Process a single file."""
        content = file.read_text("utf-8")
        has_syntax_error = self._check_syntax(file, content)
        imports = self._parse_file_imports(content)
        self._process_code_content(content, imports, file.name, has_syntax_error)

    def _check_syntax(self, file: Path, content: str) -> bool:
        """Check file for syntax errors."""
        try:
            ast.parse(content)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file}: {e}")
            return True
        return False

    def _parse_file_imports(self, content: str) -> set[str]:
        """Parse imports from file content."""
        try:
            import_set, _ = parse_imports(content)
            return import_set.get_all_imports()
        except SyntaxError:
            return set()

    def _process_code_content(
        self,
        content: str,
        imports: set[str],
        filename: str,
        has_syntax_error: bool,
    ) -> None:
        """Process code content and add to code bodies."""
        code_body = self._remove_imports(content, imports)
        cleaned_lines = self._clean_code(code_body)
        if cleaned_lines:
            self._add_code_section(cleaned_lines, filename, has_syntax_error)

    def _add_code_section(
        self,
        cleaned_lines: list[str],
        filename: str,
        has_syntax_error: bool,
    ) -> None:
        """Add a code section if not already seen."""
        code_section = "\n".join(cleaned_lines)
        code_hash = self._hash_code(code_section)

        if code_hash not in self.seen_sections:
            self.seen_sections.add(code_hash)
            header = "# Code from " + filename
            if has_syntax_error:
                header += " (contains syntax errors)"
            if self.preserve_comments:
                self.code_bodies.append(header + "\n" + code_section)
            else:
                self.code_bodies.append(code_section)

    def _hash_code(self, code: str) -> str:
        """Create a hash of the code, ignoring whitespace and comments."""
        lines = []
        for line in code.split("\n"):
            current_line = line.strip()
            if current_line and not current_line.startswith("#"):
                current_line = " ".join(current_line.split())
                lines.append(current_line)
        return hash("".join(lines))

    def _remove_imports(self, content: str, imports: set[str]) -> str:
        """Remove import statements from code content."""
        code_body = content

        if self.ignore_modules:
            for mod in self.ignore_modules:
                patterns = [
                    rf"^\s*import\s+{re.escape(mod)}(\s+as\s+\w+)?\s*$",
                    rf"^\s*from\s+\.\s+import\s+{re.escape(mod)}.*$",
                    rf"^\s*from\s+\.\s*{re.escape(mod)}\s+import.*$",
                    rf"^\s*from\s+{re.escape(mod)}\s+import.*$",
                ]
                for pattern in patterns:
                    code_body = re.sub(pattern, "", code_body, flags=re.MULTILINE)

        # Remove package imports
        package_patterns = [
            r"^\s*from\s+\.\s*.*$",
            r"^\s*from\s+erasmus\..*$",
            r"^\s*import\s+\..*$",
        ]
        for pattern in package_patterns:
            code_body = re.sub(pattern, "", code_body, flags=re.MULTILINE)

        # Remove specific imports
        for imp in imports:
            patterns = [
                rf"^.*import.*{re.escape(imp)}.*$",
                rf"^from\s+{re.escape(imp.split('.')[0])}\s+import.*$",
            ]
            for pattern in patterns:
                code_body = re.sub(pattern, "", code_body, flags=re.MULTILINE)

        return code_body

    def _clean_code(self, content: str) -> list[str]:
        """Clean code content and return non-empty lines."""
        cleaned = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or (not self.preserve_comments and stripped.startswith("#")):
                continue
            cleaned.append(line.rstrip())
        return cleaned


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

    # Map module name to file path
    module_to_file = {}
    for file in py_files:
        rel_path = file.relative_to(project_root)
        module_name = ".".join(rel_path.with_suffix("").parts)
        module_to_file[module_name] = file

    # Build dependency graph
    dependencies = {mod: set() for mod in module_to_file}
    for mod, file in module_to_file.items():
        content = file.read_text("utf-8")
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


def _embed_erasmus_files(path_manager) -> str:
    """Generate code to embed .erasmus files into the output script."""
    embedded_files = collect_erasmus_embedded_files(path_manager)
    embed_code = [
        "import os, base64",
        "def _extract_erasmus_embedded_files():",
        "    embedded = {}",
    ]
    for key, value in embedded_files.items():
        embed_code.append(f"    embedded[{key!r}] = {value!r}")
    embed_code += [
        '    if not os.path.exists(".erasmus"):',
        "        for rel_path, base64_data in embedded.items():",
        "            out_path = os.path.join(os.getcwd(), rel_path)",
        "            os.makedirs(os.path.dirname(out_path), exist_ok=True)",
        '            with open(out_path, "wb") as file:',
        "                file.write(base64.b64decode(base64_data))",
        "    # else: do not overwrite",
        "",
        "_extract_erasmus_embedded_files()",
        "",
    ]
    return "\n".join(embed_code)


def _process_files(py_files: list[Path], project_root: Path) -> tuple[list[str], str | None]:
    """Process Python files and return code sections."""
    inlined_modules = set()
    local_module_sections = []
    main_module_section = None

    ordered_files = get_ordered_files(py_files, get_packager_path_manager())

    for file in ordered_files:
        if file.name == "main.py":
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

        # Inject public symbols
        public_symbols = get_public_symbols(code)
        for symbol in public_symbols:
            local_module_sections.append(f"{symbol} = {symbol}")

    return local_module_sections, main_module_section


def _inject_dependencies(output_path: Path):
    """Inject dependencies using uv if pyproject.toml exists."""
    pyproject_file = Path("pyproject.toml")
    if not pyproject_file.exists():
        print("pyproject.toml not found, skipping uv dependency injection.")
        return

    pyproject = toml.load(pyproject_file)
    dependencies = pyproject.get("project", {}).get("dependencies", [])
    for dep in dependencies:
        pkg = re.split(r"[>=<\[ ]", dep)[0].strip()
        print(f"Adding dependency with uv: {pkg}")
        subprocess.run(["uv", "add", "--script", str(output_path), pkg], check=True)


def generate_script(
    paths: list[str | Path],
    output_path: str | Path,
    exclude_patterns: list[str] | None = None,
) -> Path:
    "Generate a script from Python files, inlining all local imports and placing them at the top."
    path_manager = get_packager_path_manager()
    project_root = path_manager.get_project_root()

    # Collect and filter Python files
    py_files = collect_python_files(paths, exclude_patterns)
    py_files = [f for f in py_files if f.name != "__init__.py"]
    py_files = [f.resolve() for f in py_files]
    if not py_files:
        raise ValueError("No Python files found in the specified paths")

    # Process files
    local_module_sections, main_module_section = _process_files(py_files, project_root)
    if main_module_section:
        local_module_sections.append(main_module_section)

    # Combine code sections
    output = "\n".join(local_module_sections)

    # Remove erasmus imports
    output = re.sub(r"^\s*from\s+erasmus[\w\.]*\s+import.*$", "", output, flags=re.MULTILINE)
    output = re.sub(r"^\s*import\s+erasmus[\w\.]*.*$", "", output, flags=re.MULTILINE)

    # Add embedded files and entry point
    output = _embed_erasmus_files(path_manager) + output
    output += "\n\nif __name__ == '__main__':\n    app()\n"

    # Write output
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")

    # Add dependencies
    _inject_dependencies(output_path)

    logger.info(f"Generated script: {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Build a single executable script from multiple Python files",
    )
    parser.add_argument("input", help="Path to a Python file or directory containing Python files")
    parser.add_argument("-o", "--output", help="Path to save the generated script")
    parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Do not preserve comments and docstrings",
    )
    parser.add_argument(
        "--no-group-imports",
        action="store_true",
        help="Do not group imports by type",
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

    except Exception:
        logger.exception("Error generating script")
        sys.exit(1)
