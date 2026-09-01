"""Live draft-pick recommendation: given the remaining player pool and a
team's roster-so-far, recommend the highest-VOR player who still fills a
useful roster need. `dry_run=True` prints the VOR score and replacement
baseline behind every candidate considered, so a pick can be audited - per
the project's existing convention of never trusting a black box (see
app.logging_setup).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.logging_setup import get_logger

# Positions capped at a small, fixed number of *rostered* players regardless
# of VOR - once a team has enough, another K/DEF is never the best use of a
# pick even if it happens to show high VOR.
DEFAULT_ROSTER_CAPS: dict[str, int] = {"K": 1, "DEF": 1}

_NO_CAP = 10_000
_DRY_RUN_PREVIEW_SIZE = 5


@dataclass
class RosterState:
    """Positions already drafted onto one team, by count."""

    counts: dict[str, int] = field(default_factory=dict)

    def count(self, position: str) -> int:
        return self.counts.get(position, 0)

    def add(self, position: str) -> None:
        self.counts[position] = self.count(position) + 1


@dataclass(frozen=True)
class PickRecommendation:
    player_name: str
    position: str
    team: str
    vor: float
    replacement_points: float
    projected_points: float
    reasoning: str


def recommend_pick(
    available: pd.DataFrame,
    roster_state: RosterState,
    roster_caps: dict[str, int] | None = None,
    dry_run: bool = False,
) -> PickRecommendation | None:
    """Return the highest-VOR available player who doesn't exceed a roster
    cap, or None if the pool is empty or every remaining player is capped
    out. `available` must already carry `vor` and `replacement_points`
    columns (see app.draft.vor.compute_vor).
    """
    if available.empty:
        return None

    logger = get_logger()
    caps = {**DEFAULT_ROSTER_CAPS, **(roster_caps or {})}

    eligible = available[
        available["position"].map(lambda pos: roster_state.count(pos) < caps.get(pos, _NO_CAP))
    ]
    ranked = eligible.sort_values("vor", ascending=False)

    if dry_run:
        logger.info("Dry-run: top VOR candidates for this pick (roster: %s):", roster_state.counts)
        for _, row in ranked.head(_DRY_RUN_PREVIEW_SIZE).iterrows():
            logger.info(
                "  %-22s %-4s VOR=%.1f (proj=%.1f, replacement=%.1f)",
                row["player_name"],
                row["position"],
                row["vor"],
                row["projected_points"],
                row["replacement_points"],
            )

    if ranked.empty:
        return None

    best = ranked.iloc[0]
    reasoning = (
        f"Highest available VOR ({best['vor']:.1f}) - {best['projected_points']:.1f} projected pts "
        f"vs. a {best['position']} replacement level of {best['replacement_points']:.1f} pts."
    )
    return PickRecommendation(
        player_name=best["player_name"],
        position=best["position"],
        team=best["team"],
        vor=float(best["vor"]),
        replacement_points=float(best["replacement_points"]),
        projected_points=float(best["projected_points"]),
        reasoning=reasoning,
    )
