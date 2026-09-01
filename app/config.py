"""Local JSON config persistence (~/.nfl_draft_analyzer/config.json)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".nfl_draft_analyzer"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "last_file_path": None,
    "scoring_system": "PPR",
    "selected_positions": ["QB", "RB", "WR", "TE", "K", "DEF"],
    "export_directory": None,
    "window_geometry": None,
}


def load_config() -> dict[str, Any]:
    """Load persisted config, falling back to defaults on any problem."""
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_CONFIG)
        merged.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG})
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)


def save_config(config: dict[str, Any]) -> None:
    """Persist config to disk, silently ignoring filesystem errors."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        payload = {k: config.get(k, DEFAULT_CONFIG[k]) for k in DEFAULT_CONFIG}
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except OSError:
        pass
