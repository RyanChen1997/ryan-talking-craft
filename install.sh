#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Use uv-managed Python without relying on a potentially stale repository .venv.
exec uv run --no-project --python '>=3.12' python "$ROOT/scripts/install_skill.py" "$@"
