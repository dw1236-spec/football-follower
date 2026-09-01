"""Turns AnalysisResult numbers into plain-language draft-strategy text."""
from __future__ import annotations

import pandas as pd

from app.analysis.metrics import AnalysisResult


def _fmt_pct(value: float) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{value * 100:.0f}%"


def _fmt_corr(value: float) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}"


def _top_pick_reliability(player_level: pd.DataFrame, position: str, top_n: int = 10) -> float | None:
    subset = player_level[
        (player_level["position"] == position) & (player_level["draft_rank"] <= top_n)
    ]
    if subset.empty:
        return None
    return float((~subset["bust"]).mean())


def build_recommendations(result: AnalysisResult) -> list[str]:
    """Return a list of plain-language recommendation sentences."""
    lines: list[str] = []
    metrics = result.position_metrics

    if result.strongest_position is not None:
        row = metrics.loc[result.strongest_position]
        lines.append(
            f"{result.strongest_position} is the most predictable position this season: "
            f"draft rank correlates strongly with final finish "
            f"(Spearman {_fmt_corr(row['spearman'])}), so ADP is a reliable guide there."
        )

    if result.weakest_position is not None:
        row = metrics.loc[result.weakest_position]
        lines.append(
            f"{result.weakest_position} is the hardest position to predict from ADP alone "
            f"(Spearman {_fmt_corr(row['spearman'])}) - consider spreading risk across "
            f"multiple {result.weakest_position} picks rather than committing early."
        )

    for position, row in metrics.iterrows():
        reliability = _top_pick_reliability(result.player_level, position)
        if reliability is not None:
            lines.append(
                f"{position}s drafted in the top 10 delivered within 20% of expected value "
                f"{_fmt_pct(reliability)} of the time this season."
            )

    sorted_by_bust = metrics["bust_rate"].dropna().sort_values(ascending=False)
    if len(sorted_by_bust):
        riskiest = sorted_by_bust.index[0]
        lines.append(
            f"{riskiest} carries the highest bust rate overall "
            f"({_fmt_pct(sorted_by_bust.iloc[0])} of picks underperformed by 20%+) - "
            "avoid overpaying for early-round certainty at this position."
        )

    sorted_by_value = metrics["value_rate"].dropna().sort_values(ascending=False)
    if len(sorted_by_value):
        best_value = sorted_by_value.index[0]
        lines.append(
            f"{best_value} offered the best chance of a value pick "
            f"({_fmt_pct(sorted_by_value.iloc[0])} of picks beat expectation by 20%+) - "
            "a good spot to look for late-round upside."
        )

    if not lines:
        lines.append("Not enough data to generate recommendations for the selected positions.")

    return lines
