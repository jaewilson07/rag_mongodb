"""Start Docker services for the MongoDB RAG Agent project."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent
_ROOT_CANDIDATES = [_SCRIPT_DIR, _SCRIPT_DIR.parent]
PROJECT_ROOT = next(
    (candidate for candidate in _ROOT_CANDIDATES if (candidate / "docker-compose.yml").exists()),
    _SCRIPT_DIR,
)
DEFAULT_COMPOSE = PROJECT_ROOT / "docker-compose.yml"
SEARCH_COMPOSE = PROJECT_ROOT / "docker-compose-search.yml"


def _run_compose(compose_file: Path) -> int:
    if not compose_file.exists():
        print(f"Missing compose file: {compose_file}")
        return 1
    cmd = ["docker-compose", "-f", str(compose_file), "up", "-d"]
    print(f"Starting services with {compose_file.name}...")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Start Docker services.")
    parser.add_argument(
        "--search",
        action="store_true",
        help="Also start services from docker-compose-search.yml",
    )
    args = parser.parse_args()

    exit_code = _run_compose(DEFAULT_COMPOSE)
    if exit_code != 0:
        return exit_code

    if args.search:
        exit_code = _run_compose(SEARCH_COMPOSE)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
