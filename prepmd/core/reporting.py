"""Reporter protocol and default implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from prepmd.models.results import RunResult


class Reporter(Protocol):
    """Receive progress and log events from setup execution."""

    def on_start(self, total_steps: int) -> None: ...

    def on_step(self, current_step: int, total_steps: int, message: str) -> None: ...

    def on_log(self, message: str) -> None: ...

    def on_error(self, error: BaseException) -> None: ...

    def on_finish(self, result: RunResult) -> None: ...


@dataclass(slots=True)
class NullReporter:
    """No-op reporter used when no UI/CLI reporter is provided."""

    def on_start(self, total_steps: int) -> None:
        _ = total_steps

    def on_step(self, current_step: int, total_steps: int, message: str) -> None:
        _ = (current_step, total_steps, message)

    def on_log(self, message: str) -> None:
        _ = message

    def on_error(self, error: BaseException) -> None:
        _ = error

    def on_finish(self, result: RunResult) -> None:
        _ = result
