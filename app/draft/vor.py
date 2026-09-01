"""Value Over Replacement (VOR) engine for the draft assistant.

VOR methodology
---------------
For each position, replacement level is the projected points of the last
"startable" player league-wide at that position - the player a team could
realistically add off waivers instead of drafting. `compute_replacement_ranks`
derives that rank dynamically from roster construction (team count + starting
slots), including a probabilistic allocation of FLEX and SUPERFLEX slots
across their eligible positions, rather than a hardcoded "11th QB" rule - so
a Superflex league correctly pushes the QB replacement level much deeper
than a Standard one-QB league, which is exactly what makes top QBs carry far
more VOR in Superflex than they would in a 1-QB format.

VOR = a player's projected points minus the replacement-level points for
their position.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.draft.schema import PROJECTION_REQUIRED_COLUMNS
from app.draft.settings import LeagueSettings
from app.logging_setup import get_logger
from app.schema import FLEX_ELIGIBLE_POSITIONS, POSITIONS

# Empirical assumption: a Superflex slot is filled by a QB far more often
# than by an RB/WR/TE, because viable starting QBs are scarcer league-wide
# than viable RB/WR/TE flex plays. Must sum to 1.0.
SUPERFLEX_QB_DEMAND_SHARE: dict[str, float] = {
    "QB": 0.75,
    "RB": 0.10,
    "WR": 0.10,
    "TE": 0.05,
}

FLEX_DEMAND_SHARE: dict[str, float] = {
    pos: 1 / len(FLEX_ELIGIBLE_POSITIONS) for pos in FLEX_ELIGIBLE_POSITIONS
}

MIN_REPLACEMENT_RANK = 1


def compute_replacement_ranks(league: LeagueSettings) -> dict[str, int]:
    """Return {position: replacement_rank} - the position-specific draft
    rank (1-indexed, by projected points) whose player defines "replacement
    level" for that position under this league's roster construction."""
    teams = league.team_count
    roster = league.roster

    starters: dict[str, float] = {
        "QB": roster.qb * teams,
        "RB": roster.rb * teams,
        "WR": roster.wr * teams,
        "TE": roster.te * teams,
        "K": roster.k * teams,
        "DEF": roster.dst * teams,
    }

    if roster.flex:
        flex_starters = roster.flex * teams
        for pos, share in FLEX_DEMAND_SHARE.items():
            starters[pos] += flex_starters * share

    if league.superflex and roster.superflex:
        superflex_starters = roster.superflex * teams
        for pos, share in SUPERFLEX_QB_DEMAND_SHARE.items():
            starters[pos] += superflex_starters * share

    # Replacement level sits one pick past the last league-wide starter -
    # the best player still available on waivers/bench at that position.
    return {
        pos: max(MIN_REPLACEMENT_RANK, math.ceil(count) + 1) for pos, count in starters.items()
    }


@dataclass(frozen=True)
class TierConfig:
    """Gap-based tiering: start a new tier whenever the drop in VOR between
    consecutive players (within a position) exceeds `drop_fraction` of that
    position's own VOR range. Deterministic and dependency-free, and stable
    even for very small position pools."""

    drop_fraction: float = 0.12


def _assign_tiers(vor_sorted: pd.Series, drop_fraction: float) -> pd.Series:
    """`vor_sorted` must already be sorted descending. Returns a same-index
    Series of 1-indexed tier numbers."""
    if vor_sorted.empty:
        return pd.Series(dtype="int64")

    vor_range = float(vor_sorted.iloc[0] - vor_sorted.iloc[-1])
    threshold = vor_range * drop_fraction if vor_range > 0 else 0.0

    tiers = [1]
    values = vor_sorted.to_numpy()
    for prev, curr in zip(values, values[1:]):
        gap = prev - curr
        tiers.append(tiers[-1] + 1 if threshold > 0 and gap > threshold else tiers[-1])
    return pd.Series(tiers, index=vor_sorted.index)


def compute_vor(
    projections: pd.DataFrame,
    league: LeagueSettings,
    tier_config: TierConfig | None = None,
) -> pd.DataFrame:
    """Attach position_rank, replacement_points, vor, tier,
    overall_vor_rank, and recommended_round to a projections DataFrame.

    `projections` must have the columns in
    app.draft.schema.PROJECTION_REQUIRED_COLUMNS; an optional `adp` column
    is passed through untouched. Runtime is O(n log n): each position group
    is sorted once for ranking/tiering, and replacement points are looked
    up per-position (not recomputed per row).
    """
    missing = set(PROJECTION_REQUIRED_COLUMNS) - set(projections.columns)
    if missing:
        raise ValueError(f"projections is missing required column(s): {sorted(missing)}")

    empty_extra_columns = {
        "position_rank": pd.Series(dtype="int64"),
        "replacement_points": pd.Series(dtype="float64"),
        "vor": pd.Series(dtype="float64"),
        "tier": pd.Series(dtype="int64"),
        "overall_vor_rank": pd.Series(dtype="int64"),
        "recommended_round": pd.Series(dtype="int64"),
    }
    if projections.empty:
        return projections.assign(**empty_extra_columns)

    logger = get_logger()
    unknown_positions = set(projections["position"].unique()) - set(POSITIONS)
    if unknown_positions:
        logger.warning(
            "%d player(s) have unrecognized position(s) %s - they'll get VOR=0.",
            int(projections["position"].isin(unknown_positions).sum()),
            sorted(unknown_positions),
        )

    tier_config = tier_config or TierConfig()
    replacement_ranks = compute_replacement_ranks(league)

    working = projections.copy()
    working["position_rank"] = (
        working.groupby("position")["projected_points"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    sorted_points_by_position: dict[str, Any] = {
        str(pos): group.sort_values(ascending=False).to_numpy()
        for pos, group in working.groupby("position")["projected_points"]
    }

    def _replacement_points_for(position: str) -> float:
        points = sorted_points_by_position.get(position)
        rank = replacement_ranks.get(position)
        if points is None or len(points) == 0 or not rank:
            return 0.0
        idx = min(rank, len(points)) - 1
        return float(points[idx])

    replacement_by_position = {pos: _replacement_points_for(pos) for pos in sorted_points_by_position}
    working["replacement_points"] = working["position"].map(replacement_by_position)
    working["vor"] = working["projected_points"] - working["replacement_points"]

    tier_parts = []
    for _, group in working.groupby("position", group_keys=False):
        vor_sorted = group.sort_values("vor", ascending=False)["vor"]
        tier_parts.append(_assign_tiers(vor_sorted, tier_config.drop_fraction))
    working["tier"] = pd.concat(tier_parts).reindex(working.index)

    working = working.sort_values("vor", ascending=False).reset_index(drop=True)
    working["overall_vor_rank"] = working.index + 1
    working["recommended_round"] = ((working["overall_vor_rank"] - 1) // league.team_count + 1).astype(
        int
    )

    return working
