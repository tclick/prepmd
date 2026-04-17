import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


def test_console_widget_runs_prepmd_cli_license() -> None:
    qt_core = pytest.importorskip("PyQt6.QtCore", exc_type=ImportError)
    qt_widgets = pytest.importorskip("PyQt6.QtWidgets", exc_type=ImportError)
    from prepmd.gui import ConsoleWidget

    app = qt_widgets.QApplication.instance()
    if app is None:
        app = qt_widgets.QApplication([])

    widget = ConsoleWidget()

    widget.run_cli(["license"])

    loop = qt_core.QEventLoop()
    timer = qt_core.QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)  # pyright: ignore[reportUnknownMemberType]
    widget.process.finished.connect(loop.quit)  # pyright: ignore[reportUnknownMemberType]
    timer.start(10_000)
    loop.exec()

    assert widget.process.state() == qt_core.QProcess.ProcessState.NotRunning
    output = widget.toPlainText()
    assert "prepmd.cli license" in output
    assert "GNU GPL-3.0-or-later" in output
    assert "[process exited with code 0]" in output
