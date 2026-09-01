"""Center Analysis Control Panel: position filters, Run Analysis, progress,
and Reset / Load New File.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QLabel,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.schema import POSITIONS


class EnterActivatedButton(QPushButton):
    """A QPushButton that activates on Enter/Return whenever it has focus,
    independent of Qt's dialog-only default-button mechanics."""

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.click()
            return
        super().keyPressEvent(event)


class ControlPanel(QWidget):
    run_requested = pyqtSignal()
    reset_requested = pyqtSignal()
    positions_changed = pyqtSignal(set)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        title = QLabel("2. Configure & Run")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        outer.addWidget(title)

        position_box = QGroupBox("Positions to Include")
        position_layout = QVBoxLayout(position_box)
        self._checkboxes: dict[str, QCheckBox] = {}
        for position in POSITIONS:
            checkbox = QCheckBox(position)
            checkbox.setChecked(True)
            checkbox.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            checkbox.stateChanged.connect(self._on_position_toggled)
            position_layout.addWidget(checkbox)
            self._checkboxes[position] = checkbox
        outer.addWidget(position_box)

        outer.addStretch(1)

        self.run_button = EnterActivatedButton("Run Analysis")
        self.run_button.setObjectName("RunButton")
        self.run_button.setMinimumHeight(56)
        self.run_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.run_button.setStyleSheet(
            "QPushButton#RunButton {"
            "  background-color: #1a73e8; color: white; font-size: 16px; font-weight: 700;"
            "  border-radius: 8px;"
            "}"
            "QPushButton#RunButton:disabled { background-color: #9db8e8; }"
            "QPushButton#RunButton:hover { background-color: #1558b0; }"
        )
        self.run_button.clicked.connect(self.run_requested.emit)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate / animated
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(18)

        self.status_label = QLabel("Validating data...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #555;")

        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)

        self.action_stack = QStackedWidget()
        self.action_stack.addWidget(self.run_button)
        self.action_stack.addWidget(progress_container)
        outer.addWidget(self.action_stack)

        self.reset_button = QPushButton("Reset / Load New File")
        self.reset_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.reset_button.clicked.connect(self.reset_requested.emit)
        outer.addWidget(self.reset_button)

    def _on_position_toggled(self) -> None:
        self.positions_changed.emit(self.selected_positions())

    def selected_positions(self) -> set[str]:
        return {pos for pos, box in self._checkboxes.items() if box.isChecked()}

    def set_selected_positions(self, positions: set[str]) -> None:
        for pos, box in self._checkboxes.items():
            box.blockSignals(True)
            box.setChecked(pos in positions)
            box.blockSignals(False)

    def set_running(self, running: bool) -> None:
        self.action_stack.setCurrentIndex(1 if running else 0)
        self.reset_button.setEnabled(True)

    def set_status(self, message: str) -> None:
        self.status_label.setText(message)

    def set_run_enabled(self, enabled: bool) -> None:
        self.run_button.setEnabled(enabled)

    def reset(self) -> None:
        for box in self._checkboxes.values():
            box.blockSignals(True)
            box.setChecked(True)
            box.blockSignals(False)
        self.set_running(False)
        self.set_status("Validating data...")
