"""UI-agnostic setup backend with plan/apply execution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

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

        sorted_directories = tuple(sorted(set(directories), key=lambda path: str(path)))
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


def apply_plan(plan: SimulationPlan, reporter: Reporter | None = None) -> SetupResult:
    """Apply a deterministic setup plan to the filesystem."""
    active_reporter = reporter or NullReporter()
    step_results: list[StepResult] = []
    current = 0
    total = plan.total_steps
    engine = EngineFactory.create(plan.config.engine.name)

    def advance(message: str, fn: Callable[[], None]) -> None:
        nonlocal current
        current += 1
        active_reporter.on_step(current, total, message)
        try:
            fn()
            step_results.append(StepResult(name=message, success=True))
        except Exception as exc:
            step_results.append(StepResult(name=message, success=False, message=str(exc)))
            raise SetupApplyError(f"{message}: {exc}") from exc

    try:
        active_reporter.on_start(total)
        shared_pdb_file = _resolve_shared_pdb_file(plan.config)
        for directory in plan.directories:
            advance(f"mkdir {directory}", lambda directory=directory: directory.mkdir(parents=True, exist_ok=True))
        for planned_file in plan.files:

            def write_planned_file(planned_file: PlannedFile = planned_file) -> None:
                planned_file.path.write_text(planned_file.content, encoding="utf-8")

            advance(
                f"write {planned_file.path}",
                write_planned_file,
            )
        for prepare_file in plan.prepare_files:
            pdb_file = plan.config.protein.pdb_files.get(prepare_file.variant) or shared_pdb_file
            contents = engine.prepare_from_pdb(pdb_file, plan.config)

            def write_prepare_file(path: Path = prepare_file.path, contents: str = contents) -> None:
                path.write_text(contents, encoding="utf-8")

            advance(
                f"write {prepare_file.path}",
                write_prepare_file,
            )
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


def _render_subdirectory_readme(title: str) -> str:
    return f"# {title}\n\nGenerated by prepmd.\n"
