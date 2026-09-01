import pandas as pd

from app.analysis.metrics import analyze
from app.analysis.recommendations import build_recommendations


def test_recommendations_mention_superflex_pools_in_superflex_format(sample_df: pd.DataFrame):
    result = analyze(sample_df, league_format="Superflex")
    lines = " ".join(build_recommendations(result))
    assert "Superflex-eligible" in lines
    assert "Flex pool" in lines


def test_recommendations_omit_superflex_pools_in_standard_format(sample_df: pd.DataFrame):
    result = analyze(sample_df, league_format="Standard")
    lines = " ".join(build_recommendations(result))
    assert "Superflex-eligible" not in lines
    assert "Flex pool" not in lines


def test_recommendations_never_name_a_pooled_group_as_riskiest_or_best_value(
    sample_df: pd.DataFrame,
):
    result = analyze(sample_df, league_format="Superflex")
    lines = build_recommendations(result)
    for line in lines:
        if "highest bust rate overall" in line or "best chance of a value pick" in line:
            assert not line.startswith("FLEX")
            assert not line.startswith("SUPERFLEX")


def test_recommendations_handle_no_data_gracefully():
    empty = pd.DataFrame(
        columns=[
            "player_name", "position", "draft_rank", "games_played",
            "total_points", "points_per_game", "season_rank",
        ]
    )
    result = analyze(empty)
    lines = build_recommendations(result)
    assert lines == ["Not enough data to generate recommendations for the selected positions."]
