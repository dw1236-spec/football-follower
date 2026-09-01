"""Shared, reusable GUI building blocks: banners, drop zone, skeleton loader,
and empty-state placeholders. Kept framework-idiomatic PyQt6 with no
business logic - callers wire signals to the AppState/StateStore.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


class DropZoneWidget(QFrame):
    """Drag-and-drop target with a Browse Files fallback button."""

    file_selected = pyqtSignal(str)
    invalid_file = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("DropZone")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(170)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("File drop zone")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        icon_label = QLabel("\U0001F4C1")
        icon_label.setStyleSheet("font-size: 40px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text_label = QLabel("Drop your Excel or CSV file here")
        self.text_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)

        sub_label = QLabel("Accepted formats: .xlsx, .xls, .csv")
        sub_label.setStyleSheet("color: #667085; font-size: 12px;")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.browse_button = QPushButton("Browse Files")
        self.browse_button.setObjectName("BrowseButton")
        self.browse_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.browse_button.clicked.connect(self._browse)

        layout.addWidget(icon_label)
        layout.addWidget(self.text_label)
        layout.addWidget(sub_label)
        layout.addSpacing(6)
        layout.addWidget(self.browse_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setStyleSheet(self._style(active=False))

    def _style(self, active: bool) -> str:
        border = "#2f80ed" if active else "#9aa5b1"
        bg = "#eaf2fe" if active else "#fafbfc"
        return f"""
            QFrame#DropZone {{
                border: 2px dashed {border};
                border-radius: 12px;
                background-color: {bg};
            }}
        """

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 - Qt override
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self._style(active=True))
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.setStyleSheet(self._style(active=False))

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 - Qt override
        self.setStyleSheet(self._style(active=False))
        urls = event.mimeData().urls()
        if urls:
            self._handle_path(urls[0].toLocalFile())

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self._browse()
        else:
            super().keyPressEvent(event)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a spreadsheet", "", "Spreadsheets (*.csv *.xlsx *.xls)"
        )
        if path:
            self._handle_path(path)

    def _handle_path(self, path: str) -> None:
        ext = Path(path).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            self.invalid_file.emit(
                f"'{ext or 'that file type'}' isn't supported. Please use a .csv, .xlsx, or .xls file."
            )
            return
        self.file_selected.emit(path)


class Banner(QWidget):
    """Dismissible top-of-window banner for error/success states."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setVisible(False)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 10, 10)

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("font-size: 13px;")

        self.dismiss_button = QPushButton("✕")
        self.dismiss_button.setFixedWidth(28)
        self.dismiss_button.setFlat(True)
        self.dismiss_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.dismiss_button.clicked.connect(self.dismiss)

        layout.addWidget(self.message_label, stretch=1)
        layout.addWidget(self.dismiss_button)

        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.dismiss)

    def show_error(self, message: str) -> None:
        self._auto_hide_timer.stop()
        self.setStyleSheet(
            "background-color: #fdecea; color: #611a15; border-radius: 6px;"
        )
        self.message_label.setText(f"⚠  {message}")
        self.setVisible(True)

    def show_success(self, message: str, auto_hide_ms: int = 4000) -> None:
        self.setStyleSheet(
            "background-color: #e6f4ea; color: #1e4620; border-radius: 6px;"
        )
        self.message_label.setText(f"✅  {message}")
        self.setVisible(True)
        if auto_hide_ms:
            self._auto_hide_timer.start(auto_hide_ms)

    def dismiss(self) -> None:
        self._auto_hide_timer.stop()
        self.setVisible(False)


class SkeletonLoader(QWidget):
    """A gentle pulsing placeholder bar shown while a panel is loading."""

    def __init__(self, text: str = "Loading...", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        self.bar = QFrame()
        self.bar.setFixedHeight(10)
        self.bar.setFixedWidth(220)
        self.bar.setStyleSheet("background-color: #cfd8dc; border-radius: 5px;")
        self._opacity_effect = QGraphicsOpacityEffect(self.bar)
        self.bar.setGraphicsEffect(self._opacity_effect)

        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #888; font-size: 13px;")

        layout.addWidget(self.bar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pulse)
        self._level = 0.3
        self._rising = True

    def _pulse(self) -> None:
        step = 0.08
        if self._rising:
            self._level = min(1.0, self._level + step)
            if self._level >= 1.0:
                self._rising = False
        else:
            self._level = max(0.3, self._level - step)
            if self._level <= 0.3:
                self._rising = True
        self._opacity_effect.setOpacity(self._level)

    def start(self, interval_ms: int = 60) -> None:
        self._timer.start(interval_ms)

    def stop(self) -> None:
        self._timer.stop()
        self._opacity_effect.setOpacity(1.0)

    def set_text(self, text: str) -> None:
        self.label.setText(text)


class EmptyStatePlaceholder(QWidget):
    """Instructional placeholder shown when there's no file/results yet."""

    def __init__(self, icon: str, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 44px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_label = QLabel(text)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setWordWrap(True)
        text_label.setStyleSheet("color: #888; font-size: 13px;")

        layout.addWidget(icon_label)
        layout.addWidget(text_label)
