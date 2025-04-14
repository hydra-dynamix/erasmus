"""
Builder module for the Python Script Packager.

This module is responsible for merging stripped code bodies and imports into a single
executable script. It handles the formatting of import statements, preservation of code
structure, and generation of the final script with appropriate headers.
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple, Union, Optional
import ast

from .parser import extract_imports, ImportSet, parse_imports
from .stdlib import StdlibDetector, is_stdlib_module
from rich.console import Console
from rich.logging import RichHandler

logger = logging.getLogger(__name__)

# Initialize stdlib detector
stdlib_detector = StdlibDetector()
stdlib_detector.initialize()


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
        preserve_comments: Whether to preserve comments in the output

    Returns:
        A tuple of (ImportSet of imports found, code body with imports removed)
    """
    imports = parse_imports(source)

    # Parse the source into an AST
    tree = ast.parse(source)

    # Find all import nodes
    import_nodes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_nodes.append(node)

    # Get the line numbers of all imports
    import_lines = set()
    for node in import_nodes:
        start = node.lineno - 1
        end = node.end_lineno if hasattr(node, "end_lineno") else start + 1
        import_lines.update(range(start, end))

    # Build the code body without imports
    lines = source.splitlines()
    body_lines = []
    for i, line in enumerate(lines):
        if i not in import_lines:
            if not preserve_comments and line.lstrip().startswith("#"):
                continue
            body_lines.append(line)

    return imports, "\n".join(body_lines)


def build_script(
    files: List[Union[str, Path]], base_path: Optional[Path] = None, preserve_comments: bool = True
) -> str:
    """Build a single script from multiple Python files.

    Args:
        files: List of file paths to include
        base_path: Base path for resolving relative imports
        preserve_comments: Whether to preserve comments in output

    Returns:
        Combined script with imports at top and code bodies below
    """
    if not files:
        raise ValueError("No files provided to build script")

    # Convert all paths to Path objects
    file_paths = [Path(f) for f in files]

    # Use first file's parent as base_path if not provided
    if base_path is None:
        base_path = file_paths[0].parent
    base_path = Path(base_path)

    # Analyze dependencies and order files
    ordered_files = order_files(file_paths)

    # Initialize combined imports
    all_imports = ImportSet()
    code_bodies = []

    # Process each file
    for file in ordered_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                source = f.read()

            # Extract imports and code body
            imports, body = extract_code_body(source, preserve_comments)

            # Add imports to combined set
            all_imports.update(imports)

            # Add non-empty code bodies
            if body.strip():
                code_bodies.append(f"\n# {file.name}\n{body}")

        except Exception as e:
            raise RuntimeError(f"Error processing file {file}: {str(e)}")

    # Format imports at top
    import_section = format_imports(all_imports)

    # Combine everything
    script = import_section
    if code_bodies:
        script += "\n\n" + "\n".join(code_bodies)

    return script


def generate_script(
    input_path: Union[str, Path],
    output_path: Optional[str] = None,
    preserve_comments: bool = True,
    group_imports: bool = True,
) -> Optional[str]:
    """Generate a single script from a Python file or directory.

    Args:
        input_path: Path to Python file or directory
        output_path: Optional path to save the script
        preserve_comments: Whether to preserve comments in output
        group_imports: Whether to group imports by type

    Returns:
        Generated script as string if no output_path, None otherwise

    Raises:
        FileNotFoundError: If input_path doesn't exist
        ValueError: If input_path is not a Python file/dir
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    # Collect Python files
    if input_path.is_file():
        if not input_path.suffix == ".py":
            raise ValueError(f"Input file must be a Python file: {input_path}")
        files = [input_path]
    else:
        files = []
        for root, _, filenames in os.walk(input_path):
            for filename in filenames:
                if filename.endswith(".py"):
                    files.append(Path(root) / filename)
        if not files:
            raise ValueError(f"No Python files found in directory: {input_path}")

    # Build the script
    script = build_script(
        files,
        base_path=input_path.parent if input_path.is_file() else input_path,
        preserve_comments=preserve_comments,
    )

    # Save or return the script
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(script)
        return None
    return script


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
