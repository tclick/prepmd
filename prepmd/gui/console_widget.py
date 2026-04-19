"""Console widget for running and displaying CLI output."""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from typing import cast

from pydantic import ValidationError as PydanticValidationError
from PyQt6.QtCore import QByteArray, QProcess
from PyQt6.QtWidgets import QPlainTextEdit, QWidget

from prepmd.config.models import ProjectConfig
from prepmd.core.run import run_setup
from prepmd.exceptions import PrepMDError
from prepmd.models.results import RunResult

type ProgressCallback = Callable[[int, int, str], None]


class ConsoleWidget(QPlainTextEdit):
    """A read-only console widget that runs ``python -m prepmd.cli``."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self._process = QProcess(self)
        self._progress_callback: ProgressCallback | None = None
        self._process.readyReadStandardOutput.connect(self._on_stdout_ready)  # pyright: ignore[reportUnknownMemberType]
        self._process.readyReadStandardError.connect(self._on_stderr_ready)  # pyright: ignore[reportUnknownMemberType]
        self._process.finished.connect(self._on_process_finished)  # pyright: ignore[reportUnknownMemberType]

    @property
    def process(self) -> QProcess:
        """Return the underlying process."""
        return self._process

    def run_cli(self, arguments: Sequence[str]) -> None:
        """Start the prepmd CLI subprocess (fallback mode)."""
        if self._process.state() != QProcess.ProcessState.NotRunning:
            return

        command_arguments = ["-m", "prepmd.cli", *arguments]
        self.appendPlainText(f"$ {sys.executable} {' '.join(command_arguments)}")
        self._process.start(sys.executable, command_arguments)  # pyright: ignore[reportUnknownMemberType]

    def run_prepare_cli(
        self,
        *,
        project_name: str,
        output_dir: str | None = None,
        pdb_file: str | None = None,
        pdb_id: str | None = None,
        apo_pdb: str | None = None,
        holo_pdb: str | None = None,
        apo_pdb_id: str | None = None,
        holo_pdb_id: str | None = None,
        include_ions: bool | None = None,
        neutralize_protein: bool | None = None,
        ion_concentration: float | None = None,
        ion_cation: str | None = None,
        ion_anion: str | None = None,
    ) -> None:
        """Run ``prepmd prepare`` via CLI subprocess mode."""
        arguments: list[str] = ["prepare", "--project-name", project_name]
        if output_dir is not None:
            arguments.extend(["--output-dir", output_dir])
        if pdb_file is not None:
            arguments.extend(["--pdb-file", pdb_file])
        if pdb_id is not None:
            arguments.extend(["--pdb-id", pdb_id])
        if apo_pdb is not None:
            arguments.extend(["--apo-pdb", apo_pdb])
        if holo_pdb is not None:
            arguments.extend(["--holo-pdb", holo_pdb])
        if apo_pdb_id is not None:
            arguments.extend(["--apo-pdb-id", apo_pdb_id])
        if holo_pdb_id is not None:
            arguments.extend(["--holo-pdb-id", holo_pdb_id])
        if include_ions is not None:
            arguments.append("--include-ions" if include_ions else "--no-include-ions")
        if neutralize_protein is not None:
            arguments.append("--neutralize-protein" if neutralize_protein else "--no-neutralize-protein")
        if ion_concentration is not None:
            arguments.extend(["--ion-concentration", f"{ion_concentration}"])
        if ion_cation is not None:
            arguments.extend(["--ion-cation", ion_cation])
        if ion_anion is not None:
            arguments.extend(["--ion-anion", ion_anion])
        self.run_cli(arguments)

    def set_progress_callback(self, callback: ProgressCallback | None) -> None:
        """Set callback used to update a GUI progress bar."""
        self._progress_callback = callback

    def run_backend_setup(self, config: ProjectConfig) -> None:
        """Run shared backend directly and stream progress into the log panel."""
        self.appendPlainText("Running backend setup...")
        reporter = _QtReporter(self.appendPlainText, self._progress_callback)
        try:
            result = run_setup(config, reporter=reporter)
        except ExceptionGroup as exc:
            self.appendPlainText("Validation errors:")
            for line in _flatten_exception_group(exc):
                self.appendPlainText(f" - {line}")
            return
        except (PrepMDError, PydanticValidationError) as exc:
            self.appendPlainText(f"Error: {exc}")
            return
        self.appendPlainText(f"Project created at {result.root_dir}")

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


class _QtReporter:
    """Reporter that writes progress to Qt log and optional progress callback."""

    def __init__(
        self,
        logger: Callable[[str], None],
        progress_callback: ProgressCallback | None,
    ) -> None:
        self._logger = logger
        self._progress_callback = progress_callback

    def on_start(self, total_steps: int) -> None:
        if self._progress_callback is not None:
            self._progress_callback(0, total_steps, "Starting setup")

    def on_step(self, current_step: int, total_steps: int, message: str) -> None:
        self._logger(message)
        if self._progress_callback is not None:
            self._progress_callback(current_step, total_steps, message)

    def on_log(self, message: str) -> None:
        self._logger(message)

    def on_error(self, error: BaseException) -> None:
        self._logger(f"Error: {error}")

    def on_finish(self, result: RunResult) -> None:
        _ = result
        self._logger("Setup finished")


def _flatten_exception_group(exc: BaseExceptionGroup[BaseException]) -> list[str]:
    messages: list[str] = []
    for sub_exc in exc.exceptions:
        if isinstance(sub_exc, BaseExceptionGroup):
            messages.extend(_flatten_exception_group(cast(BaseExceptionGroup[BaseException], sub_exc)))
        else:
            messages.append(str(sub_exc))
    return messages
