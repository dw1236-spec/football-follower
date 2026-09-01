import pandas as pd
import pytest

from app.draft.projections import estimate_points_from_rank


def test_estimate_points_from_rank_fills_missing_points_only():
    df = pd.DataFrame(
        {
            "player_name": ["Has Real Points", "Needs Estimate 1", "Needs Estimate 2"],
            "position": ["QB", "QB", "QB"],
            "team": ["BUF", "KC", "PHI"],
            "adp": [3.0, 5.0, 40.0],
            "projected_points": [412.3, None, None],
        }
    )
    result = estimate_points_from_rank(df)

    assert result.loc[0, "projected_points"] == pytest.approx(412.3)
    assert result.loc[0, "points_source"] == "scraped"
    assert result.loc[1, "points_source"] == "estimated_from_adp"
    assert result.loc[2, "points_source"] == "estimated_from_adp"
    # better ADP (lower rank number) must estimate to more points
    assert result.loc[1, "projected_points"] > result.loc[2, "projected_points"]


def test_estimate_points_from_rank_adds_column_when_entirely_absent():
    df = pd.DataFrame(
        {
            "player_name": ["A", "B"],
            "position": ["RB", "RB"],
            "team": ["SF", "ATL"],
            "adp": [1.0, 2.0],
        }
    )
    result = estimate_points_from_rank(df)
    assert "projected_points" in result.columns
    assert (result["points_source"] == "estimated_from_adp").all()
    assert result["projected_points"].iloc[0] > result["projected_points"].iloc[1]


def test_estimate_points_from_rank_is_monotonically_decreasing_within_position():
    df = pd.DataFrame(
        {
            "player_name": [f"P{i}" for i in range(15)],
            "position": ["WR"] * 15,
            "team": ["DAL"] * 15,
            "adp": list(range(1, 16)),
        }
    )
    result = estimate_points_from_rank(df)
    points = result.sort_values("adp")["projected_points"].tolist()
    assert all(points[i] > points[i + 1] for i in range(len(points) - 1))


def test_estimate_points_from_rank_unknown_position_uses_default_curve():
    df = pd.DataFrame(
        {"player_name": ["Mystery"], "position": ["LB"], "team": ["DAL"], "adp": [50.0]}
    )
    result = estimate_points_from_rank(df)
    assert result.loc[0, "projected_points"] > 0
