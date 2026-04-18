"""UI-agnostic setup backend with plan/apply execution."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path
from typing import cast
from uuid import uuid4

from loguru import logger

from prepmd.config.models import ProjectConfig
from prepmd.config.validators.pipeline import ValidationPipeline
from prepmd.core.config import CoreSimulationConfig
from prepmd.core.protocols import ProtocolStage, get_default_protocol
from prepmd.core.reporting import NullReporter, Reporter
from prepmd.engines.factory import EngineFactory
from prepmd.exceptions import SetupApplyError, SetupPlanError, StructureBuildError
from prepmd.models.results import RunResult, StepResult
from prepmd.structure.pdb_handler import PDBHandler
from prepmd.templates.protocol_templates import render_protocol_overview
from prepmd.templates.readme_templates import render_replica_readme

TOP_LEVEL_STRUCTURE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("01_input", ("structures", "parameters", "configs", "tleap_scripts")),
    ("02_scripts", ("preparation", "simulation", "analysis", "utilities")),
    ("03_logs", ("simulation", "analysis", "errors")),
    ("04_analysis_templates", ("trajectory_processing", "all_atom", "fluctuation_analysis", "summary")),
)
ANALYSIS_DIRS: tuple[str, ...] = ("trajectory", "all_atom", "fluctuation")
STATE_VERSION = 1
STATE_FILENAME = ".prepmd_state.json"
STEP_STATUS_VALUES = {"pending", "running", "done", "failed"}


@dataclass(slots=True, frozen=True)
class PlannedFile:
    """Static file write planned for setup."""

    path: Path
    content: str


@dataclass(slots=True, frozen=True)
class PlannedPrepareFile:
    """Engine-specific prepare file to generate during apply."""

    path: Path
    variant: str


@dataclass(frozen=True)
class SimulationPlan:
    """Deterministic filesystem plan built from configuration."""

    config: ProjectConfig
    root_dir: Path
    directories: tuple[Path, ...]
    files: tuple[PlannedFile, ...]
    prepare_files: tuple[PlannedPrepareFile, ...]

    @cached_property
    def total_steps(self) -> int:
        """Total apply operations in this plan."""
        return len(self.directories) + len(self.files) + len(self.prepare_files)


@dataclass(slots=True)
class SetupResult:
    """Result of running full setup workflow."""

    root_dir: Path
    result: RunResult


@dataclass(slots=True, frozen=True)
class PlannedOperation:
    """Single plan operation ready to execute during apply."""

    step_id: str
    message: str
    action: Callable[[], None]


class SetupStateStore:
    """Best-effort persisted state for resumable setup apply."""

    def __init__(self, state_path: Path, payload: dict[str, object]) -> None:
        self._state_path = state_path
        self._payload = payload

    @classmethod
    def create(
        cls,
        root_dir: Path,
        *,
        config_sha256: str,
        plan_sha256: str,
        resume: bool = False,
    ) -> SetupStateStore:
        root_dir.mkdir(parents=True, exist_ok=True)
        state_path = root_dir / STATE_FILENAME
        existing_payload = _load_state_payload(state_path)
        payload: dict[str, object]
        if resume and existing_payload is not None:
            _validate_resume_payload(existing_payload, config_sha256=config_sha256, plan_sha256=plan_sha256)
            payload = existing_payload
        else:
            payload = {
                "state_version": STATE_VERSION,
                "run_id": uuid4().hex,
                "created_at_utc": _utc_now_rfc3339(),
                "config_fingerprints": {
                    "config_sha256": config_sha256,
                    "plan_sha256": plan_sha256,
                },
                "steps": {},
            }
        state = cls(state_path=state_path, payload=payload)
        state.save_best_effort()
        return state

    def prepare_steps(self, step_ids: tuple[str, ...]) -> None:
        existing_steps = self._steps()
        normalized: dict[str, dict[str, object]] = {}
        for step_id in step_ids:
            existing = existing_steps.get(step_id, {})
            status_raw = existing.get("status")
            status = status_raw if isinstance(status_raw, str) and status_raw in STEP_STATUS_VALUES else "pending"
            item: dict[str, object] = {
                "status": status,
                "started_at_utc": existing.get("started_at_utc"),
                "finished_at_utc": existing.get("finished_at_utc"),
            }
            if "details" in existing:
                item["details"] = existing["details"]
            normalized[step_id] = item
        self._payload["steps"] = normalized
        self.save_best_effort()

    def is_done(self, step_id: str) -> bool:
        return self._steps().get(step_id, {}).get("status") == "done"

    def mark_running(self, step_id: str) -> None:
        now = _utc_now_rfc3339()
        step = self._steps().setdefault(step_id, {})
        step["status"] = "running"
        step["started_at_utc"] = now
        step["finished_at_utc"] = None
        step.pop("details", None)
        self.save_best_effort()

    def mark_done(self, step_id: str) -> None:
        now = _utc_now_rfc3339()
        step = self._steps().setdefault(step_id, {})
        step["status"] = "done"
        if step.get("started_at_utc") is None:
            step["started_at_utc"] = now
        step["finished_at_utc"] = now
        step.pop("details", None)
        self.save_best_effort()

    def mark_failed(self, step_id: str, error: BaseException) -> None:
        now = _utc_now_rfc3339()
        step = self._steps().setdefault(step_id, {})
        step["status"] = "failed"
        if step.get("started_at_utc") is None:
            step["started_at_utc"] = now
        step["finished_at_utc"] = now
        step["details"] = {"error": str(error)}
        self.save_best_effort()

    def save_best_effort(self) -> None:
        try:
            text = json.dumps(self._payload, indent=2, sort_keys=True)
            self._state_path.write_text(f"{text}\n", encoding="utf-8")
        except Exception as exc:
            logger.warning(f"Failed to persist setup state to {self._state_path}: {exc}")
            return

    def _steps(self) -> dict[str, dict[str, object]]:
        raw_steps_obj = self._payload.setdefault("steps", {})
        if not isinstance(raw_steps_obj, dict):
            raw_steps_obj = {}
            self._payload["steps"] = raw_steps_obj
        raw_steps = cast(dict[object, object], raw_steps_obj)
        typed_steps: dict[str, dict[str, object]] = {}
        for raw_key, raw_value in raw_steps.items():
            if isinstance(raw_key, str) and isinstance(raw_value, dict):
                typed_steps[raw_key] = cast(dict[str, object], raw_value)
        self._payload["steps"] = typed_steps
        return typed_steps


def build_plan(config: ProjectConfig) -> SimulationPlan:
    """Build deterministic project structure plan without filesystem side effects."""
    try:
        root_dir = Path(config.output_dir) / config.project_name
        engine = EngineFactory.create(config.engine.name)
        core_config = CoreSimulationConfig(
            target_temperature=config.simulation.temperature,
            production_runs=config.simulation.production_runs,
            production_run_length_ns=config.simulation.production_run_length_ns,
            force_field=config.engine.force_field,
            water_model=config.engine.water_model,
        )
        protocol = get_default_protocol(core_config)

        directories: list[Path] = [root_dir]
        files: list[PlannedFile] = []
        prepare_files: list[PlannedPrepareFile] = []

        for top_level, children in TOP_LEVEL_STRUCTURE:
            base = root_dir / top_level
            directories.append(base)
            for child in children:
                directories.append(base / child)

        sims_base = root_dir / "05_simulations"
        directories.append(sims_base)
        for variant in sorted(config.protein.variants):
            variant_dir = sims_base / variant
            directories.append(variant_dir)
            for replica_idx in range(1, config.simulation.replicas + 1):
                replica_num = f"{replica_idx:03d}"
                replica_dir = variant_dir / f"replica_{replica_num}"
                directories.append(replica_dir)

                _plan_protocol_directories(replica_dir, protocol, directories, files)
                analysis_base = replica_dir / "05_analysis"
                directories.append(analysis_base)
                for analysis_type in ANALYSIS_DIRS:
                    directories.append(analysis_base / analysis_type)
                directories.append(replica_dir / "06_backup")

                files.append(
                    PlannedFile(
                        replica_dir / "README.md",
                        render_replica_readme(config, variant, replica_num, engine.name),
                    )
                )
                files.append(PlannedFile(replica_dir / "PROTOCOL.md", render_protocol_overview(config)))
                prepare_files.append(PlannedPrepareFile(replica_dir / f"{engine.name}_prepare.in", variant=variant))

        sorted_directories = tuple(sorted(set(directories)))
        sorted_files = tuple(sorted(files, key=lambda planned: str(planned.path)))
        sorted_prepare_files = tuple(sorted(prepare_files, key=lambda planned: str(planned.path)))
        return SimulationPlan(
            config=config,
            root_dir=root_dir,
            directories=sorted_directories,
            files=sorted_files,
            prepare_files=sorted_prepare_files,
        )
    except Exception as exc:
        raise SetupPlanError(f"Failed to build setup plan: {exc}") from exc


def apply_plan(
    plan: SimulationPlan,
    reporter: Reporter | None = None,
    *,
    state_store: SetupStateStore | None = None,
    resume: bool = False,
) -> SetupResult:
    """Apply a deterministic setup plan to the filesystem."""
    active_reporter = reporter or NullReporter()
    step_results: list[StepResult] = []
    operations = _plan_operations(plan)
    current = 0
    total = len(operations)

    def advance(operation: PlannedOperation) -> None:
        nonlocal current
        current += 1
        active_reporter.on_step(current, total, operation.message)
        if resume and state_store is not None and state_store.is_done(operation.step_id):
            logger.bind(event="step_transition", step_id=operation.step_id, status="done", skipped=True).info(
                operation.message
            )
            step_results.append(
                StepResult(
                    name=operation.message,
                    success=True,
                    message="skipped(done)",
                    metadata={"step_id": operation.step_id, "status": "done"},
                )
            )
            return
        if state_store is not None:
            state_store.mark_running(operation.step_id)
        logger.bind(event="step_transition", step_id=operation.step_id, status="running").info(operation.message)
        try:
            operation.action()
            if state_store is not None:
                state_store.mark_done(operation.step_id)
            logger.bind(event="step_transition", step_id=operation.step_id, status="done").info(operation.message)
            step_results.append(
                StepResult(
                    name=operation.message,
                    success=True,
                    metadata={"step_id": operation.step_id, "status": "done"},
                )
            )
        except Exception as exc:
            if state_store is not None:
                state_store.mark_failed(operation.step_id, exc)
            logger.bind(event="step_transition", step_id=operation.step_id, status="failed").error(operation.message)
            step_results.append(
                StepResult(
                    name=operation.message,
                    success=False,
                    message=str(exc),
                    metadata={"step_id": operation.step_id, "status": "failed"},
                )
            )
            raise SetupApplyError(f"{operation.message}: {exc}") from exc

    try:
        active_reporter.on_start(total)
        if state_store is not None:
            state_store.prepare_steps(tuple(operation.step_id for operation in operations))
        for operation in operations:
            advance(operation)
    except Exception as exc:
        active_reporter.on_error(exc)
        raise StructureBuildError(str(exc)) from exc

    result = RunResult(steps=step_results)
    active_reporter.on_log(f"Project structure created at {plan.root_dir}")
    active_reporter.on_finish(result)
    return SetupResult(root_dir=plan.root_dir, result=result)


def run_setup(config: ProjectConfig, reporter: Reporter | None = None) -> SetupResult:
    """Validate, plan, and apply project setup."""
    ValidationPipeline().validate(config)
    plan = build_plan(config)
    return apply_plan(plan, reporter=reporter)


def _plan_operations(plan: SimulationPlan) -> tuple[PlannedOperation, ...]:
    operations: list[PlannedOperation] = []
    for directory in plan.directories:
        operations.append(
            PlannedOperation(
                step_id=f"mkdir::{directory}",
                message=f"mkdir {directory}",
                action=_mkdir_action(directory),
            )
        )
    for planned_file in plan.files:
        operations.append(
            PlannedOperation(
                step_id=f"write::{planned_file.path}",
                message=f"write {planned_file.path}",
                action=_write_file_action(planned_file),
            )
        )
    for prepare_file in render_prepare_files(plan):
        operations.append(
            PlannedOperation(
                step_id=f"prepare::{prepare_file.path}",
                message=f"write {prepare_file.path}",
                action=_write_prepare_action(prepare_file.path, prepare_file.content),
            )
        )
    return tuple(operations)


def render_prepare_files(plan: SimulationPlan, *, download_remote_pdb: bool = True) -> tuple[PlannedFile, ...]:
    """Render deterministic prepare-file contents for a plan."""
    engine = EngineFactory.create(plan.config.engine.name)
    shared_pdb_file = (
        _resolve_shared_pdb_file(plan.config) if download_remote_pdb else _resolve_plan_pdb_reference(plan.config)
    )
    rendered: list[PlannedFile] = []
    for prepare_file in plan.prepare_files:
        pdb_file = plan.config.protein.pdb_files.get(prepare_file.variant) or shared_pdb_file
        contents = engine.prepare_from_pdb(pdb_file, plan.config)
        rendered.append(PlannedFile(prepare_file.path, contents))
    return tuple(rendered)


def _plan_protocol_directories(
    replica_dir: Path,
    protocol: dict[str, list[ProtocolStage]],
    directories: list[Path],
    files: list[PlannedFile],
) -> None:
    for phase_name, stages in protocol.items():
        phase_dir = replica_dir / phase_name
        single_stage_same_name = len(stages) == 1 and stages[0].name == phase_name
        if single_stage_same_name:
            directories.append(phase_dir)
            files.append(PlannedFile(phase_dir / "README.md", _render_subdirectory_readme(stages[0].notes)))
            continue
        for stage in stages:
            stage_dir = phase_dir / stage.name
            directories.append(stage_dir)
            files.append(PlannedFile(stage_dir / "README.md", _render_subdirectory_readme(stage.notes)))


def _resolve_shared_pdb_file(config: ProjectConfig) -> str | None:
    protein = config.protein
    if protein.pdb_file is not None:
        return protein.pdb_file
    if protein.pdb_id is None:
        return None
    cache_dir = Path(protein.pdb_cache_dir) if protein.pdb_cache_dir is not None else None
    downloaded = PDBHandler(cache_dir=cache_dir).get_or_download(protein.pdb_id)
    return str(downloaded)


def _resolve_plan_pdb_reference(config: ProjectConfig) -> str | None:
    protein = config.protein
    if protein.pdb_file is not None:
        return protein.pdb_file
    if protein.pdb_id is not None:
        return f"pdb:{protein.pdb_id.upper()}"
    return None


def _render_subdirectory_readme(title: str) -> str:
    return f"# {title}\n\nGenerated by prepmd.\n"


def _mkdir_action(directory: Path) -> Callable[[], None]:
    def do_mkdir() -> None:
        directory.mkdir(parents=True, exist_ok=True)

    return do_mkdir


def _write_file_action(planned_file: PlannedFile) -> Callable[[], None]:
    def do_write() -> None:
        planned_file.path.write_text(planned_file.content, encoding="utf-8")

    return do_write


def _write_prepare_action(path: Path, contents: str) -> Callable[[], None]:
    def do_write() -> None:
        path.write_text(contents, encoding="utf-8")

    return do_write


def _utc_now_rfc3339() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_state_payload(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SetupApplyError(f"Failed to parse setup state file at {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise SetupApplyError(f"Invalid setup state file at {path}: expected JSON object")
    return cast(dict[str, object], loaded)


def _validate_resume_payload(payload: dict[str, object], *, config_sha256: str, plan_sha256: str) -> None:
    version = payload.get("state_version")
    if version != STATE_VERSION:
        raise SetupApplyError(
            f"Unsupported setup state version {version} (expected {STATE_VERSION}); use --overwrite to reset state."
        )
    run_id = payload.get("run_id")
    created_at = payload.get("created_at_utc")
    fingerprints = payload.get("config_fingerprints")
    if not isinstance(run_id, str) or not run_id:
        raise SetupApplyError("Invalid setup state file: missing run_id")
    if not isinstance(created_at, str) or not created_at:
        raise SetupApplyError("Invalid setup state file: missing created_at_utc")
    if not isinstance(fingerprints, dict):
        raise SetupApplyError("Invalid setup state file: missing config_fingerprints")
    typed_fingerprints = cast(dict[str, object], fingerprints)
    if typed_fingerprints.get("config_sha256") != config_sha256 or typed_fingerprints.get("plan_sha256") != plan_sha256:
        raise SetupApplyError("Existing setup state does not match current configuration; use --overwrite.")
