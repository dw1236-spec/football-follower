import zipfile
from pathlib import Path

import pandas as pd

from app.analysis.metrics import analyze
from app.export import exporters
from app.visualization.charts import generate_all_charts


def test_export_summary_csv(tmp_path: Path, sample_df: pd.DataFrame):
    result = analyze(sample_df)
    dest = tmp_path / "summary.csv"
    exporters.export_summary_csv(result, dest)
    assert dest.exists()
    reloaded = pd.read_csv(dest, index_col=0)
    assert set(reloaded.index) == set(result.position_metrics.index)


def test_export_charts_zip(tmp_path: Path, sample_df: pd.DataFrame):
    result = analyze(sample_df)
    charts = generate_all_charts(result)
    dest = tmp_path / "charts.zip"
    exporters.export_charts_zip(charts, dest)
    assert dest.exists()
    with zipfile.ZipFile(dest) as zf:
        names = zf.namelist()
    for key in charts:
        assert f"{key}.png" in names


def test_export_markdown_report(tmp_path: Path, sample_df: pd.DataFrame):
    result = analyze(sample_df)
    dest = tmp_path / "report.md"
    exporters.export_markdown_report(result, "PPR", dest)
    content = dest.read_text(encoding="utf-8")
    assert "# NFL Fantasy Draft Analysis Report" in content
    assert "PPR" in content
    assert "## Recommendations" in content
