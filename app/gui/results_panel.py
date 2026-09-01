"""Right Results Panel: Summary / Charts / Export tabbed views."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.analysis.metrics import AnalysisResult
from app.analysis.recommendations import build_recommendations
from app.export import exporters
from app.gui.chart_canvas import ClickableChartCanvas, FullScreenChartDialog
from app.gui.widgets import EmptyStatePlaceholder, SkeletonLoader
from app.logging_setup import get_logger

SUMMARY_COLUMNS = [
    ("n", "Players"),
    ("pearson", "Pearson r"),
    ("spearman", "Spearman ρ"),
    ("mae", "MAE"),
    ("bust_rate", "Bust Rate"),
    ("value_rate", "Value Rate"),
]

CHART_TITLES = {
    "draft_vs_season_scatter": "Draft Rank vs. Season Rank",
    "correlation_heatmap": "Correlation Heatmap",
    "bust_value_bar_chart": "Bust Rate vs. Value Rate",
}


def _green_red(value: float, good_when_high: bool) -> QColor:
    if pd.isna(value):
        return QColor("#eeeeee")
    v = max(0.0, min(1.0, float(value)))
    score = v if good_when_high else (1 - v)
    red = int(255 * (1 - score))
    green = int(180 + 60 * score)
    return QColor(min(255, red + 60), min(255, green), 110)


class ResultsPanel(QWidget):
    export_succeeded = pyqtSignal(str)
    export_failed = pyqtSignal(str)
    export_directory_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._logger = get_logger()
        self._result: AnalysisResult | None = None
        self._charts: dict = {}
        self._scoring_system = "PPR"
        self._export_directory: str | None = None

        outer = QVBoxLayout(self)
        title = QLabel("3. Results")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        outer.addWidget(title)

        self.stack = QStackedWidget()
        self._empty_state = EmptyStatePlaceholder(
            "\U0001F4CA",
            "No results yet.\nImport a file and click Run Analysis to see insights here.",
        )
        self._skeleton = SkeletonLoader("Crunching the numbers...")
        self.tabs = QTabWidget()

        self._build_summary_tab()
        self._build_charts_tab()
        self._build_export_tab()

        self.stack.addWidget(self._empty_state)
        self.stack.addWidget(self._skeleton)
        self.stack.addWidget(self.tabs)
        self.stack.setCurrentWidget(self._empty_state)
        outer.addWidget(self.stack, stretch=1)

    # -- tab construction --------------------------------------------------------
    def _build_summary_tab(self) -> None:
        summary_widget = QWidget()
        layout = QVBoxLayout(summary_widget)

        self.summary_table = QTableWidget()
        self.summary_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.summary_table, stretch=2)

        rec_label = QLabel("Draft Strategy Recommendations")
        rec_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
        layout.addWidget(rec_label)

        self.recommendations_view = QTextEdit()
        self.recommendations_view.setReadOnly(True)
        layout.addWidget(self.recommendations_view, stretch=1)

        self.tabs.addTab(summary_widget, "Summary")

    def _build_charts_tab(self) -> None:
        charts_widget = QWidget()
        outer_layout = QVBoxLayout(charts_widget)
        hint = QLabel("Double-click any chart to expand it to full screen.")
        hint.setStyleSheet("color: #667085; font-size: 12px;")
        outer_layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._charts_container = QWidget()
        self._charts_layout = QVBoxLayout(self._charts_container)
        scroll.setWidget(self._charts_container)
        outer_layout.addWidget(scroll)

        self.tabs.addTab(charts_widget, "Charts")

    def _build_export_tab(self) -> None:
        export_widget = QWidget()
        layout = QVBoxLayout(export_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(12)

        info = QLabel("Export your results to a folder of your choosing.")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.export_csv_button = QPushButton("Export Summary as CSV")
        self.export_zip_button = QPushButton("Export All Charts (PNG .zip)")
        self.export_md_button = QPushButton("Export Markdown Report")
        for button in (self.export_csv_button, self.export_zip_button, self.export_md_button):
            button.setMinimumHeight(40)
            layout.addWidget(button)

        self.export_csv_button.clicked.connect(self._export_csv)
        self.export_zip_button.clicked.connect(self._export_zip)
        self.export_md_button.clicked.connect(self._export_markdown)

        self.tabs.addTab(export_widget, "Export")

    # -- public API ----------------------------------------------------------------
    def show_loading(self) -> None:
        self.stack.setCurrentWidget(self._skeleton)
        self._skeleton.start()

    def show_empty(self) -> None:
        self._skeleton.stop()
        self.stack.setCurrentWidget(self._empty_state)

    def set_export_directory(self, directory: str | None) -> None:
        self._export_directory = directory

    def set_scoring_system(self, scoring_system: str) -> None:
        self._scoring_system = scoring_system

    def display_results(self, result: AnalysisResult, charts: dict) -> None:
        self._skeleton.stop()
        self._result = result
        self._charts = charts
        self._populate_summary_table(result)
        self._populate_recommendations(result)
        self._populate_charts(charts)
        self.stack.setCurrentWidget(self.tabs)

    def reset(self) -> None:
        self._skeleton.stop()
        self._result = None
        self._charts = {}
        self.summary_table.clear()
        self.summary_table.setRowCount(0)
        self.recommendations_view.clear()
        self._clear_charts_layout()
        self.stack.setCurrentWidget(self._empty_state)

    # -- summary tab population ------------------------------------------------
    def _populate_summary_table(self, result: AnalysisResult) -> None:
        rows = list(result.position_metrics.iterrows()) + [
            ("ALL (Overall)", result.overall_metrics)
        ]
        headers = ["Position"] + [label for _, label in SUMMARY_COLUMNS]
        self.summary_table.setColumnCount(len(headers))
        self.summary_table.setHorizontalHeaderLabels(headers)
        self.summary_table.setRowCount(len(rows))

        for row_idx, (position, row) in enumerate(rows):
            self.summary_table.setItem(row_idx, 0, QTableWidgetItem(str(position)))
            for col_idx, (key, _label) in enumerate(SUMMARY_COLUMNS, start=1):
                value = row[key]
                text = "N/A" if pd.isna(value) else (
                    f"{value:.1%}" if key in ("bust_rate", "value_rate") else f"{value:.2f}"
                )
                item = QTableWidgetItem(text)
                if key in ("pearson", "spearman"):
                    item.setBackground(_green_red(abs(value) if not pd.isna(value) else value, good_when_high=True))
                elif key == "bust_rate":
                    item.setBackground(_green_red(value, good_when_high=False))
                elif key == "value_rate":
                    item.setBackground(_green_red(value, good_when_high=True))
                self.summary_table.setItem(row_idx, col_idx, item)

        self.summary_table.resizeColumnsToContents()

    def _populate_recommendations(self, result: AnalysisResult) -> None:
        lines = build_recommendations(result)
        html = "<ul>" + "".join(f"<li>{line}</li>" for line in lines) + "</ul>"
        self.recommendations_view.setHtml(html)

    # -- charts tab population ---------------------------------------------------
    def _clear_charts_layout(self) -> None:
        while self._charts_layout.count():
            item = self._charts_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _populate_charts(self, charts: dict) -> None:
        self._clear_charts_layout()
        for key, figure in charts.items():
            title = CHART_TITLES.get(key, key)
            label = QLabel(title)
            label.setStyleSheet("font-weight: 600; margin-top: 10px;")
            self._charts_layout.addWidget(label)

            canvas = ClickableChartCanvas(figure)
            canvas.doubleClicked.connect(
                lambda fig, t=title: self._expand_chart(fig, t)
            )
            self._charts_layout.addWidget(canvas)
            canvas.draw()
        self._charts_layout.addStretch(1)

    def _expand_chart(self, figure, title: str) -> None:
        dialog = FullScreenChartDialog(figure, title, parent=self)
        dialog.exec()

    # -- export tab actions --------------------------------------------------------
    def _choose_save_path(self, default_name: str, file_filter: str) -> str | None:
        start_dir = self._export_directory or str(Path.home())
        path, _ = QFileDialog.getSaveFileName(
            self, "Choose where to save", str(Path(start_dir) / default_name), file_filter
        )
        if path:
            self._export_directory = str(Path(path).parent)
            self.export_directory_changed.emit(self._export_directory)
        return path or None

    def _export_csv(self) -> None:
        if self._result is None:
            self.export_failed.emit("Run an analysis before exporting results.")
            return
        path = self._choose_save_path("summary.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            exporters.export_summary_csv(self._result, path)
            self.export_succeeded.emit(f"Summary exported to {path}")
        except OSError as exc:
            self._logger.error("CSV export failed: %s", exc)
            self.export_failed.emit("We couldn't save the CSV file to that location.")

    def _export_zip(self) -> None:
        if not self._charts:
            self.export_failed.emit("Run an analysis before exporting charts.")
            return
        path = self._choose_save_path("charts.zip", "Zip Archive (*.zip)")
        if not path:
            return
        try:
            exporters.export_charts_zip(self._charts, path)
            self.export_succeeded.emit(f"Charts exported to {path}")
        except OSError as exc:
            self._logger.error("Chart export failed: %s", exc)
            self.export_failed.emit("We couldn't save the chart archive to that location.")

    def _export_markdown(self) -> None:
        if self._result is None:
            self.export_failed.emit("Run an analysis before exporting a report.")
            return
        path = self._choose_save_path("report.md", "Markdown Files (*.md)")
        if not path:
            return
        try:
            exporters.export_markdown_report(self._result, self._scoring_system, path)
            self.export_succeeded.emit(f"Report exported to {path}")
        except OSError as exc:
            self._logger.error("Markdown export failed: %s", exc)
            self.export_failed.emit("We couldn't save the report to that location.")
