"""Fills in `projected_points` when a data source only provides rank/ADP
(FantasyPros' free rankings pages don't publish raw point projections - see
app.draft.scraper). The curve is a simple, transparent, monotonically
decreasing function of position rank, tuned so RB/WR point totals separate
slowly at the top (deep, flat positions) and QB/TE separate faster (thin at
the top) - a commonly used shape for redraft fantasy scoring, not a
substitute for a real weekly points model. Any row that already carries a
nonzero `projected_points` is left untouched.
"""
from __future__ import annotations

import math

import pandas as pd

# (top-of-position points, decay rate, points floor) - tuned for a Half-PPR
# baseline. points = floor + (top - floor) * exp(-decay * (position_rank - 1))
_CURVE_PARAMS: dict[str, tuple[float, float, float]] = {
    "QB": (410.0, 0.032, 130.0),
    "RB": (330.0, 0.045, 40.0),
    "WR": (310.0, 0.035, 45.0),
    "TE": (230.0, 0.060, 30.0),
    "K": (165.0, 0.020, 90.0),
    "DEF": (170.0, 0.020, 80.0),
}
_DEFAULT_CURVE = (250.0, 0.04, 40.0)


def _estimate_one(position: str, position_rank: int) -> float:
    top, decay, floor = _CURVE_PARAMS.get(position, _DEFAULT_CURVE)
    return floor + (top - floor) * math.exp(-decay * (position_rank - 1))


def estimate_points_from_rank(df: pd.DataFrame, adp_column: str = "adp") -> pd.DataFrame:
    """Return a copy of `df` with `projected_points` (and a `points_source`
    column) filled in wherever `projected_points` is missing or NaN, using
    each row's within-position rank by `adp_column`.
    """
    working = df.copy()
    if "projected_points" not in working.columns:
        working["projected_points"] = pd.NA
    if "points_source" not in working.columns:
        working["points_source"] = "scraped"

    needs_estimate = working["projected_points"].isna()
    if needs_estimate.any():
        position_rank = (
            working.loc[needs_estimate]
            .groupby("position")[adp_column]
            .rank(method="first")
            .astype(int)
        )
        estimated = [
            _estimate_one(pos, rank)
            for pos, rank in zip(working.loc[needs_estimate, "position"], position_rank)
        ]
        working.loc[needs_estimate, "projected_points"] = estimated
        working.loc[needs_estimate, "points_source"] = "estimated_from_adp"

    working["projected_points"] = working["projected_points"].astype(float)
    return working
