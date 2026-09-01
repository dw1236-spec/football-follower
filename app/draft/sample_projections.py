"""Bundled offline ADP pool, used when scraping fails for any reason (see
app.draft.scraper.scrape_projections) and as a ready-to-run demo dataset for
the draft assistant CLI (`--offline`).

These are illustrative ADP estimates, not a live feed - real usage should
rely on a successful scrape. `projected_points` isn't included here: the
caller runs this through app.draft.projections.estimate_points_from_rank
the same way a real scrape without a points feed would be, so the fallback
path exercises the identical downstream code as production.
"""
from __future__ import annotations

import pandas as pd

# player_name, position, team, adp
_SAMPLE_ROWS: list[tuple[str, str, str, float]] = [
    ("Josh Allen", "QB", "BUF", 3.0),
    ("Patrick Mahomes", "QB", "KC", 5.0),
    ("Jalen Hurts", "QB", "PHI", 6.0),
    ("Lamar Jackson", "QB", "BAL", 8.0),
    ("Joe Burrow", "QB", "CIN", 14.0),
    ("Jayden Daniels", "QB", "WAS", 17.0),
    ("Justin Herbert", "QB", "LAC", 24.0),
    ("C.J. Stroud", "QB", "HOU", 26.0),
    ("Dak Prescott", "QB", "DAL", 30.0),
    ("Kyler Murray", "QB", "ARI", 60.0),
    ("Anthony Richardson", "QB", "IND", 65.0),
    ("Caleb Williams", "QB", "CHI", 70.0),
    ("Brock Purdy", "QB", "SF", 75.0),
    ("Jared Goff", "QB", "DET", 80.0),
    ("Trevor Lawrence", "QB", "JAC", 85.0),
    ("Tua Tagovailoa", "QB", "MIA", 90.0),
    ("Kirk Cousins", "QB", "ATL", 110.0),
    ("Bo Nix", "QB", "DEN", 120.0),
    ("Baker Mayfield", "QB", "TB", 125.0),
    ("Geno Smith", "QB", "SEA", 130.0),
    ("Christian McCaffrey", "RB", "SF", 1.0),
    ("Bijan Robinson", "RB", "ATL", 2.0),
    ("Breece Hall", "RB", "NYJ", 7.0),
    ("Jahmyr Gibbs", "RB", "DET", 9.0),
    ("Jonathan Taylor", "RB", "IND", 10.0),
    ("Saquon Barkley", "RB", "PHI", 11.0),
    ("De'Von Achane", "RB", "MIA", 15.0),
    ("Derrick Henry", "RB", "BAL", 16.0),
    ("Kyren Williams", "RB", "LAR", 18.0),
    ("Josh Jacobs", "RB", "GB", 20.0),
    ("James Cook", "RB", "BUF", 22.0),
    ("Travis Etienne", "RB", "JAC", 33.0),
    ("Alvin Kamara", "RB", "NO", 28.0),
    ("Isiah Pacheco", "RB", "KC", 35.0),
    ("Joe Mixon", "RB", "HOU", 38.0),
    ("Rachaad White", "RB", "TB", 42.0),
    ("Aaron Jones", "RB", "MIN", 44.0),
    ("Najee Harris", "RB", "PIT", 50.0),
    ("Tony Pollard", "RB", "TEN", 52.0),
    ("Rhamondre Stevenson", "RB", "NE", 58.0),
    ("Justin Jefferson", "WR", "MIN", 4.0),
    ("Ja'Marr Chase", "WR", "CIN", 12.0),
    ("CeeDee Lamb", "WR", "DAL", 13.0),
    ("Amon-Ra St. Brown", "WR", "DET", 19.0),
    ("Tyreek Hill", "WR", "MIA", 21.0),
    ("A.J. Brown", "WR", "PHI", 23.0),
    ("Puka Nacua", "WR", "LAR", 25.0),
    ("Garrett Wilson", "WR", "NYJ", 27.0),
    ("Nico Collins", "WR", "HOU", 29.0),
    ("Malik Nabers", "WR", "NYG", 31.0),
    ("Davante Adams", "WR", "LV", 32.0),
    ("Mike Evans", "WR", "TB", 34.0),
    ("Chris Olave", "WR", "NO", 36.0),
    ("DK Metcalf", "WR", "SEA", 37.0),
    ("Brandon Aiyuk", "WR", "SF", 39.0),
    ("Stefon Diggs", "WR", "HOU", 41.0),
    ("DJ Moore", "WR", "CHI", 43.0),
    ("Deebo Samuel", "WR", "SF", 45.0),
    ("Marvin Harrison Jr.", "WR", "ARI", 46.0),
    ("Drake London", "WR", "ATL", 47.0),
    ("Sam LaPorta", "TE", "DET", 48.0),
    ("Trey McBride", "TE", "ARI", 51.0),
    ("Travis Kelce", "TE", "KC", 49.0),
    ("Mark Andrews", "TE", "BAL", 53.0),
    ("George Kittle", "TE", "SF", 54.0),
    ("Evan Engram", "TE", "JAC", 68.0),
    ("Dallas Goedert", "TE", "PHI", 72.0),
    ("Kyle Pitts", "TE", "ATL", 78.0),
    ("Jake Ferguson", "TE", "DAL", 85.0),
    ("David Njoku", "TE", "CLE", 88.0),
    ("Justin Tucker", "K", "BAL", 145.0),
    ("Brandon Aubrey", "K", "DAL", 148.0),
    ("Harrison Butker", "K", "KC", 150.0),
    ("Jake Moody", "K", "SF", 155.0),
    ("San Francisco 49ers", "DEF", "SF", 140.0),
    ("Baltimore Ravens", "DEF", "BAL", 138.0),
    ("Dallas Cowboys", "DEF", "DAL", 142.0),
    ("Pittsburgh Steelers", "DEF", "PIT", 144.0),
]


def build_sample_projections() -> pd.DataFrame:
    return pd.DataFrame(_SAMPLE_ROWS, columns=["player_name", "position", "team", "adp"])
