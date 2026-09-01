"""League settings (team count, scoring, roster construction) loaded from a
YAML or JSON config file. Mirrors app.config's "never trust the file, always
fall back to a safe default" philosophy from the desktop app.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.schema import SCORING_SYSTEMS

DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent / "config" / "league_settings.yaml"
)

_SUPPORTED_SUFFIXES = {".yaml", ".yml", ".json"}


class LeagueConfigError(Exception):
    """Raised when a league settings file is missing, malformed, or invalid."""


@dataclass(frozen=True)
class RosterSlots:
    qb: int = 1
    rb: int = 2
    wr: int = 2
    te: int = 1
    flex: int = 1  # RB/WR/TE eligible
    superflex: int = 1  # QB/RB/WR/TE eligible
    k: int = 1
    dst: int = 1
    bench: int = 6

    def total_starters(self) -> int:
        return self.qb + self.rb + self.wr + self.te + self.flex + self.superflex + self.k + self.dst


@dataclass(frozen=True)
class LeagueSettings:
    team_count: int = 10
    scoring: str = "Half-PPR"
    superflex: bool = True
    roster: RosterSlots = field(default_factory=RosterSlots)

    def __post_init__(self) -> None:
        if self.team_count < 2:
            raise LeagueConfigError(f"team_count must be at least 2 (got {self.team_count}).")
        if self.scoring not in SCORING_SYSTEMS:
            raise LeagueConfigError(
                f"scoring must be one of {SCORING_SYSTEMS} (got '{self.scoring}')."
            )
        if self.superflex and self.roster.superflex < 1:
            raise LeagueConfigError("superflex=True requires roster.superflex >= 1.")


DEFAULT_LEAGUE_SETTINGS = LeagueSettings()


def _settings_from_dict(data: dict[str, Any]) -> LeagueSettings:
    known_keys = {"team_count", "scoring", "superflex", "roster"}
    unknown_keys = set(data) - known_keys
    if unknown_keys:
        raise LeagueConfigError(f"Unknown league setting(s): {sorted(unknown_keys)}")

    roster_data = data.get("roster") or {}
    unknown_roster_keys = set(roster_data) - set(RosterSlots.__dataclass_fields__)
    if unknown_roster_keys:
        raise LeagueConfigError(f"Unknown roster slot(s): {sorted(unknown_roster_keys)}")

    try:
        roster = RosterSlots(**roster_data)
        kwargs: dict[str, Any] = {"roster": roster}
        for key in ("team_count", "scoring", "superflex"):
            if key in data:
                kwargs[key] = data[key]
        return LeagueSettings(**kwargs)
    except (TypeError, ValueError) as exc:
        raise LeagueConfigError(f"Invalid league settings: {exc}") from exc


def load_league_settings(path: str | Path | None = None) -> LeagueSettings:
    """Load league settings from a YAML/JSON file.

    If `path` is omitted, loads the bundled default config
    (config/league_settings.yaml); if that file is somehow missing, falls
    back to DEFAULT_LEAGUE_SETTINGS (10-team, Half-PPR, Superflex) so the
    draft assistant always has *something* runnable. An explicitly passed
    `path` that doesn't exist or can't be parsed is a real, reported error.
    """
    file_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH

    if not file_path.exists():
        if path is None:
            return DEFAULT_LEAGUE_SETTINGS
        raise LeagueConfigError(f"League settings file not found: {file_path}")

    if file_path.suffix.lower() not in _SUPPORTED_SUFFIXES:
        raise LeagueConfigError(
            f"Unsupported league settings format '{file_path.suffix}' - use .yaml, .yml, or .json."
        )

    try:
        text = file_path.read_text(encoding="utf-8")
        if file_path.suffix.lower() == ".json":
            data = json.loads(text) if text.strip() else {}
        else:
            data = yaml.safe_load(text) or {}
    except (yaml.YAMLError, json.JSONDecodeError, OSError) as exc:
        raise LeagueConfigError(f"Could not read/parse '{file_path.name}': {exc}") from exc

    if not isinstance(data, dict):
        raise LeagueConfigError(
            f"'{file_path.name}' must contain a mapping of settings at the top level."
        )

    return _settings_from_dict(data)


def settings_to_dict(settings: LeagueSettings) -> dict[str, Any]:
    return asdict(settings)
