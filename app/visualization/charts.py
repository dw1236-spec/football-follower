"""Matplotlib/seaborn figure builders for the Charts tab and export.

Figures are built with the object-oriented API (Figure/Axes directly,
no pyplot) so they can be embedded in the Qt canvas or saved headlessly
without depending on a global pyplot backend.
"""
from __future__ import annotations

import math

import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure

from app.analysis.metrics import AnalysisResult

sns.set_theme(style="whitegrid")

_POSITION_ORDER = ["QB", "RB", "WR", "TE", "K", "DEF"]


def _ordered_positions(present: list[str]) -> list[str]:
    return [p for p in _POSITION_ORDER if p in present] + sorted(
        p for p in present if p not in _POSITION_ORDER
    )


def scatter_draft_vs_season(player_level: pd.DataFrame) -> Figure:
    """Grid of scatter plots (draft rank vs season rank) - one per position."""
    positions = _ordered_positions(sorted(player_level["position"].unique()))
    n = max(len(positions), 1)
    n_cols = min(3, n)
    n_rows = math.ceil(n / n_cols)

    fig = Figure(figsize=(4.5 * n_cols, 4 * n_rows))
    for i, position in enumerate(positions, start=1):
        ax = fig.add_subplot(n_rows, n_cols, i)
        subset = player_level[player_level["position"] == position]
        colors = subset["bust"].map({True: "#d62728", False: "#2ca02c"})
        colors = colors.where(~subset["value_pick"], "#1f77b4")
        ax.scatter(subset["draft_rank"], subset["season_rank"], c=colors, alpha=0.75, edgecolors="none")
        max_rank = max(subset["draft_rank"].max(), subset["season_rank"].max(), 1)
        ax.plot([0, max_rank], [0, max_rank], linestyle="--", color="gray", linewidth=1)
        ax.set_title(position)
        ax.set_xlabel("Draft Rank")
        ax.set_ylabel("Season-End Rank")
        ax.invert_yaxis()
        ax.invert_xaxis()

    fig.suptitle("Draft Rank vs. Season-End Rank by Position")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return fig


def correlation_heatmap(position_metrics: pd.DataFrame) -> Figure:
    """Heatmap of Pearson/Spearman correlation coefficients across positions."""
    fig = Figure(figsize=(5.5, max(3, 0.6 * len(position_metrics) + 1.5)))
    ax = fig.add_subplot(111)
    data = position_metrics[["pearson", "spearman"]].reindex(
        _ordered_positions(list(position_metrics.index))
    )
    sns.heatmap(
        data,
        annot=True,
        fmt=".2f",
        cmap="RdYlGn",
        center=0,
        vmin=-1,
        vmax=1,
        cbar_kws={"label": "Correlation"},
        ax=ax,
    )
    ax.set_title("Draft Rank vs. Season Rank Correlation")
    ax.set_ylabel("Position")
    fig.tight_layout()
    return fig


def bust_value_bar_chart(position_metrics: pd.DataFrame) -> Figure:
    """Grouped bar chart comparing bust rate and value rate per position."""
    positions = _ordered_positions(list(position_metrics.index))
    data = position_metrics.reindex(positions)

    fig = Figure(figsize=(max(6, 1.2 * len(positions)), 4.5))
    ax = fig.add_subplot(111)
    x = range(len(positions))
    width = 0.35
    ax.bar([i - width / 2 for i in x], data["bust_rate"] * 100, width, label="Bust Rate %", color="#d62728")
    ax.bar([i + width / 2 for i in x], data["value_rate"] * 100, width, label="Value Rate %", color="#2ca02c")
    ax.set_xticks(list(x))
    ax.set_xticklabels(positions)
    ax.set_ylabel("Percent of Players")
    ax.set_title("Bust Rate vs. Value Rate by Position")
    ax.legend()
    fig.tight_layout()
    return fig


def generate_all_charts(result: AnalysisResult) -> dict[str, Figure]:
    """Build every chart the Charts tab / export needs, keyed by filename stem."""
    return {
        "draft_vs_season_scatter": scatter_draft_vs_season(result.player_level),
        "correlation_heatmap": correlation_heatmap(result.position_metrics),
        "bust_value_bar_chart": bust_value_bar_chart(result.position_metrics),
    }
