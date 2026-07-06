from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SECRET_PATTERNS = [
    re.compile(r"(?i)(?:^|[\s{,])(?:INVEST_TOKEN|T_INVEST_TOKEN|API_KEY|SECRET|PASSWORD)\s*[:=]\s*['\"]?([^'\"\s]+)"),
    re.compile(r"t\.[A-Za-z0-9_-]{40,}"),
]

BLOCKED_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
}

BLOCKED_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
}

TEXT_SUFFIXES = {
    ".cfg",
    ".csv",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def main() -> int:
    files = tracked_files()
    problems: list[str] = []
    for path in files:
        if path.name in BLOCKED_FILENAMES or path.suffix in BLOCKED_SUFFIXES:
            problems.append(f"blocked tracked file: {path.as_posix()}")
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        text = read_text(path)
        if text is None:
            continue
        for pattern in SECRET_PATTERNS:
            match = pattern.search(text)
            if match and not is_placeholder(match.group(1) if match.groups() else match.group(0)):
                problems.append(f"possible secret pattern in {path.as_posix()}")
                break

    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    return 0


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [Path(line) for line in result.stdout.splitlines() if line]


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def is_placeholder(value: str) -> bool:
    normalized = value.strip("\"'").lower()
    return normalized in {"str", "none", "null"} or any(
        marker in normalized for marker in ["your_", "example", "placeholder", "read_only_token"]
    )


if __name__ == "__main__":
    raise SystemExit(main())
