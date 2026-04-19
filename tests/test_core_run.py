from dataclasses import dataclass, field
from pathlib import Path

import pytest

from prepmd.config.models import ProjectConfig, ProteinConfig
from prepmd.config.validators.pipeline import ValidationPipeline
from prepmd.core.run import apply_plan, build_plan, run_setup
from prepmd.exceptions import ValidationErrorGroup


@dataclass(slots=True)
class RecordingReporter:
    starts: list[int] = field(default_factory=list)
    steps: list[tuple[int, int, str]] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    finished: int = 0

    def on_start(self, total_steps: int) -> None:
        self.starts.append(total_steps)

    def on_step(self, current_step: int, total_steps: int, message: str) -> None:
        self.steps.append((current_step, total_steps, message))

    def on_log(self, message: str) -> None:
        self.logs.append(message)

    def on_error(self, error: BaseException) -> None:
        self.errors.append(str(error))

    def on_finish(self, result: object) -> None:
        _ = result
        self.finished += 1


def _config(tmp_path: Path) -> ProjectConfig:
    return ProjectConfig(
        project_name="plan-demo",
        output_dir=str(tmp_path),
        protein=ProteinConfig(variants=["holo", "apo"], pdb_file=str(tmp_path / "input.pdb")),
    )


def test_build_plan_deterministic(tmp_path: Path) -> None:
    config = _config(tmp_path)
    first = build_plan(config)
    second = build_plan(config)
    assert first.directories == second.directories
    assert first.files == second.files
    assert first.prepare_files == second.prepare_files
    assert first.total_steps > 0


def test_apply_plan_creates_expected_output(tmp_path: Path) -> None:
    config = _config(tmp_path)
    plan = build_plan(config)
    reporter = RecordingReporter()
    setup_result = apply_plan(plan, reporter=reporter)
    assert setup_result.root_dir == tmp_path / "plan-demo"
    assert (setup_result.root_dir / "05_simulations" / "apo" / "replica_001" / "README.md").exists()
    assert (setup_result.root_dir / "05_simulations" / "holo" / "replica_001" / "amber_prepare.in").exists()
    assert reporter.starts == [plan.total_steps]
    assert reporter.finished == 1
    assert not reporter.errors


def test_run_setup_executes_plan_and_apply(tmp_path: Path) -> None:
    config = _config(tmp_path)
    reporter = RecordingReporter()
    setup_result = run_setup(config, reporter=reporter)
    assert setup_result.result.success
    assert reporter.steps
    assert setup_result.root_dir.exists()


def test_validation_pipeline_raises_exception_group_for_multiple_errors(tmp_path: Path) -> None:
    config = _config(tmp_path)
    bad_config = config.model_copy(deep=True)
    bad_config.simulation.temperature = 2000.0
    bad_config.simulation.replicas = 0
    with pytest.raises(ValidationErrorGroup) as exc_info:
        ValidationPipeline().validate(bad_config)
    messages = [str(error) for error in exc_info.value.exceptions]
    assert any("temperature must be between 0 and 1000 K" in msg for msg in messages)
    assert any("replicas must be >= 1" in msg for msg in messages)
