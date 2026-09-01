import numpy as np
import pandas as pd
import pytest

from app.analysis.metrics import add_expected_points_and_flags, analyze
from app.schema import BUST_VALUE_THRESHOLD


def test_analyze_returns_expected_shape(sample_df: pd.DataFrame):
    result = analyze(sample_df)
    expected_positions = set(sample_df["position"].unique())
    assert set(result.position_metrics.index) == expected_positions
    assert list(result.position_metrics.columns) == [
        "n", "pearson", "spearman", "mae", "bust_rate", "value_rate",
    ]
    assert result.overall_metrics.name == "ALL"
    assert len(result.player_level) == len(sample_df)
    assert result.strongest_position in expected_positions
    assert result.weakest_position in expected_positions


def test_analyze_respects_position_filter(sample_df: pd.DataFrame):
    result = analyze(sample_df, selected_positions={"QB", "RB"})
    assert set(result.position_metrics.index) == {"QB", "RB"}
    assert set(result.player_level["position"].unique()) == {"QB", "RB"}


def test_perfect_correlation_is_one():
    df = pd.DataFrame(
        {
            "player_name": [f"P{i}" for i in range(10)],
            "position": ["RB"] * 10,
            "draft_rank": list(range(1, 11)),
            "games_played": [16] * 10,
            "total_points": [300 - i * 10 for i in range(10)],
            "points_per_game": [18.0] * 10,
            "season_rank": list(range(1, 11)),
        }
    )
    result = analyze(df)
    row = result.position_metrics.loc["RB"]
    assert row["pearson"] == pytest.approx(1.0, abs=1e-6)
    assert row["spearman"] == pytest.approx(1.0, abs=1e-6)
    assert row["mae"] == pytest.approx(0.0, abs=1e-6)


def test_bust_and_value_flags_use_threshold():
    df = pd.DataFrame(
        {
            "player_name": [f"P{i}" for i in range(6)],
            "position": ["WR"] * 6,
            "draft_rank": [10, 20, 30, 40, 50, 60],
            "games_played": [16] * 6,
            "total_points": [200, 190, 180, 170, 160, 150],
            "points_per_game": [12.5] * 6,
            "season_rank": [1, 2, 3, 4, 5, 6],
        }
    )
    flagged = add_expected_points_and_flags(df)
    assert not (flagged["bust"] & flagged["value_pick"]).any()

    lower = flagged["expected_points"] * (1 - BUST_VALUE_THRESHOLD)
    upper = flagged["expected_points"] * (1 + BUST_VALUE_THRESHOLD)
    assert (flagged.loc[flagged["bust"], "total_points"] < lower[flagged["bust"]]).all()
    assert (flagged.loc[flagged["value_pick"], "total_points"] > upper[flagged["value_pick"]]).all()


def test_small_group_falls_back_to_mean_without_crashing():
    df = pd.DataFrame(
        {
            "player_name": ["A", "B"],
            "position": ["K", "K"],
            "draft_rank": [100, 150],
            "games_played": [16, 16],
            "total_points": [120.0, 110.0],
            "points_per_game": [7.5, 6.9],
            "season_rank": [3, 5],
        }
    )
    flagged = add_expected_points_and_flags(df)
    assert np.isclose(flagged["expected_points"].iloc[0], flagged["expected_points"].iloc[1])


def test_standard_format_has_no_pooled_groups(sample_df: pd.DataFrame):
    result = analyze(sample_df, league_format="Standard")
    assert "FLEX" not in result.position_metrics.index
    assert "SUPERFLEX" not in result.position_metrics.index


def test_superflex_format_adds_pooled_groups(sample_df: pd.DataFrame):
    result = analyze(sample_df, league_format="Superflex")
    metrics = result.position_metrics
    assert "FLEX" in metrics.index
    assert "SUPERFLEX" in metrics.index

    real_positions = set(sample_df["position"].unique())
    assert set(metrics.index) == real_positions | {"FLEX", "SUPERFLEX"}

    flex_players = result.player_level[result.player_level["position"].isin(["RB", "WR", "TE"])]
    superflex_players = result.player_level[
        result.player_level["position"].isin(["QB", "RB", "WR", "TE"])
    ]
    assert metrics.loc["FLEX", "n"] == len(flex_players)
    assert metrics.loc["SUPERFLEX", "n"] == len(superflex_players)

    # strongest/weakest are chosen from real positions only, never a pooled group
    assert result.strongest_position in real_positions
    assert result.weakest_position in real_positions


def test_superflex_groups_omitted_when_no_eligible_players():
    df = pd.DataFrame(
        {
            "player_name": ["A", "B"],
            "position": ["K", "K"],
            "draft_rank": [140, 155],
            "games_played": [16, 16],
            "total_points": [148.0, 152.5],
            "points_per_game": [9.3, 9.5],
            "season_rank": [5, 3],
        }
    )
    result = analyze(df, league_format="Superflex")
    assert "FLEX" not in result.position_metrics.index
    assert "SUPERFLEX" not in result.position_metrics.index


def test_analyze_handles_empty_dataframe_gracefully():
    empty = pd.DataFrame(
        columns=[
            "player_name", "position", "draft_rank", "games_played",
            "total_points", "points_per_game", "season_rank",
        ]
    )
    result = analyze(empty)
    assert result.position_metrics.empty
    assert result.strongest_position is None
    assert result.weakest_position is None
