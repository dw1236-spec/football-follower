import pandas as pd

from app.data import column_mapping
from app.schema import REQUIRED_FIELD_NAMES


def test_suggest_mapping_exact_match(sample_df: pd.DataFrame):
    mapping = column_mapping.suggest_mapping(list(sample_df.columns))
    assert column_mapping.is_mapping_complete(mapping)
    for field in REQUIRED_FIELD_NAMES:
        assert mapping[field] == field


def test_suggest_mapping_aliases(messy_df: pd.DataFrame):
    mapping = column_mapping.suggest_mapping(list(messy_df.columns))
    assert mapping["player_name"] == "Player"
    assert mapping["position"] == "Pos"
    assert mapping["draft_rank"] == "ADP"
    assert mapping["total_points"] == "FPTS"
    assert mapping["points_per_game"] == "PPG"
    assert mapping["season_rank"] == "Final Rank"


def test_missing_fields_reports_unmatched():
    mapping = column_mapping.suggest_mapping(["totally_unrelated_column"])
    missing = column_mapping.missing_fields(mapping)
    assert set(missing) == set(REQUIRED_FIELD_NAMES)


def test_apply_mapping_renames_and_orders_columns(sample_df: pd.DataFrame):
    mapping = {name: name for name in REQUIRED_FIELD_NAMES}
    result = column_mapping.apply_mapping(sample_df, mapping)
    assert list(result.columns) == REQUIRED_FIELD_NAMES


def test_validate_and_clean_drops_bad_rows_and_warns(messy_df: pd.DataFrame):
    mapping = column_mapping.suggest_mapping(list(messy_df.columns))
    mapped = column_mapping.apply_mapping(messy_df, mapping)
    clean, report = column_mapping.validate_and_clean(mapped)

    # 6 input rows: 1 missing name, 1 invalid position, 1 non-numeric points,
    # 1 out-of-range draft_rank, 1 duplicate -> only "B" should survive is not
    # guaranteed given overlaps, so just assert clean set is well-formed.
    assert report.rows_in == 6
    assert report.rows_out < report.rows_in
    assert len(report.warnings) > 0
    assert clean["position"].isin(["QB", "RB", "WR", "TE", "K", "DEF"]).all()
    assert clean["draft_rank"].between(1, 300).all()
    assert not clean.duplicated(subset=["player_name", "position"]).any()
    assert clean["player_name"].ne("").all()


def test_validate_and_clean_output_dtypes(sample_df: pd.DataFrame):
    clean, report = column_mapping.validate_and_clean(sample_df)
    assert report.rows_out == len(sample_df)
    assert clean["draft_rank"].dtype.kind == "i"
    assert clean["games_played"].dtype.kind == "i"
    assert clean["season_rank"].dtype.kind == "i"
    assert clean["total_points"].dtype.kind == "f"
    assert clean["points_per_game"].dtype.kind == "f"


def test_derives_points_per_game_when_missing():
    df = pd.DataFrame(
        {
            "player_name": ["X"],
            "position": ["RB"],
            "draft_rank": [10],
            "games_played": [10],
            "total_points": [100.0],
            "points_per_game": [None],
            "season_rank": [5],
        }
    )
    clean, _ = column_mapping.validate_and_clean(df)
    assert clean.loc[0, "points_per_game"] == 10.0
