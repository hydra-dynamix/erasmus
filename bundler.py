import logging
from pathlib import Path
from typing import Any
import os
import ast
from collections import defaultdict, deque

IMPORTS = {
    "import": [],
    "from": {},  # nested dict structure
}


def add_module_to_tree(tree: dict, module_path: str, imported_name: str) -> None:
    """
    Add an imported name to a nested dictionary tree for a module path.
    Direct imports are stored under the '__all__' key as a set.
    Example: ('some.module', 'thing') -> tree['some']['module']['__all__'] = {'thing'}
    """
    if not imported_name:
        return
    parts = module_path.split(".")
    current = tree
    for part in parts:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    if "__all__" not in current:
        current["__all__"] = set()
    current["__all__"].add(imported_name)


def construct_imports(code_string: str, package_name: str | None = None) -> None:
    """
    Adds imports to the IMPORTS dict and builds a nested dict for 'from ... import ...' statements.
    Handles the 'logging.timeit' edge case by replacing it with 'import timeit'.
    If more than 5 such edge cases are needed, migrate to the ast library.
    """
    if code_string.startswith("from erasmus"):
        return
    if code_string.strip() in ("from logging import timeit", "import logging.timeit"):
        IMPORTS["import"].append("import timeit")
        return
    if code_string.startswith("import"):
        IMPORTS["import"].append(code_string)
    elif code_string.startswith("from"):
        parts = code_string.split()
        if "import" in parts:
            import_idx = parts.index("import")
            module_path = " ".join(parts[1:import_idx]).replace(" ", "")
            if module_path.startswith("."):
                return  # Only skip relative imports
            imported_names = " ".join(parts[import_idx + 1 :]).split(",")
            for name in [n.strip() for n in imported_names if n.strip()]:
                add_module_to_tree(IMPORTS["from"], module_path, name)


def reconstruct_imports(tree: dict, prefix: str = "") -> list[str]:
    """
    Reconstruct 'from ... import ...' statements from the nested dictionary tree.
    Handles both set and dict values at any level, and outputs __all__ as top-level imports.
    """
    imports = []
    for key, value in tree.items():
        if isinstance(value, dict):
            # Output import for __all__ if present
            if "__all__" in value and value["__all__"]:
                import_list = ", ".join(sorted(value["__all__"]))
                mod = f"{prefix}{key}" if prefix else key
                imports.append(f"from {mod} import {import_list}")
            # Recurse into submodules
            for subkey, subvalue in value.items():
                if subkey != "__all__":
                    imports.extend(reconstruct_imports({subkey: subvalue}, f"{prefix}{key}."))
        elif isinstance(value, set):
            if value:
                mod = f"{prefix}{key}" if prefix else key
                import_list = ", ".join(sorted(value))
                imports.append(f"from {mod} import {import_list}")
    return imports


def construct_indent_tree(code_string: str) -> dict[str, Any]:
    """
    Construct an indent tree from a string.
    Each line is categorized by its indentation level (number of leading spaces divided by 4).
    Returns a dict with keys for each indent level and a 'sequence' list for reconstruction order.
    """
    indent_tree: dict[str, list[str] | list[int]] = {"sequence": [], "0": []}
    lines = code_string.splitlines()
    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            # Preserve blank lines at top level
            indent_tree["0"].append("")
            indent_tree["sequence"].append(0)
            continue
        indent_level = (len(line) - len(stripped)) // 4
        key = str(indent_level)
        if key not in indent_tree:
            indent_tree[key] = []
        indent_tree[key].append(stripped)
        indent_tree["sequence"].append(indent_level)
    return indent_tree


def reconstruct_from_indent_tree(indent_tree: dict[str, Any]) -> str:
    """
    Reconstruct code from an indent tree.
    """
    sequence: list[int] = indent_tree["sequence"]
    lines: list[str] = []
    counters: dict[str, int] = {k: 0 for k in indent_tree if k != "sequence"}
    for idx in sequence:
        key = str(idx)
        block = indent_tree[key]
        line_idx = counters[key]
        counters[key] += 1
        line = block[line_idx]
        lines.append(("    " * idx) + line if line else "")
    return "\n".join(lines)


def read_file_lines(input_path: Path) -> list[str]:
    """Read the file and return a list of lines."""
    return input_path.read_text().splitlines()


