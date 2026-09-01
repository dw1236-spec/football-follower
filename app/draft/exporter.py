"""Writes the final VOR draft board to an import-ready CSV or JSON file."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.draft.schema import DRAFT_BOARD_COLUMNS
from app.logging_setup import get_logger


class ExportFormatError(Exception):
    """Raised for an unsupported export file extension."""


def _board_view(vor_df: pd.DataFrame) -> pd.DataFrame:
    missing = set(DRAFT_BOARD_COLUMNS) - set(vor_df.columns)
    if missing:
        raise ValueError(f"vor_df is missing required column(s) for export: {sorted(missing)}")
    board = vor_df[list(DRAFT_BOARD_COLUMNS)].copy()
    board["vor"] = board["vor"].round(1)
    board["adp"] = board["adp"].round(1)
    board["projected_points"] = board["projected_points"].round(1)
    return board


def export_draft_board(vor_df: pd.DataFrame, destination: str | Path) -> Path:
    """Write the draft board to `destination`; format is inferred from the
    file extension (.csv or .json)."""
    destination = Path(destination)
    board = _board_view(vor_df)

    suffix = destination.suffix.lower()
    if suffix == ".csv":
        board.to_csv(destination, index=False)
    elif suffix == ".json":
        board.to_json(destination, orient="records", indent=2)
    else:
        raise ExportFormatError(f"Unsupported export format '{suffix}' - use .csv or .json.")

    get_logger().info("Exported draft board (%d players) to %s", len(board), destination)
    return destination
