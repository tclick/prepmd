import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from prepmd.config.models import ProjectConfig, ProteinConfig


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


def test_console_widget_backend_setup_progress_and_logs(tmp_path: Path) -> None:
    qt_widgets = pytest.importorskip("PyQt6.QtWidgets", exc_type=ImportError)
    from prepmd.gui import ConsoleWidget

    app = qt_widgets.QApplication.instance()
    if app is None:
        app = qt_widgets.QApplication([])

    progress_calls: list[tuple[int, int, str]] = []
    widget = ConsoleWidget()
    widget.set_progress_callback(lambda current, total, message: progress_calls.append((current, total, message)))

    cfg = ProjectConfig(
        project_name="gui-demo",
        output_dir=str(tmp_path),
        protein=ProteinConfig(pdb_file=str(tmp_path / "input.pdb")),
    )
    widget.run_backend_setup(cfg)

    text = widget.toPlainText()
    assert "Project created at" in text
    assert progress_calls


def test_console_widget_backend_lists_grouped_validation_errors(tmp_path: Path) -> None:
    qt_widgets = pytest.importorskip("PyQt6.QtWidgets", exc_type=ImportError)
    from prepmd.gui import ConsoleWidget

    app = qt_widgets.QApplication.instance()
    if app is None:
        app = qt_widgets.QApplication([])

    widget = ConsoleWidget()
    cfg = ProjectConfig(
        project_name="gui-invalid",
        output_dir=str(tmp_path),
        protein=ProteinConfig(pdb_file=str(tmp_path / "input.pdb")),
    )
    cfg.simulation.temperature = 1500.0
    cfg.simulation.replicas = 0
    widget.run_backend_setup(cfg)

    text = widget.toPlainText()
    assert "Validation errors" in text
    assert "temperature must be between 0 and 1000 K" in text
    assert "replicas must be >= 1" in text


def test_console_widget_run_prepare_cli_supports_variant_pdb_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    qt_widgets = pytest.importorskip("PyQt6.QtWidgets", exc_type=ImportError)
    from prepmd.gui import ConsoleWidget

    app = qt_widgets.QApplication.instance()
    if app is None:
        app = qt_widgets.QApplication([])

    captured: list[str] = []
    widget = ConsoleWidget()

    def fake_run_cli(arguments: list[str]) -> None:
        captured[:] = arguments

    monkeypatch.setattr(widget, "run_cli", fake_run_cli)

    widget.run_prepare_cli(
        project_name="gui-variant-ids",
        output_dir="/tmp/output",
        apo_pdb_id="1abc",
        holo_pdb_id="2xyz",
    )

    assert captured == [
        "prepare",
        "--project-name",
        "gui-variant-ids",
        "--output-dir",
        "/tmp/output",
        "--apo-pdb-id",
        "1abc",
        "--holo-pdb-id",
        "2xyz",
    ]
