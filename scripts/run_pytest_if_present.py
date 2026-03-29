from __future__ import annotations

import subprocess
from pathlib import Path


def has_discoverable_tests(project_root: Path) -> bool:
    tests_dir = project_root / "tests"
    if not tests_dir.is_dir():
        return False

    for pattern in ("test_*.py", "*_test.py"):
        if any(tests_dir.rglob(pattern)):
            return True
    return False


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]

    if not has_discoverable_tests(project_root):
        print("pytest skipped: no tests discovered under tests/")
        return 0

    return subprocess.call(["pytest"], cwd=str(project_root))


if __name__ == "__main__":
    raise SystemExit(main())