def parse_lines(lines: list[str]) -> tuple[list[str], list[str]]:
    """
    Process lines, returning import lines and code body lines.
    Handles multi-line imports and skips comments/docstrings.
    Stops processing at 'if __name__ == "__main__"'.
    Only skips lines that are empty, start with #, ', or ` (not ").
    """
    import_lines = []
    code_body_lines = []
    i = 0
    in_triple_quote = False
    triple_quote_type = None
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Stop processing at main block
        if 'if __name__ == "__main__"' in stripped:
            break
        # Handle triple-quoted comments
        if not in_triple_quote and (stripped.startswith(('"""', "'''"))):
            in_triple_quote = True
            triple_quote_type = stripped[:3]
            if stripped.count(triple_quote_type) == 2:
                in_triple_quote = False
                triple_quote_type = None
            i += 1
            continue
        if in_triple_quote:
            if triple_quote_type and triple_quote_type in stripped:
                in_triple_quote = False
                triple_quote_type = None
            i += 1
            continue
        # Drop single-line comments and single-quoted string lines
        if not stripped or stripped.startswith(("#", "'", "`")):
            i += 1
            continue
        # Handle multi-line imports
        if (
            (stripped.startswith(("import", "from")))
            and "(" in stripped
            and not stripped.rstrip().endswith(")")
        ):
            import_lines_accum = [stripped]
            i += 1
            while i < len(lines):
                nextline = lines[i].strip()
                import_lines_accum.append(nextline)
                if ")" in nextline:
                    break
                i += 1
            full_import = " ".join(import_lines_accum).replace("( ", "(").replace(" )", ")")
            import_lines.append(full_import)
            i += 1
            continue
        # Handle normal imports
        if stripped.startswith(("import", "from")):
            import_lines.append(stripped)
            i += 1
            continue
        # Otherwise, treat as code
        code_body_lines.append(line)
        i += 1
    return import_lines, code_body_lines


def process_imports(import_lines: list[str], package_name: str | None = None) -> None:
    """Process all import lines and update the global IMPORTS structure."""
    global IMPORTS  # noqa: PLW0603
    IMPORTS = {"import": [], "from": {}}
    for imp in import_lines:
        construct_imports(imp, package_name)


def bundle_code(code_body_lines: list[str]) -> str:
    """Build the indent tree and reconstruct the code body."""
    code_body = "\n".join(code_body_lines)
    indent_tree = construct_indent_tree(code_body)
    return reconstruct_from_indent_tree(indent_tree)


def write_output(imports_text: str, code_text: str, output_path: Path) -> None:
    """Write the final output file with imports at the top, then code body."""
    output_text = imports_text + "\n\n" + code_text
    output_path.write_text(output_text)
    logging.info(f"Bundled file written to: {output_path}")


def get_python_files_in_dir(directory: Path) -> list[Path]:
    """Recursively collect all .py files in a directory."""
    return [
        file
        for root, _, files in os.walk(directory)
        for file in (Path(root) / f for f in files if f.endswith(".py"))
    ]


def find_first_usage_lines(
    code_body_lines: list[str], imports: list[str], from_imports: list[str]
) -> list[str]:
    """
    Order imports by first usage in the code body. Unused imports go at the end.
    For from-imports, use the minimum line number of all imported symbols.
    For plain imports, use the minimum line number of the module name.
    Preserve original order for ties.
    """
    usage_map = {}
    code_lines = code_body_lines
    # For plain imports, look for 'module.' or 'module(' or 'module ' in code
    for idx, imp in enumerate(imports):
        parts = imp.split()
        if len(parts) >= 2:
            module = parts[1].split(",")[0]
            module = module.split("as")[0].strip()
            first_line = float("inf")
            for line_idx, line in enumerate(code_lines):
                if f"{module}." in line or f"{module}(" in line or f"{module} " in line:
                    first_line = line_idx
                    break
            usage_map[(imp, idx)] = first_line
    # For from-imports, look for all imported symbols, use the minimum line number
    for idx, imp in enumerate(from_imports):
        try:
            left, right = imp.split("import", 1)
            symbols = [s.strip() for s in right.split(",") if s.strip()]
        except Exception:
            symbols = []
        first_line = float("inf")
        for symbol in symbols:
            for line_idx, line in enumerate(code_lines):
                if f"{symbol}(" in line or f"{symbol} " in line or f"{symbol}." in line:
                    if line_idx < first_line:
                        first_line = line_idx
                    break
        usage_map[(imp, idx + 10000)] = (
            first_line  # offset idx to preserve order between import/from
        )
    # Sort by first usage, then by original order
    ordered = sorted(usage_map.items(), key=lambda x: (x[1], x[0][1]))
    return [imp for (imp, _), _ in ordered]


