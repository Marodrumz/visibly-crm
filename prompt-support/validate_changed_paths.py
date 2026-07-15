"""Validate that changed files stay within the allowed paths for a build step."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ALLOWED_PREFIXES_BY_STEP: dict[str, tuple[str, ...]] = {
    "S00": (
        "docs/specs/",
        "docs/matrices/",
        "docs/adr/",
        "docs/plans/",
        "docs/progress/",
        "docs/compatibility/",
        "docs/test-evidence/",
        "prompt-support/validate_changed_paths.py",
    )
}


def _git_lines(*args: str) -> list[str]:
    completed = subprocess.run(
        ("git", *args),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _changed_paths() -> list[str]:
    tracked = _git_lines("diff", "--name-only")
    untracked = _git_lines("ls-files", "--others", "--exclude-standard")
    return sorted({path.replace("\\", "/") for path in [*tracked, *untracked]})


def _is_allowed(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in prefixes)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", required=True)
    args = parser.parse_args()

    step = args.step.upper()
    allowed_prefixes = ALLOWED_PREFIXES_BY_STEP.get(step)
    if allowed_prefixes is None:
        print(f"Unsupported step: {step}", file=sys.stderr)
        return 2

    root = Path.cwd()
    if not (root / ".git").exists():
        print("Run from repository root.", file=sys.stderr)
        return 2

    paths = _changed_paths()
    violations = [path for path in paths if not _is_allowed(path, allowed_prefixes)]

    print(f"step={step}")
    print(f"changed_paths={len(paths)}")
    for path in paths:
        print(path)
    print(f"violations={len(violations)}")
    for path in violations:
        print(f"VIOLATION {path}", file=sys.stderr)

    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
