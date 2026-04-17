"""Directory structure builder for MD simulations."""

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Self

from loguru import logger

from prepmd.config import ProjectConfig
from prepmd.core.config import CoreSimulationConfig
from prepmd.core.protocols import ProtocolStage, get_default_protocol
from prepmd.core.simulation import SimulationPlan
from prepmd.engines.factory import EngineFactory
from prepmd.exceptions import StructureBuildError
from prepmd.models.results import RunResult, StepResult
from prepmd.structure.pdb_handler import PDBHandler
from prepmd.templates.protocol_templates import render_protocol_overview
from prepmd.templates.readme_templates import render_replica_readme


class StructureBuilder(SimulationPlan):
    """Build organized MD simulation project directory structures.

    This class implements :class:`~prepmd.core.simulation.SimulationPlan` and
    is responsible for creating the full on-disk layout required to run a
    molecular-dynamics project, including per-stage directories, engine
    preparation scripts, and documentation files.

    Each high-level build step is recorded as a :class:`~prepmd.models.results.StepResult`
    and collected into a :class:`~prepmd.models.results.RunResult` accessible via
    :meth:`get_results` after :meth:`build` completes.
    """

    def __init__(self, config: ProjectConfig) -> None:
        self.config = config
        self.root_dir = Path(config.output_dir) / config.project_name
        self._created_dirs: set[Path] = set()
        self._engine = EngineFactory.create(config.engine.name)
        self._shared_pdb_file = self._resolve_shared_pdb_file()
        self._results: RunResult = RunResult()
        logger.info(f"Initialized StructureBuilder for {self.root_dir}")

    # ------------------------------------------------------------------
    # SimulationPlan interface
    # ------------------------------------------------------------------

    def build(self) -> Path:
        """Build the project directory structure and return the root path.

        Each top-level creation step is tracked as a
        :class:`~prepmd.models.results.StepResult`.  If any step raises, a
        :class:`~prepmd.exceptions.StructureBuildError` is raised after the
        partial results are stored.

        Returns
        -------
        Path
            The root directory of the created project.

        Raises
        ------
        StructureBuildError
            When a build step fails.
        """
        steps: list[StepResult] = []
        step_sequence: list[tuple[str, Callable[[], Self]]] = [
            ("create_root_directory", self.create_root_directory),
            ("create_input_directories", self.create_input_directories),
            ("create_script_directories", self.create_script_directories),
            ("create_log_directories", self.create_log_directories),
            ("create_analysis_template_directories", self.create_analysis_template_directories),
            ("create_simulation_directories", self.create_simulation_directories),
        ]
        for step_name, step_fn in step_sequence:
            try:
                step_fn()
                steps.append(StepResult(name=step_name, success=True))
            except Exception as exc:
                steps.append(StepResult(name=step_name, success=False, message=str(exc)))
                self._results = RunResult(steps=steps)
                raise StructureBuildError(f"Build step '{step_name}' failed: {exc}") from exc
        self._results = RunResult(steps=steps)
        logger.success(f"Project structure created: {self.root_dir} ({len(self._created_dirs)} directories)")
        return self.root_dir

    # ------------------------------------------------------------------
    # Step methods
    # ------------------------------------------------------------------

    def create_root_directory(self) -> Self:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._created_dirs.add(self.root_dir)
        return self

    def create_input_directories(self) -> Self:
        input_base = self.root_dir / "01_input"
        for subdir in ["structures", "parameters", "configs", "tleap_scripts"]:
            dir_path = input_base / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            self._created_dirs.add(dir_path)
        return self

    def create_script_directories(self) -> Self:
        scripts_base = self.root_dir / "02_scripts"
        for subdir in ["preparation", "simulation", "analysis", "utilities"]:
            dir_path = scripts_base / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            self._created_dirs.add(dir_path)
        return self

    def create_log_directories(self) -> Self:
        logs_base = self.root_dir / "03_logs"
        for subdir in ["simulation", "analysis", "errors"]:
            dir_path = logs_base / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            self._created_dirs.add(dir_path)
        return self

    def create_analysis_template_directories(self) -> Self:
        templates_base = self.root_dir / "04_analysis_templates"
        for subdir in ["trajectory_processing", "all_atom", "fluctuation_analysis", "summary"]:
            dir_path = templates_base / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            self._created_dirs.add(dir_path)
        return self

    def create_simulation_directories(self) -> Self:
        """Create per-variant, per-replica simulation subdirectories.

        Stage directories are derived directly from
        :func:`~prepmd.core.protocols.get_default_protocol` so that the
        filesystem layout and the documented protocol are always in sync.
        """
        core_config = CoreSimulationConfig(
            target_temperature=self.config.simulation.temperature,
            production_runs=self.config.simulation.production_runs,
            production_run_length_ns=self.config.simulation.production_run_length_ns,
            force_field=self.config.engine.force_field,
            water_model=self.config.engine.water_model,
        )
        protocol = get_default_protocol(core_config)

        sims_base = self.root_dir / "05_simulations"
        for variant in sorted(self.config.protein.variants):
            variant_dir = sims_base / variant
            for replica_idx in range(1, self.config.simulation.replicas + 1):
                replica_num = f"{replica_idx:03d}"
                replica_dir = variant_dir / f"replica_{replica_num}"

                self._create_protocol_stage_dirs(replica_dir, protocol)
                self._create_analysis_and_backup_dirs(replica_dir)
                self._write_replica_files(replica_dir, variant, replica_num)

        return self

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _create_protocol_stage_dirs(self, replica_dir: Path, protocol: Mapping[str, list[ProtocolStage]]) -> None:
        """Create stage directories driven by the protocol definition.

        For phases that contain a single stage whose name matches the phase
        key (e.g. ``02_heating``), only the phase directory is created.
        For all other phases (multiple stages, or single stage with a
        different name), a sub-directory per stage is created.
        """
        for phase_name, stages in protocol.items():
            phase_dir = replica_dir / phase_name
            single_stage_same_name = len(stages) == 1 and stages[0].name == phase_name
            if single_stage_same_name:
                phase_dir.mkdir(parents=True, exist_ok=True)
                self._created_dirs.add(phase_dir)
                self._write_subdirectory_readme(phase_dir, stages[0].notes)
            else:
                for stage in stages:
                    stage_dir = phase_dir / stage.name
                    stage_dir.mkdir(parents=True, exist_ok=True)
                    self._created_dirs.add(stage_dir)
                    self._write_subdirectory_readme(stage_dir, stage.notes)

    def _create_analysis_and_backup_dirs(self, replica_dir: Path) -> None:
        analysis_base = replica_dir / "05_analysis"
        for analysis_type in ["trajectory", "all_atom", "fluctuation"]:
            (analysis_base / analysis_type).mkdir(parents=True, exist_ok=True)
            self._created_dirs.add(analysis_base / analysis_type)

        backup_dir = replica_dir / "06_backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        self._created_dirs.add(backup_dir)

    def _write_replica_files(self, replica_dir: Path, variant: str, replica_num: str) -> None:
        replica_dir.mkdir(parents=True, exist_ok=True)
        (replica_dir / "README.md").write_text(
            render_replica_readme(self.config, variant, replica_num, self._engine.name),
            encoding="utf-8",
        )
        (replica_dir / "PROTOCOL.md").write_text(
            render_protocol_overview(self.config),
            encoding="utf-8",
        )
        pdb_file = self.config.protein.pdb_files.get(variant) or self._shared_pdb_file
        prep_contents = self._engine.prepare_from_pdb(pdb_file, self.config)
        (replica_dir / f"{self._engine.name}_prepare.in").write_text(prep_contents, encoding="utf-8")

    def _resolve_shared_pdb_file(self) -> str | None:
        protein = self.config.protein
        if protein.pdb_file is not None:
            return protein.pdb_file
        if protein.pdb_id is None:
            return None
        cache_dir = Path(protein.pdb_cache_dir) if protein.pdb_cache_dir is not None else None
        downloaded = PDBHandler(cache_dir=cache_dir).get_or_download(protein.pdb_id)
        return str(downloaded)

    def _write_subdirectory_readme(self, directory: Path, title: str) -> None:
        (directory / "README.md").write_text(f"# {title}\n\nGenerated by prepmd.\n", encoding="utf-8")

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_results(self) -> RunResult:
        """Return build step results accumulated during the last :meth:`build` call."""
        return self._results

    def get_created_directories(self) -> set[Path]:
        return self._created_dirs.copy()