def get_defined_and_used_symbols(file_path: Path) -> tuple[set[str], set[str]]:
    """
    Parse a Python file and return a set of defined symbols (functions/classes)
    and a set of used symbols (names used in function calls, attribute access, etc.).
    """
    source = file_path.read_text()
    tree = ast.parse(source, filename=str(file_path))
    defined = set()
    used = set()

    class SymbolVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            defined.add(node.name)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            defined.add(node.name)
            self.generic_visit(node)

        def visit_ClassDef(self, node):
            defined.add(node.name)
            self.generic_visit(node)

        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                used.add(node.id)

        def visit_Attribute(self, node):
            # Only add the attribute name, not the full chain
            used.add(node.attr)
            self.generic_visit(node)

    SymbolVisitor().visit(tree)
    return defined, used


def topological_file_order(py_files: list[Path]) -> list[Path]:
    """
    Return a list of files sorted so that dependencies come before dependents.
    Ensures all files are included, even if there are missing symbols or cycles.
    """
    symbol_to_file = {}
    file_defined = {}
    file_used = {}
    for file in py_files:
        defined, used = get_defined_and_used_symbols(file)
        file_defined[file] = defined
        file_used[file] = used
        for sym in defined:
            symbol_to_file[sym] = file
    # Build dependency graph
    deps = defaultdict(set)
    for file in py_files:
        for sym in file_used[file]:
            dep_file = symbol_to_file.get(sym)
            if dep_file and dep_file != file:
                deps[file].add(dep_file)
    # Topological sort (robust, includes all files)
    visited = set()
    result = []
    temp_mark = set()

    def visit(n):
        if n in visited:
            return
        if n in temp_mark:
            # Cycle detected, skip
            return
        temp_mark.add(n)
        for m in deps.get(n, []):
            visit(m)
        temp_mark.remove(n)
        visited.add(n)
        result.append(n)

    for file in py_files:
        visit(file)
    # Add any files not in result (in case of missing symbols)
    for file in py_files:
        if file not in result:
            result.append(file)
    return result[::-1]  # reverse to get correct order


def main(
    input_file: str = "test_levels.py",
    output_file: str = "test_levels_bundled.py",
) -> None:
    """
    Orchestrate reading, parsing, processing, bundling, and writing.
    Supports both single file and directory input.
    Ensures all imports are reconstructed and written at the top.
    Deduplicates plain import statements while preserving order.
    Orders imports by first usage in the code body.
    Stacks files in dependency order.
    """
    logging.basicConfig(level=logging.INFO)
    input_path = Path(input_file)
    if not input_path.exists():
        logging.error(f"Input file not found: {input_file}")
        return

    all_import_lines: list[str] = []
    all_code_body_lines: list[str] = []

    if input_path.is_dir():
        py_files = get_python_files_in_dir(input_path)
        # Topologically sort files by dependency
        py_files_sorted = topological_file_order(py_files)
        for py_file in py_files_sorted:
            lines = read_file_lines(py_file)
            import_lines, code_body_lines = parse_lines(lines)
            all_import_lines.extend(import_lines)
            all_code_body_lines.extend(code_body_lines)
        package_name = input_path.name
    else:
        lines = read_file_lines(input_path)
        import_lines, code_body_lines = parse_lines(lines)
        all_import_lines.extend(import_lines)
        all_code_body_lines.extend(code_body_lines)
        package_name = input_path.stem

    process_imports(all_import_lines, package_name)
    reconstructed_code = bundle_code(all_code_body_lines)
    # Deduplicate plain imports while preserving order
    seen_imports = set()
    plain_imports = []
    for imp in IMPORTS["import"]:
        if imp not in seen_imports:
            plain_imports.append(imp)
            seen_imports.add(imp)
    from_imports = reconstruct_imports(IMPORTS["from"])
    # Order imports by first usage
    ordered_imports = find_first_usage_lines(all_code_body_lines, plain_imports, from_imports)
    imports_text = "\n".join([imp for imp in ordered_imports if imp.strip()])
    write_output(imports_text, reconstructed_code, Path(output_file))
    # Optionally print for debug
    print("Reconstructed imports:")
    for stmt in ordered_imports:
        print(stmt)
    print("\nReconstructed code body:")
    print(reconstructed_code)


if __name__ == "__main__":
    main(
        "erasmus",
        "erasmus_bundled.py",
    )
