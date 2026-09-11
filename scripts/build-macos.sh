#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 ]]; then
    echo "Build on arm64 macOS." >&2
    exit 1
fi

# Install the pinned build dependencies into this repository's virtual environment first.
export PYINSTALLER_CONFIG_DIR="$PWD/.git/pyinstaller-cache"
.git/release-venv/bin/python -m PyInstaller \
    --noconfirm --clean --onefile --target-architecture arm64 \
    --name ledger-macos-arm64 \
    --distpath .git/release --workpath .git/pyinstaller-work \
    --specpath .git ledger
