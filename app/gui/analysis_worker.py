"""Background QThread that runs analysis + chart generation off the UI thread
so the window stays responsive, reporting progress via thread-safe signals.
"""
from __future__ import annotations

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from app.analysis.metrics import analyze
from app.logging_setup import get_logger
from app.visualization.charts import generate_all_charts


class AnalysisWorker(QThread):
    progress = pyqtSignal(str)
    finished_ok = pyqtSignal(object, object)  # (AnalysisResult, charts: dict[str, Figure])
    failed = pyqtSignal(str)

    def __init__(
        self,
        df: pd.DataFrame,
        selected_positions: set[str],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._df = df
        self._selected_positions = selected_positions

    def run(self) -> None:  # noqa: D102 - QThread override
        logger = get_logger()
        try:
            self.progress.emit("Validating data...")
            if self._df is None or self._df.empty:
                self.failed.emit("There's no data to analyze. Please import a file first.")
                return
            filtered = self._df[self._df["position"].isin(self._selected_positions)]
            if not self._selected_positions or filtered.empty:
                self.failed.emit(
                    "No players match the selected position filters. "
                    "Please select at least one position with data."
                )
                return

            self.progress.emit("Calculating correlations...")
            result = analyze(self._df, self._selected_positions)

            self.progress.emit("Generating charts...")
            charts = generate_all_charts(result)

            self.progress.emit("Done.")
            self.finished_ok.emit(result, charts)
        except Exception:  # noqa: BLE001 - translated to a friendly message
            logger.exception("Analysis failed")
            self.failed.emit(
                "Something went wrong while analyzing your data. "
                "Details were saved to the session log."
            )
