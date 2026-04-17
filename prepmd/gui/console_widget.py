"""Console widget for running and displaying CLI output."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from PyQt6.QtCore import QByteArray, QProcess
from PyQt6.QtWidgets import QPlainTextEdit, QWidget


class ConsoleWidget(QPlainTextEdit):
    """A read-only console widget that runs ``python -m prepmd.cli``."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self._process = QProcess(self)
        self._process.readyReadStandardOutput.connect(self._on_stdout_ready)  # pyright: ignore[reportUnknownMemberType]
        self._process.readyReadStandardError.connect(self._on_stderr_ready)  # pyright: ignore[reportUnknownMemberType]
        self._process.finished.connect(self._on_process_finished)  # pyright: ignore[reportUnknownMemberType]

    @property
    def process(self) -> QProcess:
        """Return the underlying process."""
        return self._process

    def run_cli(self, arguments: Sequence[str]) -> None:
        """Start the prepmd CLI with the provided command arguments."""
        if self._process.state() != QProcess.ProcessState.NotRunning:
            return

        command_arguments = ["-m", "prepmd.cli", *arguments]
        self.appendPlainText(f"$ {sys.executable} {' '.join(command_arguments)}")
        self._process.start(sys.executable, command_arguments)

    def stop_cli(self) -> None:
        """Stop the running CLI process, if any."""
        if self._process.state() == QProcess.ProcessState.NotRunning:
            return
        self._process.terminate()
        if not self._process.waitForFinished(3000):
            self._process.kill()

    def _on_stdout_ready(self) -> None:
        self._append_process_bytes(self._process.readAllStandardOutput())

    def _on_stderr_ready(self) -> None:
        self._append_process_bytes(self._process.readAllStandardError())

    def _on_process_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self.appendPlainText(f"\n[process exited with code {exit_code}]")

    def _append_process_bytes(self, data: QByteArray) -> None:
        text = data.data().decode("utf-8", errors="replace")
        if text:
            self.appendPlainText(text.rstrip("\n"))
