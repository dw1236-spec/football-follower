"""Core draft-analysis math: correlation, MAE, bust/value rates.

Bust/value rate methodology: for each position group we fit a scikit-learn
linear regression of log(total_points) on log(draft_rank), which gives a
smooth "expected points for this draft slot" curve for that position. A
player is a "bust" if their actual total_points falls more than
BUST_VALUE_THRESHOLD (20%) below that expected value, and a "value pick" if
they beat it by the same margin.

Superflex support: when `league_format="Superflex"`, `analyze()` adds extra
pooled rows to `position_metrics` (see `SUPERFLEX_POSITION_GROUPS`) - a
"FLEX" row over RB/WR/TE and a "SUPERFLEX" row over QB/RB/WR/TE. These reuse
the bust/value flags already computed per player's real position (each
position keeps its own expected-points curve; QBs and RBs score on very
different scales, so pooling the regression itself would be meaningless) and
simply aggregate correlation/MAE/bust/value across the pooled player set -
the group of players that actually competes for a single Flex/Superflex
roster slot.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

from app.logging_setup import get_logger
from app.schema import BUST_VALUE_THRESHOLD, SUPERFLEX_POSITION_GROUPS

MIN_ROWS_FOR_REGRESSION = 4
MIN_ROWS_FOR_CORRELATION = 3

OVERALL_LABEL = "ALL"


def _fit_expected_points(group: pd.DataFrame) -> pd.Series:
    """Return a per-row 'expected_points' series for this position group."""
    if len(group) < MIN_ROWS_FOR_REGRESSION or group["draft_rank"].nunique() < 2:
        return pd.Series(group["total_points"].mean(), index=group.index)

    x = np.log(group["draft_rank"].to_numpy(dtype=float)).reshape(-1, 1)
    y = np.log1p(group["total_points"].to_numpy(dtype=float))

    model = LinearRegression()
    model.fit(x, y)
    predicted_log = model.predict(x)
    expected = np.expm1(predicted_log)
    expected = np.clip(expected, a_min=0.0, a_max=None)
    return pd.Series(expected, index=group.index)


def add_expected_points_and_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Attach expected_points, bust, and value_pick columns per position group."""
    result = df.copy()
    result["expected_points"] = np.nan

    for _, group in result.groupby("position", group_keys=False):
        result.loc[group.index, "expected_points"] = _fit_expected_points(group)

    lower_bound = result["expected_points"] * (1 - BUST_VALUE_THRESHOLD)
    upper_bound = result["expected_points"] * (1 + BUST_VALUE_THRESHOLD)
    result["bust"] = result["total_points"] < lower_bound
    result["value_pick"] = result["total_points"] > upper_bound
    return result


def _safe_corr(x: pd.Series, y: pd.Series, method: str) -> float:
    if len(x) < MIN_ROWS_FOR_CORRELATION or x.nunique() < 2 or y.nunique() < 2:
        return float("nan")
    if method == "pearson":
        coeff, _ = stats.pearsonr(x, y)
    else:
        coeff, _ = stats.spearmanr(x, y)
    return float(coeff)


def _safe_mae(x: pd.Series, y: pd.Series) -> float:
    if len(x) == 0:
        return float("nan")
    return float(mean_absolute_error(x, y))


def _group_metrics_row(group: pd.DataFrame) -> dict[str, float]:
    return {
        "n": int(len(group)),
        "pearson": _safe_corr(group["draft_rank"], group["season_rank"], "pearson"),
        "spearman": _safe_corr(group["draft_rank"], group["season_rank"], "spearman"),
        "mae": _safe_mae(group["draft_rank"], group["season_rank"]),
        "bust_rate": float(group["bust"].mean()) if len(group) else float("nan"),
        "value_rate": float(group["value_pick"].mean()) if len(group) else float("nan"),
    }


@dataclass
class AnalysisResult:
    player_level: pd.DataFrame
    position_metrics: pd.DataFrame
    overall_metrics: pd.Series
    strongest_position: str | None
    weakest_position: str | None


def analyze(
    df: pd.DataFrame,
    selected_positions: set[str] | None = None,
    league_format: str = "Standard",
) -> AnalysisResult:
    """Run the full draft-analysis pipeline and return an AnalysisResult.

    `league_format="Superflex"` additionally appends pooled "FLEX" and
    "SUPERFLEX" rows to `position_metrics` (see module docstring); it never
    changes the real per-position rows or `player_level`.
    """
    logger = get_logger()
    working = df
    if selected_positions:
        working = working[working["position"].isin(selected_positions)]

    working = add_expected_points_and_flags(working)

    metric_columns = ["n", "pearson", "spearman", "mae", "bust_rate", "value_rate"]
    rows = {
        position: _group_metrics_row(group)
        for position, group in working.groupby("position")
    }
    position_metrics = pd.DataFrame.from_dict(rows, orient="index", columns=metric_columns)
    position_metrics.index.name = "position"
    position_metrics = position_metrics.sort_index()

    ranked = position_metrics["spearman"].dropna().abs().sort_values(ascending=False)
    strongest = ranked.index[0] if len(ranked) else None
    weakest = ranked.index[-1] if len(ranked) else None

    if league_format == "Superflex":
        for label, positions in SUPERFLEX_POSITION_GROUPS.items():
            group = working[working["position"].isin(positions)]
            if not group.empty:
                position_metrics.loc[label] = _group_metrics_row(group)
        position_metrics.index.name = "position"

    overall_metrics = pd.Series(_group_metrics_row(working), name=OVERALL_LABEL)

    logger.info(
        "Analysis complete for %d players across %d positions.",
        len(working), len(position_metrics),
    )

    return AnalysisResult(
        player_level=working,
        position_metrics=position_metrics,
        overall_metrics=overall_metrics,
        strongest_position=strongest,
        weakest_position=weakest,
    )
