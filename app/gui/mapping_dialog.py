"""Friendly column-mapping dialog shown when auto-detection can't match
every required schema field to a column in the user's spreadsheet.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)

from app.schema import REQUIRED_FIELDS


class ColumnMappingDialog(QDialog):
    def __init__(
        self,
        columns: list[str],
        suggested: dict[str, str | None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Match Your Columns")
        self.setMinimumWidth(440)
        self._combo_boxes: dict[str, QComboBox] = {}

        layout = QVBoxLayout(self)

        intro = QLabel(
            "We couldn't automatically match every column in your file. "
            "Tell us which of your spreadsheet's columns corresponds to each "
            "field below, then click OK."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        for schema_field in REQUIRED_FIELDS:
            combo = QComboBox()
            combo.setFocusPolicy(combo.focusPolicy())
            combo.addItem("-- Select column --", None)
            for col in columns:
                combo.addItem(str(col), col)
            guess = suggested.get(schema_field.name)
            if guess:
                idx = combo.findData(guess)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            form.addRow(f"{schema_field.label}:", combo)
            self._combo_boxes[schema_field.name] = combo
        layout.addLayout(form)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #b3261e; font-size: 12px;")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_mapping(self) -> dict[str, str]:
        return {
            name: combo.currentData()
            for name, combo in self._combo_boxes.items()
            if combo.currentData()
        }

    def _on_accept(self) -> None:
        mapping = self.get_mapping()
        missing = [f.label for f in REQUIRED_FIELDS if f.name not in mapping]
        if missing:
            self._status_label.setText(
                "Please choose a column for: " + ", ".join(missing)
            )
            return
        self.accept()
