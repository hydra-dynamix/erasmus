from pathlib import Path
from typing import List


def get_ordered_files(py_files: list[Path], path_manager) -> list[Path]:
    """
    Return a list of files ordered according to the custom build order defined in the path manager.
    Only files in the custom order are included, in the specified order.
    """
    custom_order_paths = path_manager.build_order()
    # Use path_manager.rel_to_project for normalization
    custom_order = [str(path_manager.rel_to_project(p)) for p in custom_order_paths]
    project_root = path_manager.get_project_root().resolve()
    rel_to_file = {str(f.resolve().relative_to(project_root)): f for f in py_files}
    ordered_files = []
    for rel_path in custom_order:
        if rel_path in rel_to_file:
            ordered_files.append(rel_to_file[rel_path])
    return ordered_files
