import json
from pathlib import Path

import pandas as pd
import pytest

from app.draft.exporter import ExportFormatError, export_draft_board
from app.draft.schema import DRAFT_BOARD_COLUMNS


def _board_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "player_name": ["Josh Allen", "Christian McCaffrey"],
            "position": ["QB", "RB"],
            "team": ["BUF", "SF"],
            "projected_points": [412.345, 388.001],
            "vor": [122.567, 166.749],
            "tier": [1, 1],
            "adp": [3.21, 1.05],
            "recommended_round": [1, 1],
            "extra_internal_column": ["ignored", "ignored"],
        }
    )


def test_export_draft_board_csv_has_exact_required_columns(tmp_path: Path):
    dest = tmp_path / "board.csv"
    export_draft_board(_board_df(), dest)
    reloaded = pd.read_csv(dest)
    assert list(reloaded.columns) == list(DRAFT_BOARD_COLUMNS)
    assert reloaded.loc[0, "vor"] == pytest.approx(122.6)
    assert "extra_internal_column" not in reloaded.columns


def test_export_draft_board_json_has_exact_required_columns(tmp_path: Path):
    dest = tmp_path / "board.json"
    export_draft_board(_board_df(), dest)
    data = json.loads(dest.read_text(encoding="utf-8"))
    assert set(data[0].keys()) == set(DRAFT_BOARD_COLUMNS)
    assert data[1]["player_name"] == "Christian McCaffrey"


def test_export_draft_board_rounds_numeric_fields(tmp_path: Path):
    dest = tmp_path / "board.csv"
    export_draft_board(_board_df(), dest)
    reloaded = pd.read_csv(dest)
    assert reloaded.loc[1, "projected_points"] == pytest.approx(388.0)
    assert reloaded.loc[1, "adp"] == pytest.approx(1.0)


def test_export_draft_board_missing_column_raises(tmp_path: Path):
    incomplete = _board_df().drop(columns=["vor"])
    with pytest.raises(ValueError):
        export_draft_board(incomplete, tmp_path / "board.csv")


def test_export_draft_board_unsupported_extension_raises(tmp_path: Path):
    with pytest.raises(ExportFormatError):
        export_draft_board(_board_df(), tmp_path / "board.txt")


def test_export_draft_board_no_import_ready_file_needs_manual_edits(tmp_path: Path):
    """No player-facing column should ever be dropped or renamed to
    something a fantasy platform's import wizard wouldn't expect."""
    dest = tmp_path / "board.csv"
    export_draft_board(_board_df(), dest)
    header = dest.read_text(encoding="utf-8").splitlines()[0]
    for column in DRAFT_BOARD_COLUMNS:
        assert column in header
