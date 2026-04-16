"""Result dataclasses for prepmd workflows."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class StepResult:
    """Result for an individual workflow step."""

    name: str
    success: bool
    message: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class RunResult:
    """Aggregate result for a full workflow run."""

    steps: list[StepResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return all(step.success for step in self.steps)
