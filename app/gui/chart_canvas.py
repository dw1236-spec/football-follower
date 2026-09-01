"""A matplotlib canvas embedded in the Qt GUI that expands full-screen on
double-click, per the interaction spec (no pop-up windows for normal viewing).
"""
from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout


class ClickableChartCanvas(FigureCanvasQTAgg):
    doubleClicked = pyqtSignal(object)

    def __init__(self, figure: Figure) -> None:
        super().__init__(figure)
        self.setMinimumHeight(320)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.doubleClicked.emit(self.figure)
        super().mouseDoubleClickEvent(event)


class FullScreenChartDialog(QDialog):
    def __init__(self, figure: Figure, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1100, 800)
        layout = QVBoxLayout(self)
        canvas = FigureCanvasQTAgg(figure)
        layout.addWidget(canvas)
        canvas.draw()
