from pathlib import Path

import pandas as pd

from app.draft.cli import run
from app.draft.schema import DRAFT_BOARD_COLUMNS


def test_run_offline_writes_import_ready_csv(tmp_path: Path, capsys):
    output = tmp_path / "board.csv"
    result_path = run(["--offline", "--output", str(output)])

    assert result_path == output
    assert output.exists()

    board = pd.read_csv(output)
    assert list(board.columns) == list(DRAFT_BOARD_COLUMNS)
    assert not board.empty
    assert board["position"].isin(["QB", "RB", "WR", "TE", "K", "DEF"]).all()

    captured = capsys.readouterr()
    assert "Top picks by position" in captured.out
    assert "10-team Half-PPR Superflex" in captured.out
    assert "Draft board written to" in captured.out


def test_run_offline_writes_json_when_output_ends_in_json(tmp_path: Path):
    output = tmp_path / "board.json"
    run(["--offline", "--output", str(output)])
    assert output.exists()
    board = pd.read_json(output)
    assert list(board.columns) == list(DRAFT_BOARD_COLUMNS)


def test_run_with_custom_config_reflects_settings(tmp_path: Path, capsys):
    config = tmp_path / "league.yaml"
    config.write_text("team_count: 12\nscoring: PPR\nsuperflex: false\nroster:\n  superflex: 0\n", encoding="utf-8")
    output = tmp_path / "board.csv"

    run(["--offline", "--config", str(config), "--output", str(output)])

    captured = capsys.readouterr()
    assert "12-team PPR draft board" in captured.out
    board = pd.read_csv(output).sort_values("vor", ascending=False).reset_index(drop=True)
    # round should be computed against 12 teams, not the 10-team default
    assert board.loc[11, "recommended_round"] == 1
    assert board.loc[12, "recommended_round"] == 2
