"""Parser module for extracting imports from Python files.

This module provides functionality to parse Python files and extract import information,
including handling of relative imports and error reporting.
"""

import ast
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


@dataclass
class ImportInfo:
    """Information about an import statement."""

    module_name: str
    imported_names: Set[str] = field(default_factory=set)
    is_from_import: bool = False
    level: int = 0  # For relative imports (should be avoided; use absolute imports)
    lineno: int = 0
    col_offset: int = 0


@dataclass
class FileImports:
    """Container for all imports found in a file and any parsing errors."""

    imports: list[ImportInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ImportSet:
    """Container for categorized imports from a file or project."""

    stdlib: Set[str] = field(default_factory=set)
    third_party: Set[str] = field(default_factory=set)
    local: Set[str] = field(default_factory=set)

    def get_all_imports(self) -> Set[str]:
        """Get all imports as a single set."""
        return self.stdlib | self.third_party | self.local

    def get_all_base_modules(self) -> Set[str]:
        """Get all base module names (first part of import path)."""
        all_imports = self.get_all_imports()
        return {imp.split(".")[0] for imp in all_imports}

    def update(self, other: "ImportSet") -> None:
        """Update this ImportSet with imports from another ImportSet.

        Args:
            other: Another ImportSet to merge with this one
        """
        self.stdlib.update(other.stdlib)
        self.third_party.update(other.third_party)
        self.local.update(other.local)


class ImportVisitor(ast.NodeVisitor):
    """AST visitor that collects import information from Python files."""

    def __init__(self) -> None:
        self.imports: list[ImportInfo] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Process Import nodes (e.g., 'import foo' or 'import foo as bar')."""
        for name in node.names:
            import_info = ImportInfo(
                module_name=name.name, lineno=node.lineno, col_offset=node.col_offset
            )
            if name.asname:
                import_info.imported_names.add(name.asname)
            self.imports.append(import_info)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Process ImportFrom nodes (e.g., 'from foo import bar')."""
        if node.module is None:
            # Handle "from packager. import foo" case (should be avoided; use absolute imports)
            module_name = ""
        else:
            module_name = node.module

        import_info = ImportInfo(
            module_name=module_name,
            is_from_import=True,
            level=node.level,
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

        for name in node.names:
            if name.name == "*":
                import_info.imported_names.add("*")
            else:
                import_name = name.asname if name.asname else name.name
                import_info.imported_names.add(import_name)

        self.imports.append(import_info)
        self.generic_visit(node)


def parse_file(file_path: Union[str, Path]) -> FileImports:
    """Parse a Python file and extract its imports.

    Args:
        file_path: Path to the Python file to parse

    Returns:
        FileImports object containing the list of imports and any errors encountered
    """
    file_path = Path(file_path)
    result = FileImports()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        error_msg = f"Failed to read file {file_path}: {str(e)}"
        logger.error(error_msg)
        result.errors.append(error_msg)
        return result

    try:
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError as e:
        error_msg = f"Syntax error in {file_path} at line {e.lineno}, column {e.offset}: {str(e)}"
        logger.error(error_msg)
        result.errors.append(error_msg)
        return result
    except Exception as e:
        error_msg = f"Failed to parse {file_path}: {str(e)}"
        logger.error(error_msg)
        result.errors.append(error_msg)
        return result

    visitor = ImportVisitor()
    visitor.visit(tree)
    result.imports = visitor.imports
    return result


def resolve_relative_import(
    base_path: Union[str, Path], import_info: ImportInfo, package_name: str | None = None
) -> str | None:
    """Resolve a relative import to its absolute form.

    Args:
        base_path: Path to the file containing the relative import
        import_info: ImportInfo object containing the import details
        package_name: Optional package name for resolving relative imports

    Returns:
        Resolved absolute import path or None if resolution fails
    """
    if import_info.level == 0:
        return import_info.module_name

    if not package_name:
        logger.warning("Package name not provided for relative import resolution")
        return None

    try:
        base_path = Path(base_path)
        parts = package_name.split(".")

        # Go up the directory tree based on the relative import level
        current_path = base_path.parent
        for _ in range(import_info.level - 1):
            current_path = current_path.parent
            if not current_path.exists():
                return None

        # Construct the absolute import path
        remaining_parts = parts[: -import_info.level] if import_info.level <= len(parts) else []
        if import_info.module_name:
            remaining_parts.append(import_info.module_name)

        return ".".join(remaining_parts) if remaining_parts else None

    except Exception as e:
        logger.error(f"Failed to resolve relative import: {str(e)}")
        return None


def normalize_imports(
    file_imports: FileImports, base_path: Union[str, Path], package_name: str | None = None
) -> Tuple[Set[str], list[str]]:
    """Convert collected imports into a normalized set of import strings.

    Args:
        file_imports: FileImports object containing the imports to normalize
        base_path: Path to the file containing the imports
        package_name: Optional package name for resolving relative imports

    Returns:
        Tuple of (set of normalized import strings, list of error messages)
    """
    normalized_imports: Set[str] = set()
    errors: list[str] = file_imports.errors.copy()

    for import_info in file_imports.imports:
        if import_info.level > 0:
            resolved = resolve_relative_import(base_path, import_info, package_name)
            if resolved is None:
                errors.append(
                    f"Failed to resolve relative import at line {import_info.lineno}: "
                    f"from {'.' * import_info.level}{import_info.module_name} "
                    f"import {', '.join(import_info.imported_names)}"
                )
                continue
            import_info.module_name = resolved

        if import_info.is_from_import:
            if "*" in import_info.imported_names:
                normalized_imports.add(import_info.module_name)
            else:
                for name in import_info.imported_names:
                    normalized_imports.add(f"{import_info.module_name}.{name}")
        else:
            normalized_imports.add(import_info.module_name)

    return normalized_imports, errors


def parse_imports(content: str) -> Tuple[ImportSet, list[str]]:
    """Parse imports from a string containing Python code.

    Args:
        content: String containing Python code

    Returns:
        Tuple of (ImportSet object containing categorized imports, list of error messages)
    """
    result = FileImports()

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        error_msg = f"Syntax error at line {e.lineno}, column {e.offset}: {str(e)}"
        logger.error(error_msg)
        result.errors.append(error_msg)
        return ImportSet(), result.errors
    except Exception as e:
        error_msg = f"Failed to parse content: {str(e)}"
        logger.error(error_msg)
        result.errors.append(error_msg)
        return ImportSet(), result.errors

    visitor = ImportVisitor()
    visitor.visit(tree)
    result.imports = visitor.imports

    # Since we don't have a file path, we can't resolve relative imports
    # So we'll just normalize the imports without resolving relative imports
    normalized_imports: Set[str] = set()
    for import_info in result.imports:
        if import_info.is_from_import:
            if "*" in import_info.imported_names:
                normalized_imports.add(import_info.module_name)
            else:
                for name in import_info.imported_names:
                    normalized_imports.add(f"{import_info.module_name}.{name}")
        else:
            normalized_imports.add(import_info.module_name)

    # Create an ImportSet object
    import_set = ImportSet()

    # Categorize imports
    for imp in normalized_imports:
        # This is a simplified categorization - in a real implementation,
        # you would use the StdlibDetector to properly categorize imports
        if imp.startswith(".") or imp.startswith(".."):
            import_set.local.add(imp)
        else:
            # Assume it's a third-party import for now
            # In a real implementation, you would check against stdlib
            import_set.third_party.add(imp)

    return import_set, result.errors


def extract_imports(
    file_path: Union[str, Path], package_name: str | None = None
) -> Tuple[ImportSet, list[str]]:
    """Extract and normalize imports from a Python file.

    This is the main entry point for the parser module. It combines parsing
    and normalization into a single convenient function.

    Args:
        file_path: Path to the Python file to parse
        package_name: Optional package name for resolving relative imports

    Returns:
        Tuple of (ImportSet object containing categorized imports, list of error messages)
    """
    file_imports = parse_file(file_path)
    normalized_imports, errors = normalize_imports(file_imports, file_path, package_name)

    # Create an ImportSet object
    import_set = ImportSet()

    # Categorize imports
    for imp in normalized_imports:
        # This is a simplified categorization - in a real implementation,
        # you would use the StdlibDetector to properly categorize imports
        if imp.startswith(".") or imp.startswith(".."):
            import_set.local.add(imp)
        else:
            # Assume it's a third-party import for now
            # In a real implementation, you would check against stdlib
            import_set.third_party.add(imp)

    return import_set, errors


def is_valid_python_file(file_path: Union[str, Path]) -> bool:
    """Check if a file is a valid Python file.

    Args:
        file_path: Path to the file to check

    Returns:
        True if the file is a valid Python file, False otherwise
    """
    file_path = Path(file_path)

    # Check if file exists and has .py extension
    if not file_path.exists() or file_path.suffix != ".py":
        return False

    # Check if file is not empty
    try:
        if file_path.stat().st_size == 0:
            return False
    except Exception:
        return False

    # Try to parse the file to check for syntax errors
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        ast.parse(content, filename=str(file_path))
        return True
    except Exception:
        return False


def extract_code_body(
    files: Union[str, Path, list[Union[str, Path]]],
    preserve_comments: bool = True,
    ignore_modules: set[str] = None,
) -> str:
    """Extract code body from Python files, removing imports.

    Args:
        files: Path to Python file, directory, list of files, or string content
        preserve_comments: Whether to keep comments in output
        ignore_modules: Set of module names to ignore/remove imports for

    Returns:
        Combined code body with imports removed
    """
    # If files is a string and not a path, treat it as content
    if isinstance(files, str) and not Path(files).exists():
        content = files
        # Try to parse the content
        try:
            tree = ast.parse(content)
            has_syntax_error = False
        except SyntaxError as e:
            has_syntax_error = True
            logger.warning(f"Syntax error in content: {e}")

        # Extract imports if possible
        try:
            # Use parse_imports for string content
            import_set, _ = parse_imports(content)
            imports = import_set.get_all_imports()
        except SyntaxError:
            imports = set()

        # Remove imports from the content
        code_body = content
        if ignore_modules is not None:
            for mod in ignore_modules:
                # Remove 'import erasmus' or 'import erasmus.something'
                code_body = re.sub(
                    rf"^\s*import\s+{re.escape(mod)}(\.[\w\.]+)?(\s+as\s+\w+)?\s*$",
                    "",
                    code_body,
                    flags=re.MULTILINE,
                )
                # Remove 'from erasmus import ...' or 'from erasmus.something import ...'
                code_body = re.sub(
                    rf"^\s*from\s+{re.escape(mod)}(\.[\w\.]+)?\s+import.*$",
                    "",
                    code_body,
                    flags=re.MULTILINE,
                )
                # Remove 'from . import erasmus' or 'from .erasmus import ...'
                code_body = re.sub(
                    rf"^\s*from\s+\.\s*{re.escape(mod)}(\.[\w\.]+)?\s+import.*$",
                    "",
                    code_body,
                    flags=re.MULTILINE,
                )
        for imp in imports:
            code_body = re.sub(
                rf"^.*import.*{re.escape(imp)}.*$",
                "",
                code_body,
                flags=re.MULTILINE,
            )
            base_module = imp.split(".")[0]
            code_body = re.sub(
                rf"^from\s+{re.escape(base_module)}\s+import.*$",
                "",
                code_body,
                flags=re.MULTILINE,
            )

        lines = code_body.splitlines()
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if not preserve_comments and stripped.startswith("#"):
                continue
            cleaned_lines.append(line.rstrip())

        if cleaned_lines:
            return "\n".join(cleaned_lines)
        return ""

    if isinstance(files, (str, Path)):
        files = [files]

    seen_sections = set()
    code_bodies = []

    def hash_code(code: str) -> str:
        lines = []
        for line in code.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                line = " ".join(line.split())
                lines.append(line)
        return hash("".join(lines))

    for file in files:
        file = Path(file)
        if not file.exists():
            raise FileNotFoundError(f"File does not exist: {file}")

        if file.is_file():
            content = file.read_text()
            try:
                tree = ast.parse(content)
                has_syntax_error = False
            except SyntaxError as e:
                has_syntax_error = True
                logger.warning(f"Syntax error in {file}: {e}")

            try:
                import_set, _ = parse_imports(content)
                imports = import_set.get_all_imports()
            except SyntaxError:
                imports = set()

            code_body = content
            if ignore_modules is not None:
                for mod in ignore_modules:
                    # Remove 'import erasmus' or 'import erasmus.something'
                    code_body = re.sub(
                        rf"^\s*import\s+{re.escape(mod)}(\.[\w\.]+)?(\s+as\s+\w+)?\s*$",
                        "",
                        code_body,
                        flags=re.MULTILINE,
                    )
                    # Remove 'from erasmus import ...' or 'from erasmus.something import ...'
                    code_body = re.sub(
                        rf"^\s*from\s+{re.escape(mod)}(\.[\w\.]+)?\s+import.*$",
                        "",
                        code_body,
                        flags=re.MULTILINE,
                    )
                    # Remove 'from . import erasmus' or 'from .erasmus import ...'
                    code_body = re.sub(
                        rf"^\s*from\s+\.\s*{re.escape(mod)}(\.[\w\.]+)?\s+import.*$",
                        "",
                        code_body,
                        flags=re.MULTILINE,
                    )
            for imp in imports:
                code_body = re.sub(
                    rf"^.*import.*{re.escape(imp)}.*$",
                    "",
                    code_body,
                    flags=re.MULTILINE,
                )
                base_module = imp.split(".")[0]
                code_body = re.sub(
                    rf"^from\s+{re.escape(base_module)}\s+import.*$",
                    "",
                    code_body,
                    flags=re.MULTILINE,
                )

            lines = code_body.splitlines()
            cleaned_lines = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if not preserve_comments and stripped.startswith("#"):
                    continue
                cleaned_lines.append(line.rstrip())

            if cleaned_lines:
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
