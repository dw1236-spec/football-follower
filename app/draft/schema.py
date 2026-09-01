"""Schema for the forward-looking draft-assistant pipeline (projections,
VOR, tiers, exports) - a separate concern from app.schema, which models the
historical draft-vs-performance analyzer's ADP/season-results schema.
"""
from __future__ import annotations

# Position validity is shared with the historical draft analyzer -
# see app.schema.POSITIONS.

# Minimum columns a projections DataFrame must carry before compute_vor can
# run. `adp` is not required here - it's optional context passed through to
# the export, and it's what app.draft.projections.estimate_points_from_rank
# uses to fill in projected_points when a source doesn't publish real ones.
PROJECTION_REQUIRED_COLUMNS: tuple[str, ...] = (
    "player_name",
    "position",
    "team",
    "projected_points",
)

# Column order for the final import-ready draft board file.
DRAFT_BOARD_COLUMNS: tuple[str, ...] = (
    "player_name",
    "position",
    "team",
    "projected_points",
    "vor",
    "tier",
    "adp",
    "recommended_round",
)
