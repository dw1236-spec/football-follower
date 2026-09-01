#!/usr/bin/env bash
# Build a standalone Linux (Ubuntu 20.04+) app bundle in dist/NFLDraftAnalyzer/.
# Must be run on Linux - PyInstaller does not cross-compile.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m pip install -r requirements-dev.txt
python3 -m PyInstaller --noconfirm packaging/pyinstaller.spec

echo ""
echo "Build complete: dist/NFLDraftAnalyzer/"
echo "Run it with: dist/NFLDraftAnalyzer/NFLDraftAnalyzer"
