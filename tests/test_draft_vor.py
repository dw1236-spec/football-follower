import math

import pandas as pd
import pytest

from app.draft.settings import LeagueSettings, RosterSlots
from app.draft.vor import TierConfig, compute_replacement_ranks, compute_vor

STANDARD_LEAGUE = LeagueSettings(
    team_count=10,
    scoring="Half-PPR",
    superflex=False,
    roster=RosterSlots(superflex=0),
)
SUPERFLEX_LEAGUE = LeagueSettings(team_count=10, scoring="Half-PPR", superflex=True)


def _projections(rows: list[tuple[str, str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["player_name", "position", "team", "projected_points"])


# -- compute_replacement_ranks -------------------------------------------------


def test_replacement_ranks_match_hand_computed_values_for_default_league():
    ranks = compute_replacement_ranks(SUPERFLEX_LEAGUE)
    # QB: 1*10 dedicated + 0.75*10 superflex share = 17.5 -> ceil 18 + 1 = 19
    assert ranks["QB"] == 19
    # RB: 2*10 dedicated + (1/3)*10 flex + 0.10*10 superflex = 24.33 -> ceil 25 + 1 = 26
    assert ranks["RB"] == 26
    # K: 1*10 dedicated only, no flex/superflex eligibility -> 10 + 1 = 11
    assert ranks["K"] == 11


def test_superflex_pushes_qb_replacement_rank_far_deeper_than_standard():
    """This is the core Superflex-adjustment requirement: switching a
    league to Superflex must meaningfully increase QB scarcity demand
    (a deeper replacement rank) relative to a standard 1-QB league, while
    RB/WR/TE/K/DEF barely move."""
    standard_ranks = compute_replacement_ranks(STANDARD_LEAGUE)
    superflex_ranks = compute_replacement_ranks(SUPERFLEX_LEAGUE)

    assert standard_ranks["QB"] == 11  # 1*10 dedicated + 1
    assert superflex_ranks["QB"] > standard_ranks["QB"] + 5

    # Non-QB positions shouldn't be meaningfully affected by turning on
    # Superflex (only through the small RB/WR/TE superflex demand share).
    assert superflex_ranks["K"] == standard_ranks["K"]
    assert superflex_ranks["DEF"] == standard_ranks["DEF"]


def test_replacement_rank_never_drops_below_one():
    tiny_league = LeagueSettings(team_count=2, superflex=False, roster=RosterSlots(k=0, dst=0, superflex=0))
    ranks = compute_replacement_ranks(tiny_league)
    assert ranks["K"] == 1
    assert ranks["DEF"] == 1


# -- compute_vor ----------------------------------------------------------------


def test_compute_vor_matches_hand_computed_values():
    league = LeagueSettings(team_count=2, superflex=False, roster=RosterSlots(qb=1, rb=1, wr=0, te=0, flex=0, superflex=0, k=0, dst=0))
    # QB replacement rank = 1*2 + 1 = 3 -> 3rd-ranked QB's points
    df = _projections(
        [
            ("QB1", "QB", "AAA", 300.0),
            ("QB2", "QB", "BBB", 250.0),
            ("QB3", "QB", "CCC", 200.0),
            ("QB4", "QB", "DDD", 150.0),
        ]
    )
    result = compute_vor(df, league)
    by_name = result.set_index("player_name")
    assert by_name.loc["QB1", "replacement_points"] == pytest.approx(200.0)
    assert by_name.loc["QB1", "vor"] == pytest.approx(100.0)
    assert by_name.loc["QB3", "vor"] == pytest.approx(0.0)
    assert by_name.loc["QB4", "vor"] == pytest.approx(-50.0)


def test_compute_vor_replacement_rank_beyond_pool_uses_last_player():
    league = LeagueSettings(team_count=10, superflex=False, roster=RosterSlots(dst=0))
    df = _projections([("K1", "K", "AAA", 130.0), ("K2", "K", "BBB", 120.0)])
    result = compute_vor(df, league)
    # Replacement rank for K is 11, but only 2 Ks exist - falls back to the
    # worst available K rather than crashing or going out of bounds.
    assert (result["replacement_points"] == 120.0).all()


def test_compute_vor_overall_rank_and_recommended_round():
    league = LeagueSettings(team_count=4, superflex=False)
    df = _projections(
        [(f"P{i}", "WR", "AAA", 100.0 - i) for i in range(10)]
    )
    result = compute_vor(df, league)
    assert list(result["overall_vor_rank"]) == list(range(1, 11))
    # team_count=4: picks 1-4 => round 1, picks 5-8 => round 2, 9-10 => round 3
    assert list(result["recommended_round"]) == [1, 1, 1, 1, 2, 2, 2, 2, 3, 3]


def test_compute_vor_tiers_break_on_large_gaps():
    league = LeagueSettings(team_count=10, superflex=False)
    df = _projections(
        [
            ("Elite1", "RB", "AAA", 300.0),
            ("Elite2", "RB", "BBB", 295.0),
            ("Cliff", "RB", "CCC", 150.0),  # big drop -> new tier
            ("Cliff2", "RB", "DDD", 145.0),
        ]
        + [(f"Filler{i}", "RB", "ZZZ", 50.0 - i) for i in range(20)]
    )
    result = compute_vor(df, league, tier_config=TierConfig(drop_fraction=0.12))
    by_name = result.set_index("player_name")
    assert by_name.loc["Elite1", "tier"] == by_name.loc["Elite2", "tier"]
    assert by_name.loc["Cliff", "tier"] > by_name.loc["Elite2", "tier"]


def test_compute_vor_missing_required_column_raises():
    df = pd.DataFrame({"player_name": ["A"], "position": ["QB"]})
    with pytest.raises(ValueError):
        compute_vor(df, SUPERFLEX_LEAGUE)


def test_compute_vor_empty_dataframe_returns_empty_with_all_columns():
    df = pd.DataFrame(columns=["player_name", "position", "team", "projected_points"])
    result = compute_vor(df, SUPERFLEX_LEAGUE)
    assert result.empty
    for col in ("vor", "tier", "overall_vor_rank", "recommended_round", "replacement_points"):
        assert col in result.columns


def test_compute_vor_unknown_position_does_not_crash():
    df = _projections([("Mystery", "LB", "AAA", 100.0), ("QB1", "QB", "BBB", 300.0)])
    result = compute_vor(df, SUPERFLEX_LEAGUE)
    assert result.set_index("player_name").loc["Mystery", "vor"] == pytest.approx(100.0)


def test_superflex_qb_demand_share_sums_to_one():
    from app.draft.vor import SUPERFLEX_QB_DEMAND_SHARE

    assert math.isclose(sum(SUPERFLEX_QB_DEMAND_SHARE.values()), 1.0)
