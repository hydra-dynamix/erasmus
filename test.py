import ast
import tokenize
import io


def sanitize_docstrings(source: str, replacement: str = '""') -> str:
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


if __name__ == "__main__":
    from pathlib import Path

    filepath = Path(__file__).parent / "input.py"
    string_value = filepath.read_text()
    print(sanitize_docstrings(string_value))
