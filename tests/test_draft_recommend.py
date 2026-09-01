import logging

import pandas as pd
import pytest

from app.draft.recommend import RosterState, recommend_pick


def _pool() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "player_name": ["Elite RB", "Great QB", "Good WR", "Best K", "Backup K"],
            "position": ["RB", "QB", "WR", "K", "K"],
            "team": ["SF", "BUF", "DAL", "BAL", "KC"],
            "projected_points": [330.0, 400.0, 300.0, 150.0, 140.0],
            "vor": [180.0, 175.0, 150.0, 40.0, 30.0],
            "replacement_points": [150.0, 225.0, 150.0, 110.0, 110.0],
        }
    )


def test_recommend_pick_selects_highest_vor():
    rec = recommend_pick(_pool(), RosterState())
    assert rec is not None
    assert rec.player_name == "Elite RB"
    assert rec.vor == pytest.approx(180.0)
    assert "Highest available VOR" in rec.reasoning


def test_recommend_pick_respects_default_roster_caps():
    """Even though 'Best K' has real VOR, a team that already has a K
    should never be told to draft a second one under default caps."""
    roster = RosterState(counts={"RB": 5, "QB": 5, "WR": 5, "K": 1})
    rec = recommend_pick(_pool(), roster)
    assert rec is not None
    assert rec.position != "K"


def test_recommend_pick_honors_custom_roster_caps():
    roster = RosterState(counts={"QB": 3})
    rec = recommend_pick(_pool(), roster, roster_caps={"QB": 2})
    assert rec is not None
    assert rec.position != "QB"


def test_recommend_pick_returns_none_when_everything_is_capped_out():
    pool = _pool()[lambda df: df["position"] == "K"]
    roster = RosterState(counts={"K": 1})
    assert recommend_pick(pool, roster) is None


def test_recommend_pick_returns_none_for_empty_pool():
    empty = pd.DataFrame(columns=["player_name", "position", "team", "projected_points", "vor", "replacement_points"])
    assert recommend_pick(empty, RosterState()) is None


def test_roster_state_tracks_counts():
    state = RosterState()
    assert state.count("RB") == 0
    state.add("RB")
    state.add("RB")
    assert state.count("RB") == 2
    assert state.count("WR") == 0


def test_recommend_pick_dry_run_logs_vor_and_replacement_baseline(caplog):
    caplog.set_level(logging.INFO, logger="nfl_draft_analyzer")
    recommend_pick(_pool(), RosterState(), dry_run=True)
    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert "Dry-run" in messages
    assert "Elite RB" in messages
    assert "VOR=180.0" in messages
    assert "replacement=150.0" in messages
