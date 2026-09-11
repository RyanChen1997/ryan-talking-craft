#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SKILLS_DIR="$HOME/.pi/agent/skills"
DRY_RUN=false

WHITELIST=(
  "SKILL.md"
  "references"
  "scripts"
  "assets"
  "tests"
  "pyproject.toml"
  "uv.lock"
)

usage() {
  cat <<'EOF'
Usage: ./install.sh [--skills-dir DIR] [--dry-run]
EOF
}

while (($#)); do
  case "$1" in
    --skills-dir)
      [[ $# -ge 2 ]] || { echo "--skills-dir requires a directory" >&2; exit 2; }
      SKILLS_DIR="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$SKILLS_DIR" in
  "~") SKILLS_DIR="$HOME" ;;
  "~/"*) SKILLS_DIR="$HOME/${SKILLS_DIR#\~/}" ;;
esac

for item in "${WHITELIST[@]}"; do
  [[ -e "$ROOT/$item" ]] || { echo "Missing whitelist item: $ROOT/$item" >&2; exit 1; }
done

TARGET="$SKILLS_DIR/ryan-talking-craft"
if $DRY_RUN; then
  echo "Target: $TARGET"
  echo "Whitelist:"
  printf '  %s\n' "${WHITELIST[@]}"
  echo "Excluded inside whitelist directories: .tmp, caches, node_modules"
  exit 0
fi

mkdir -p "$SKILLS_DIR"
SKILLS_DIR="$(cd -- "$SKILLS_DIR" && pwd -P)"
TARGET="$SKILLS_DIR/ryan-talking-craft"

[[ "$SKILLS_DIR" != "/" && "$SKILLS_DIR" != "$HOME" ]] || {
  echo "Choose a dedicated skills directory, not filesystem root or home" >&2
  exit 1
}
[[ ! -L "$TARGET" ]] || { echo "Refusing to replace a symlink target" >&2; exit 1; }
case "$TARGET/" in "$ROOT/"*) echo "Install target must not overlap source repository" >&2; exit 1;; esac
case "$ROOT/" in "$TARGET/"*) echo "Install target must not overlap source repository" >&2; exit 1;; esac

if [[ -e "$TARGET" ]]; then
  while true; do
    printf 'A skill named ryan-talking-craft already exists at %s. Delete it and reinstall? [yes/no]: ' "$TARGET"
    if ! IFS= read -r answer; then
      echo
      echo "Installation cancelled: no confirmation received."
      exit 1
    fi
    case "$answer" in
      yes)
        rm -rf -- "$TARGET"
        break
        ;;
      no)
        echo "Installation cancelled."
        exit 0
        ;;
      *)
        echo "Please answer yes or no."
        ;;
    esac
  done
fi

TEMP_DIR="$(mktemp -d "$SKILLS_DIR/.talking-craft-install.XXXXXX")"
trap 'rm -rf "$TEMP_DIR"' EXIT
STAGE="$TEMP_DIR/ryan-talking-craft"
mkdir -p "$STAGE"

for item in "${WHITELIST[@]}"; do
  destination="$STAGE/$(dirname -- "$item")"
  mkdir -p "$destination"
  cp -R "$ROOT/$item" "$destination/"
done

find "$STAGE" -type d \( \
  -name .tmp -o \
  -name __pycache__ -o \
  -name .pytest_cache -o \
  -name .ruff_cache -o \
  -name node_modules \
\) -prune -exec rm -rf {} +
find "$STAGE" -type f \( -name '*.pyc' -o -name '.DS_Store' \) -delete

# README 展示素材不随 skill 安装
rm -rf -- "$STAGE/assets/readme"

mv "$STAGE" "$TARGET"
printf 'Installed: %s\n' "$TARGET"
