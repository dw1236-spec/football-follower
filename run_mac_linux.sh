#!/usr/bin/env bash
# One-click launcher for macOS/Linux: creates a virtual environment (first
# run only), installs dependencies, and starts the app.
# Usage: ./run_mac_linux.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing dependencies (first run only, this may take a minute)..."
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo ""
echo "Launching NFL Fantasy Draft Analyzer..."
python main.py
