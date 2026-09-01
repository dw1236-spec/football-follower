"""One-click export helpers for the Export tab: CSV, PNG zip, Markdown report."""
from __future__ import annotations

import io
import zipfile
from datetime import datetime
from pathlib import Path

from matplotlib.figure import Figure

from app.analysis.metrics import AnalysisResult
from app.analysis.recommendations import build_recommendations
from app.logging_setup import get_logger


def export_summary_csv(result: AnalysisResult, destination: str | Path) -> Path:
    destination = Path(destination)
    result.position_metrics.to_csv(destination, index=True)
    get_logger().info("Exported summary CSV to %s", destination)
    return destination


def export_charts_zip(charts: dict[str, Figure], destination: str | Path) -> Path:
    destination = Path(destination)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, fig in charts.items():
            buffer = io.BytesIO()
            fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
            zf.writestr(f"{name}.png", buffer.getvalue())
    get_logger().info("Exported %d charts to %s", len(charts), destination)
    return destination


def export_markdown_report(
    result: AnalysisResult,
    scoring_system: str,
    destination: str | Path,
) -> Path:
    destination = Path(destination)
    lines: list[str] = []
    lines.append("# NFL Fantasy Draft Analysis Report")
    lines.append("")
    lines.append(f"_Generated {datetime.now():%Y-%m-%d %H:%M}_ | Scoring: **{scoring_system}**")
    lines.append("")
    lines.append("## Position Summary")
    lines.append("")
    lines.append(result.position_metrics.round(3).to_markdown())
    lines.append("")
    lines.append("## Overall")
    lines.append("")
    lines.append(result.overall_metrics.round(3).to_markdown())
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for rec in build_recommendations(result):
        lines.append(f"- {rec}")
    lines.append("")

    destination.write_text("\n".join(lines), encoding="utf-8")
    get_logger().info("Exported Markdown report to %s", destination)
    return destination
