#!/usr/bin/env python3
"""Fail if any source file exceeds the line limit (default 300)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_LINES = 300
EXTENSIONS = {".py", ".ts", ".tsx"}
SKIP_FILES = {
    "scripts/restructure_backend.py",
    "scripts/restructure_frontend.py",
}
SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    "dist",
    "email_platform.egg-info",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in EXTENSIONS:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel in SKIP_FILES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def main() -> int:
    violations: list[tuple[int, Path]] = []
    for path in iter_source_files():
        try:
            count = sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if count > MAX_LINES:
            violations.append((count, path))

    if not violations:
        print(f"OK: no files exceed {MAX_LINES} lines")
        return 0

    print(f"Files exceeding {MAX_LINES} lines:")
    for count, path in violations:
        rel = path.relative_to(ROOT)
        print(f"  {count:4d}  {rel}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
