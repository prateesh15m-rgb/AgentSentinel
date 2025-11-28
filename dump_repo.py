#!/usr/bin/env python3
"""
Dump repo structure + key file contents + lightweight code stats
so you can paste into ChatGPT for architecture/optimization review.

Usage (from repo root):
    python dump_repo.py > repo_snapshot.txt

Optional: target a subfolder (e.g. just ADK + supervisor):
    python dump_repo.py v2_adk > repo_snapshot_v2_adk.txt
"""

import os
import sys
import ast
from collections import Counter, defaultdict
from pathlib import Path

# ---- CONFIG -------------------------------------------------------------

# Directories we don't care about (adjust if needed)
IGNORE_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".DS_Store",
}

# File extensions we *do* care about for CONTENT DUMP
INCLUDE_EXTS = {
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
    ".csv",
    ".txt",
}

# Max bytes of a single file to print
MAX_FILE_BYTES = 40_000  # ~40 KB

# Max depth for directory tree (None = no limit)
MAX_TREE_DEPTH = None  # or set to an int like 5


# ---- BASIC HELPERS ------------------------------------------------------


def is_binary_file(path: str) -> bool:
    """Heuristic: treat file as binary if it has null bytes in first 1024 bytes."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(1024)
        if b"\0" in chunk:
            return True
        return False
    except Exception:
        return True


def print_tree(root: str, max_depth=None):
    """
    Print a simple directory tree from root.
    """
    print("=== DIRECTORY TREE ===")
    root = os.path.abspath(root)
    for current_root, dirs, files in os.walk(root):
        # Compute depth relative to root
        rel = os.path.relpath(current_root, root)
        if rel == ".":
            depth = 0
            display_name = "."
        else:
            depth = rel.count(os.sep) + 1
            display_name = rel

        if max_depth is not None and depth > max_depth:
            # Don't descend further
            dirs[:] = []
            continue

        indent = "    " * depth
        print(f"{indent}{display_name}/")

        # Filter dir list in-place to avoid walking into ignored dirs
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for f in sorted(files):
            print(f"{indent}    {f}")

    print("\n")  # spacing


def dump_files(root: str):
    """
    Print contents of relevant files under root.
    """
    root = os.path.abspath(root)
    print("=== FILE CONTENTS (FILTERED) ===")

    for current_root, dirs, files in os.walk(root):
        # Filter ignored dirs
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for fname in sorted(files):
            path = os.path.join(current_root, fname)
            rel_path = os.path.relpath(path, root)
            ext = os.path.splitext(fname)[1].lower()

            if ext not in INCLUDE_EXTS:
                continue

            if not os.path.isfile(path):
                continue

            if is_binary_file(path):
                # Skip obvious binary files
                continue

            try:
                size = os.path.getsize(path)
            except OSError:
                continue

            print("\n" + "=" * 80)
            print(f"=== FILE: {rel_path} (size: {size} bytes) ===")
            print("=" * 80)

            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read(MAX_FILE_BYTES)
            except UnicodeDecodeError:
                # fallback with errors replaced, just in case
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(MAX_FILE_BYTES)
            except Exception as e:
                print(f"[ERROR reading file: {e}]")
                continue

            print(content)
            if size > MAX_FILE_BYTES:
                print("\n[TRUNCATED OUTPUT - file larger than MAX_FILE_BYTES]\n")


# ---- CODE ANALYSIS HELPERS ----------------------------------------------


def analyze_python_file(path: Path):
    """
    Returns a dict with:
      - relpath
      - lines
      - num_functions
      - num_classes
      - imports (set of module names)
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None

    relpath = str(path)
    lines = text.count("\n") + 1

    try:
        tree = ast.parse(text, filename=relpath)
    except SyntaxError:
        # Non-parsable file; still return basic stats
        return {
            "relpath": relpath,
            "lines": lines,
            "num_functions": 0,
            "num_classes": 0,
            "imports": set(),
        }

    num_functions = 0
    num_classes = 0
    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            num_functions += 1
        elif isinstance(node, ast.ClassDef):
            num_classes += 1
        elif isinstance(node, ast.Import):
            for alias in node.names:
                root_name = alias.name.split(".")[0]
                imports.add(root_name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_name = node.module.split(".")[0]
                imports.add(root_name)

    return {
        "relpath": relpath,
        "lines": lines,
        "num_functions": num_functions,
        "num_classes": num_classes,
        "imports": imports,
    }


def analyze_repo(root: Path):
    file_stats = []
    import_counter = Counter()
    per_import_files = defaultdict(list)

    for dirpath, dirnames, filenames in os.walk(root):
        # Remove ignored dirs in-place to prune traversal
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            full_path = Path(dirpath) / filename
            stat = analyze_python_file(full_path)
            if not stat:
                continue
            file_stats.append(stat)
            for imp in stat["imports"]:
                import_counter[imp] += 1
                per_import_files[imp].append(stat["relpath"])

    return file_stats, import_counter, per_import_files


def print_code_stats(root: Path, top_imports: int = 40):
    print("=== CODE STATS (PYTHON) ===")
    file_stats, import_counter, _ = analyze_repo(root)

    # Per-file stats (sorted for readability)
    for stat in sorted(file_stats, key=lambda s: s["relpath"]):
        rel = os.path.relpath(stat["relpath"], root)
        imports_preview = ", ".join(sorted(stat["imports"]))[:120]
        print(
            f"- {rel}\n"
            f"    lines         : {stat['lines']}\n"
            f"    functions     : {stat['num_functions']}\n"
            f"    classes       : {stat['num_classes']}\n"
            f"    imports       : {imports_preview}\n"
        )

    # Global import summary
    print("\n=== GLOBAL IMPORT SUMMARY ===")
    print(f"(Top {top_imports} modules by frequency across Python files)\n")

    for module, count in import_counter.most_common(top_imports):
        print(f"{module:25s}  used in {count} file(s)")

    print("\n")  # spacing


# ---- MAIN ---------------------------------------------------------------


def main():
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = "."

    root_abs = os.path.abspath(root)

    print(f"# Repo snapshot for: {root_abs}\n")

    # 1) Tree
    print_tree(root_abs, MAX_TREE_DEPTH)

    # 2) Code stats (for optimization/architecture)
    print_code_stats(Path(root_abs), top_imports=40)

    # 3) File contents (for detailed review)
    dump_files(root_abs)


if __name__ == "__main__":
    main()
