import os

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.data.sample_template import build_sample_dataframe  # noqa: E402
from app.schema import REQUIRED_FIELD_NAMES  # noqa: E402


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return build_sample_dataframe()


@pytest.fixture
def messy_df() -> pd.DataFrame:
    """A DataFrame with renamed headers, bad rows, and duplicates."""
    return pd.DataFrame(
        {
            "Player": ["A", "B", "C", "D", "", "A"],
            "Pos": ["QB", "RB", "ZZ", "WR", "TE", "QB"],
            "ADP": [1, 2, 3, 400, 5, 1],
            "Games": [16, 15, 16, 16, 16, 16],
            "FPTS": [300.0, 250.0, 200.0, "oops", 150.0, 300.0],
            "PPG": [18.7, 16.6, 12.5, 9.0, 9.3, 18.7],
            "Final Rank": [2, 10, 5, 3, 40, 2],
        }
    )


@pytest.fixture
def required_columns() -> list[str]:
    return list(REQUIRED_FIELD_NAMES)
