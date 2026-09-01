import json
from pathlib import Path

from app import config as config_module


def test_load_config_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.json")
    loaded = config_module.load_config()
    assert loaded == config_module.DEFAULT_CONFIG


def test_load_config_backfills_league_format_for_older_saved_files(tmp_path, monkeypatch):
    """A config saved before League Format existed shouldn't error or be
    missing the key - it should merge in the new default."""
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"scoring_system": "Half-PPR"}), encoding="utf-8")
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)

    loaded = config_module.load_config()
    assert loaded["scoring_system"] == "Half-PPR"
    assert loaded["league_format"] == "Standard"


def test_save_then_load_round_trips_league_format(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.json")

    config_module.save_config({**config_module.DEFAULT_CONFIG, "league_format": "Superflex"})
    loaded = config_module.load_config()
    assert loaded["league_format"] == "Superflex"
