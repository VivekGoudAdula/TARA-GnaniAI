"""
check_line_limits.py - Verifies that every source, test, script, and doc file is strictly under 250 lines.
Excludes virtualenvs, git metadata, node_modules, build artifacts, and package locks.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "dist", "build",
    "__pycache__", ".pytest_cache", ".system_generated",
}
IGNORE_FILES = {
    "package-lock.json", ".noise_cache.json",
}
CHECK_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".md", ".json", ".html", ".css", ".yml", ".yaml"
}
MAX_LINES = 250


def scan_files() -> int:
    violating_files = []
    total_checked = 0

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.name in IGNORE_FILES:
            continue
        if path.suffix not in CHECK_EXTENSIONS:
            continue

        total_checked += 1
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                line_count = sum(1 for _ in f)
            if line_count >= MAX_LINES:
                violating_files.append((path.relative_to(ROOT), line_count))
        except Exception as exc:
            print(f"[check_line_limits] Error reading {path}: {exc}")

    print(f"[check_line_limits] Checked {total_checked} files.")
    if violating_files:
        print(f"[check_line_limits] FAILED: {len(violating_files)} file(s) exceed {MAX_LINES} lines:")
        for rel_path, count in violating_files:
            print(f"  - {rel_path}: {count} lines")
        return 1

    print(f"[check_line_limits] PASSED: All {total_checked} files are strictly under {MAX_LINES} lines.")
    return 0


if __name__ == "__main__":
    sys.exit(scan_files())

