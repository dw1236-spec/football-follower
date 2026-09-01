"""Single-window dashboard: three-panel layout wired to a central AppState
via the Observer/callback pattern. This is the only window in the app -
no drawers, no secondary screens, tabbed navigation lives inside the
Results Panel only.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget

from app import config as config_module
from app.gui.analysis_worker import AnalysisWorker
from app.gui.control_panel import ControlPanel
from app.gui.import_panel import ImportPanel
from app.gui.results_panel import ResultsPanel
from app.gui.widgets import Banner
from app.logging_setup import get_logger
from app.state import StateStore

FOCUS_STYLESHEET = """
QPushButton:focus, QCheckBox:focus, QComboBox:focus, QLineEdit:focus {
    outline: none;
    border: 2px solid #1a73e8;
}
QMainWindow {
    background-color: #f7f8fa;
}
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._logger = get_logger()
        self._config = config_module.load_config()
        self._store = StateStore()
        self._worker: AnalysisWorker | None = None

        self.setWindowTitle("NFL Fantasy Draft Analyzer")
        self.resize(1440, 900)
        self.setMinimumSize(1280, 720)
        self.setStyleSheet(FOCUS_STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        outer_layout = QVBoxLayout(central)

        self.banner = Banner()
        outer_layout.addWidget(self.banner)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.import_panel = ImportPanel()
        self.control_panel = ControlPanel()
        self.results_panel = ResultsPanel()

        splitter.addWidget(self.import_panel)
        splitter.addWidget(self.control_panel)
        splitter.addWidget(self.results_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 4)
        outer_layout.addWidget(splitter, stretch=1)

        self.setTabOrder(self.import_panel.drop_zone.browse_button, self.import_panel.scoring_combo)

        self._wire_signals()
        self._restore_session()

    # -- wiring ----------------------------------------------------------------
    def _wire_signals(self) -> None:
        self.import_panel.data_loaded.connect(self._on_data_loaded)
        self.import_panel.error_occurred.connect(self.banner.show_error)
        self.import_panel.scoring_system_changed.connect(self._on_scoring_system_changed)

        self.control_panel.positions_changed.connect(self._on_positions_changed)
        self.control_panel.run_requested.connect(self._on_run_requested)
        self.control_panel.reset_requested.connect(self._on_reset_requested)

        self.results_panel.export_succeeded.connect(self.banner.show_success)
        self.results_panel.export_failed.connect(self.banner.show_error)
        self.results_panel.export_directory_changed.connect(self._on_export_directory_changed)

    def _restore_session(self) -> None:
        self.import_panel.set_scoring_system(self._config.get("scoring_system", "PPR"))
        self._store.update(scoring_system=self._config.get("scoring_system", "PPR"))

        positions = set(self._config.get("selected_positions") or [])
        if positions:
            self.control_panel.set_selected_positions(positions)
            self._store.update(selected_positions=positions)

        export_dir = self._config.get("export_directory")
        if export_dir:
            self.results_panel.set_export_directory(export_dir)
            self._store.update(export_directory=export_dir)

        last_file = self._config.get("last_file_path")
        if last_file and Path(last_file).exists():
            self.import_panel.load_file(last_file)

    def _persist_config(self) -> None:
        state = self._store.state
        config_module.save_config(
            {
                "last_file_path": state.loaded_file_path,
                "scoring_system": state.scoring_system,
                "selected_positions": sorted(state.selected_positions),
                "export_directory": state.export_directory,
                "window_geometry": None,
            }
        )

    # -- import panel handlers ---------------------------------------------------
    def _on_data_loaded(
        self, df: pd.DataFrame, mapping: dict, warnings: list[str], path: str
    ) -> None:
        self._store.update(
            raw_dataframe=df,
            mapped_columns=mapping,
            loaded_file_path=path,
        )
        self.control_panel.set_run_enabled(True)
        message = f"File loaded successfully ({len(df)} players)."
        if warnings:
            message += " " + " ".join(warnings[:3])
        self.banner.show_success(message)
        self._persist_config()

    def _on_scoring_system_changed(self, scoring_system: str) -> None:
        self._store.update(scoring_system=scoring_system)
        self.results_panel.set_scoring_system(scoring_system)
        self._persist_config()

    # -- control panel handlers ---------------------------------------------------
    def _on_positions_changed(self, positions: set[str]) -> None:
        self._store.update(selected_positions=positions)
        self._persist_config()

    def _on_run_requested(self) -> None:
        state = self._store.state
        if state.raw_dataframe is None or state.raw_dataframe.empty:
            self.banner.show_error("Please import a file before running an analysis.")
            return
        if not state.selected_positions:
            self.banner.show_error("Please select at least one position to analyze.")
            return

        self.banner.dismiss()
        self.control_panel.set_running(True)
        self.results_panel.show_loading()
        self._store.update(is_analyzing=True)

        self._worker = AnalysisWorker(state.raw_dataframe, set(state.selected_positions))
        self._worker.progress.connect(self.control_panel.set_status)
        self._worker.finished_ok.connect(self._on_analysis_finished)
        self._worker.failed.connect(self._on_analysis_failed)
        self._worker.start()

    def _on_analysis_finished(self, result, charts) -> None:
        self.control_panel.set_running(False)
        self.results_panel.display_results(result, charts)
        self._store.update(
            analysis_results={
                "position_metrics": result.position_metrics,
                "overall_metrics": result.overall_metrics,
            },
            is_analyzing=False,
        )
        self.banner.show_success("Analysis complete!")

    def _on_analysis_failed(self, message: str) -> None:
        self.control_panel.set_running(False)
        self.results_panel.show_empty()
        self._store.update(is_analyzing=False)
        self.banner.show_error(message)

    def _on_reset_requested(self) -> None:
        self._store.reset()
        self.import_panel.reset()
        self.control_panel.reset()
        self.results_panel.reset()
        self.banner.dismiss()
        self._persist_config()

    # -- export handlers ------------------------------------------------------------
    def _on_export_directory_changed(self, directory: str) -> None:
        self._store.update(export_directory=directory)
        self._persist_config()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._persist_config()
        super().closeEvent(event)
