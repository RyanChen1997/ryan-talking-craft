from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class TalkingCraftError(RuntimeError):
    """Raised when a deterministic skill operation cannot be completed."""


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


def run_command(
    args: Sequence[str],
    *,
    check: bool = True,
    cwd: Path | None = None,
) -> CommandResult:
    """Run an external command without invoking a shell."""
    completed = subprocess.run(
        list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    result = CommandResult(
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )
    if check and completed.returncode != 0:
        rendered = " ".join(args)
        raise TalkingCraftError(
            f"Command failed ({completed.returncode}): {rendered}\n{completed.stderr.strip()}"
        )
    return result


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    """Read UTF-8 JSON and return its decoded value."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TalkingCraftError(f"Cannot read JSON {path}: {error}") from error


def write_json(path: Path, value: Any) -> None:
    """Write stable, human-readable UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_fraction(value: str | None) -> float | None:
    """Parse an ffprobe fraction such as 30000/1001."""
    if not value or value == "0/0":
        return None
    if "/" not in value:
        try:
            return float(value)
        except ValueError:
            return None
    numerator, denominator = value.split("/", maxsplit=1)
    try:
        denominator_value = float(denominator)
        if denominator_value == 0:
            return None
        return float(numerator) / denominator_value
    except ValueError:
        return None
