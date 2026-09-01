"""Entry point for the NFL Fantasy Draft Analyzer desktop application."""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from app.gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("NFL Fantasy Draft Analyzer")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
