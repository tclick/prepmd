"""GUI application entrypoint."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from prepmd.gui.console_widget import ConsoleWidget


def main() -> None:
    """Run the lightweight prepmd GUI console window."""
    app = QApplication.instance() or QApplication(sys.argv)
    widget = ConsoleWidget()
    widget.setWindowTitle("prepmd GUI")
    widget.resize(900, 600)
    widget.show()
    app.exec()
