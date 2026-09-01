import json

import pytest
import yaml

from app.draft.settings import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_LEAGUE_SETTINGS,
    LeagueConfigError,
    LeagueSettings,
    RosterSlots,
    load_league_settings,
    settings_to_dict,
)


def test_default_league_settings_match_spec():
    assert DEFAULT_LEAGUE_SETTINGS.team_count == 10
    assert DEFAULT_LEAGUE_SETTINGS.scoring == "Half-PPR"
    assert DEFAULT_LEAGUE_SETTINGS.superflex is True
    assert DEFAULT_LEAGUE_SETTINGS.roster == RosterSlots()


def test_bundled_config_file_matches_code_default():
    """The shipped config/league_settings.yaml must describe the same
    league as DEFAULT_LEAGUE_SETTINGS, or the CLI's --config-less default
    run and the documented example would silently disagree."""
    assert DEFAULT_CONFIG_PATH.exists()
    loaded = load_league_settings()
    assert loaded == DEFAULT_LEAGUE_SETTINGS


def test_load_league_settings_missing_default_path_falls_back(monkeypatch, tmp_path):
    monkeypatch.setattr("app.draft.settings.DEFAULT_CONFIG_PATH", tmp_path / "missing.yaml")
    assert load_league_settings() == DEFAULT_LEAGUE_SETTINGS


def test_load_league_settings_missing_explicit_path_raises(tmp_path):
    with pytest.raises(LeagueConfigError):
        load_league_settings(tmp_path / "does_not_exist.yaml")


def test_load_league_settings_from_yaml(tmp_path):
    path = tmp_path / "league.yaml"
    path.write_text(
        yaml.safe_dump({"team_count": 12, "scoring": "PPR", "superflex": False, "roster": {"qb": 1, "superflex": 0}}),
        encoding="utf-8",
    )
    settings = load_league_settings(path)
    assert settings.team_count == 12
    assert settings.scoring == "PPR"
    assert settings.superflex is False
    assert settings.roster.superflex == 0


def test_load_league_settings_from_json(tmp_path):
    path = tmp_path / "league.json"
    path.write_text(json.dumps({"team_count": 8}), encoding="utf-8")
    settings = load_league_settings(path)
    assert settings.team_count == 8
    assert settings.scoring == "Half-PPR"  # default carried through


def test_load_league_settings_unsupported_extension_raises(tmp_path):
    path = tmp_path / "league.txt"
    path.write_text("team_count: 10", encoding="utf-8")
    with pytest.raises(LeagueConfigError):
        load_league_settings(path)


def test_load_league_settings_malformed_yaml_raises(tmp_path):
    path = tmp_path / "league.yaml"
    path.write_text("team_count: [this is not valid: yaml", encoding="utf-8")
    with pytest.raises(LeagueConfigError):
        load_league_settings(path)


def test_load_league_settings_non_mapping_top_level_raises(tmp_path):
    path = tmp_path / "league.yaml"
    path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(LeagueConfigError):
        load_league_settings(path)


def test_load_league_settings_unknown_top_level_key_raises(tmp_path):
    path = tmp_path / "league.yaml"
    path.write_text(yaml.safe_dump({"team_count": 10, "not_a_real_setting": True}), encoding="utf-8")
    with pytest.raises(LeagueConfigError):
        load_league_settings(path)


def test_load_league_settings_unknown_roster_key_raises(tmp_path):
    path = tmp_path / "league.yaml"
    path.write_text(yaml.safe_dump({"roster": {"not_a_slot": 1}}), encoding="utf-8")
    with pytest.raises(LeagueConfigError):
        load_league_settings(path)


def test_invalid_scoring_value_raises():
    with pytest.raises(LeagueConfigError):
        LeagueSettings(scoring="Not A Real Scoring System")


def test_team_count_below_minimum_raises():
    with pytest.raises(LeagueConfigError):
        LeagueSettings(team_count=1)


def test_superflex_requires_a_superflex_roster_slot():
    with pytest.raises(LeagueConfigError):
        LeagueSettings(superflex=True, roster=RosterSlots(superflex=0))


def test_settings_to_dict_round_trips_key_values():
    as_dict = settings_to_dict(DEFAULT_LEAGUE_SETTINGS)
    assert as_dict["team_count"] == 10
    assert as_dict["roster"]["qb"] == 1
