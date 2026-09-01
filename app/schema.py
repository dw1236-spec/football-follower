"""Canonical player-record schema used throughout the app."""
from __future__ import annotations

from dataclasses import dataclass

POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF"]

SCORING_SYSTEMS = ["PPR", "Half-PPR", "Standard"]

LEAGUE_FORMATS = ["Standard", "Superflex"]

FLEX_ELIGIBLE_POSITIONS: tuple[str, ...] = ("RB", "WR", "TE")
SUPERFLEX_ELIGIBLE_POSITIONS: tuple[str, ...] = ("QB", "RB", "WR", "TE")

# Extra pooled-position rows added to the analysis (alongside the real
# per-position rows) when the league format calls for them, keyed by the
# label shown in the summary table/exports.
SUPERFLEX_POSITION_GROUPS: dict[str, tuple[str, ...]] = {
    "FLEX": FLEX_ELIGIBLE_POSITIONS,
    "SUPERFLEX": SUPERFLEX_ELIGIBLE_POSITIONS,
}


@dataclass(frozen=True)
class SchemaField:
    name: str
    dtype: str  # "str" | "int" | "float"
    label: str
    aliases: tuple[str, ...]


REQUIRED_FIELDS: list[SchemaField] = [
    SchemaField(
        "player_name", "str", "Player Name",
        ("player", "name", "player_name", "full_name", "player name"),
    ),
    SchemaField(
        "position", "str", "Position",
        ("pos", "position", "positon"),
    ),
    SchemaField(
        "draft_rank", "int", "Draft Rank (ADP)",
        ("draft_rank", "adp", "draft_pick", "draft pick", "overall_pick", "draftrank", "draft rank"),
    ),
    SchemaField(
        "games_played", "int", "Games Played",
        ("games_played", "games", "gp", "games played"),
    ),
    SchemaField(
        "total_points", "float", "Total Points",
        ("total_points", "points", "fpts", "fantasy_points", "total points", "fantasy points"),
    ),
    SchemaField(
        "points_per_game", "float", "Points Per Game",
        ("points_per_game", "ppg", "avg_points", "points per game"),
    ),
    SchemaField(
        "season_rank", "int", "Season-End Rank",
        ("season_rank", "final_rank", "end_of_season_rank", "actual_rank", "season rank"),
    ),
]

REQUIRED_FIELD_NAMES = [f.name for f in REQUIRED_FIELDS]

DRAFT_RANK_MIN = 1
DRAFT_RANK_MAX = 300

BUST_VALUE_THRESHOLD = 0.20  # 20% of expected points for the draft slot
