#!/usr/bin/env bash
# Build a standalone macOS (12+) .app bundle in dist/NFLDraftAnalyzer.app.
# Must be run on macOS - PyInstaller does not cross-compile.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m pip install -r requirements-dev.txt
python3 -m PyInstaller --noconfirm packaging/pyinstaller.spec

echo ""
echo "Build complete: dist/NFLDraftAnalyzer.app"
echo "Note: the app is unsigned. To distribute it, sign and notarize it with your Apple Developer account."
