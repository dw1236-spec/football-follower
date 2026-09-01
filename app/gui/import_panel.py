"""Left Import Panel: drag-and-drop / browse, live preview, scoring toggle,
column mapping flow, and the sample-template download.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.data import column_mapping, ingestion, sample_template
from app.gui.mapping_dialog import ColumnMappingDialog
from app.gui.widgets import DropZoneWidget, EmptyStatePlaceholder, SkeletonLoader
from app.logging_setup import get_logger
from app.schema import REQUIRED_FIELD_NAMES, SCORING_SYSTEMS

PREVIEW_ROWS = 10


class ImportPanel(QWidget):
    data_loaded = pyqtSignal(object, dict, list, str)  # (clean_dataframe, mapping, warnings, path)
    error_occurred = pyqtSignal(str)
    scoring_system_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._logger = get_logger()
        self._flagged_rows: set[int] = set()
        self._current_path: str | None = None

        outer = QVBoxLayout(self)
        title = QLabel("1. Import Your Data")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        outer.addWidget(title)

        self.drop_zone = DropZoneWidget()
        self.drop_zone.file_selected.connect(self.load_file)
        self.drop_zone.invalid_file.connect(self.error_occurred.emit)
        outer.addWidget(self.drop_zone)

        template_row = QHBoxLayout()
        self.download_template_button = QPushButton("Download Sample Template")
        self.download_template_button.clicked.connect(self._download_template)
        template_row.addWidget(self.download_template_button)
        template_row.addStretch(1)
        outer.addLayout(template_row)

        scoring_box = QGroupBox("Scoring System")
        scoring_layout = QHBoxLayout(scoring_box)
        self.scoring_combo = QComboBox()
        self.scoring_combo.addItems(SCORING_SYSTEMS)
        self.scoring_combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.scoring_combo.currentTextChanged.connect(self.scoring_system_changed.emit)
        scoring_layout.addWidget(self.scoring_combo)
        outer.addWidget(scoring_box)

        preview_label = QLabel("Preview (first 10 rows)")
        preview_label.setStyleSheet("font-weight: 600; margin-top: 6px;")
        outer.addWidget(preview_label)

        self.preview_stack = QStackedWidget()
        self._empty_state = EmptyStatePlaceholder(
            "\U0001F4C4", "No file loaded yet.\nDrop a spreadsheet above to see a preview here."
        )
        self._skeleton = SkeletonLoader("Reading your file...")
        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.preview_table.customContextMenuRequested.connect(self._show_context_menu)

        self.preview_stack.addWidget(self._empty_state)
        self.preview_stack.addWidget(self._skeleton)
        self.preview_stack.addWidget(self.preview_table)
        self.preview_stack.setCurrentWidget(self._empty_state)
        outer.addWidget(self.preview_stack, stretch=1)

    # -- scoring system persistence -------------------------------------------------
    def set_scoring_system(self, value: str) -> None:
        self.scoring_combo.blockSignals(True)
        idx = self.scoring_combo.findText(value)
        if idx >= 0:
            self.scoring_combo.setCurrentIndex(idx)
        self.scoring_combo.blockSignals(False)

    # -- file loading flow -----------------------------------------------------------
    def load_file(self, path: str) -> None:
        self._current_path = path
        self.preview_stack.setCurrentWidget(self._skeleton)
        self._skeleton.start()
        QApplication.processEvents()
        QTimer.singleShot(0, lambda: self._load_file_impl(path))

    def _load_file_impl(self, path: str) -> None:
        try:
            raw_df = ingestion.load_dataframe(path)
        except ingestion.DataError as exc:
            self._skeleton.stop()
            self.preview_stack.setCurrentWidget(self._empty_state)
            self.error_occurred.emit(ingestion.friendly_message(exc))
            return
        except Exception as exc:  # noqa: BLE001
            self._skeleton.stop()
            self.preview_stack.setCurrentWidget(self._empty_state)
            self.error_occurred.emit(ingestion.friendly_message(exc))
            return

        mapping = column_mapping.suggest_mapping(list(raw_df.columns))
        if not column_mapping.is_mapping_complete(mapping):
            dialog = ColumnMappingDialog(list(raw_df.columns), mapping, parent=self)
            if dialog.exec():
                mapping = dialog.get_mapping()
            else:
                self._skeleton.stop()
                self.preview_stack.setCurrentWidget(self._empty_state)
                self.error_occurred.emit(
                    "Import cancelled - please match all required columns to continue."
                )
                return

        try:
            mapped_df = column_mapping.apply_mapping(raw_df, mapping)
            clean_df, report = column_mapping.validate_and_clean(mapped_df)
        except Exception as exc:  # noqa: BLE001
            self._skeleton.stop()
            self.preview_stack.setCurrentWidget(self._empty_state)
            self.error_occurred.emit(ingestion.friendly_message(exc))
            return

        if clean_df.empty:
            self._skeleton.stop()
            self.preview_stack.setCurrentWidget(self._empty_state)
            self.error_occurred.emit(
                "None of the rows in this file matched the expected format. "
                "Please check your data and try again."
            )
            return

        self._populate_preview(clean_df)
        self._skeleton.stop()
        self.preview_stack.setCurrentWidget(self.preview_table)
        self.data_loaded.emit(clean_df, mapping, report.warnings, path)

    def _populate_preview(self, df: pd.DataFrame) -> None:
        self._flagged_rows.clear()
        preview = df.head(PREVIEW_ROWS)
        self.preview_table.clear()
        self.preview_table.setColumnCount(len(REQUIRED_FIELD_NAMES))
        self.preview_table.setHorizontalHeaderLabels(REQUIRED_FIELD_NAMES)
        self.preview_table.setRowCount(len(preview))
        for row_idx, (_, row) in enumerate(preview.iterrows()):
            for col_idx, col in enumerate(REQUIRED_FIELD_NAMES):
                item = QTableWidgetItem(str(row[col]))
                self.preview_table.setItem(row_idx, col_idx, item)
        self.preview_table.resizeColumnsToContents()

    def _show_context_menu(self, position) -> None:
        row = self.preview_table.rowAt(position.y())
        if row < 0:
            return
        menu = QMenu(self)
        copy_action = menu.addAction("Copy row")
        flag_action = menu.addAction("Flag row as invalid")
        chosen = menu.exec(self.preview_table.viewport().mapToGlobal(position))
        if chosen == copy_action:
            self._copy_row(row)
        elif chosen == flag_action:
            self._flag_row(row)

    def _copy_row(self, row: int) -> None:
        values = [
            self.preview_table.item(row, col).text()
            if self.preview_table.item(row, col)
            else ""
            for col in range(self.preview_table.columnCount())
        ]
        QApplication.clipboard().setText("\t".join(values))

    def _flag_row(self, row: int) -> None:
        self._flagged_rows.add(row)
        for col in range(self.preview_table.columnCount()):
            item = self.preview_table.item(row, col)
            if item:
                item.setBackground(Qt.GlobalColor.red)
        self._logger.info("User flagged preview row %d as invalid", row)

    def reset(self) -> None:
        self._flagged_rows.clear()
        self._current_path = None
        self.preview_table.clear()
        self.preview_table.setRowCount(0)
        self.preview_stack.setCurrentWidget(self._empty_state)

    def _download_template(self) -> None:
        default_path = str(Path.home() / "sample_data_template.xlsx")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Sample Template", default_path, "Excel Workbook (*.xlsx)"
        )
        if not path:
            return
        try:
            sample_template.write_sample_template(path)
        except OSError as exc:
            self._logger.error("Failed to write sample template: %s", exc)
            self.error_occurred.emit("We couldn't save the sample template to that location.")
