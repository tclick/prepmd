"""Directory structure builder for MD simulations."""

from pathlib import Path
from typing import Self

from loguru import logger

from prepmd.config import ProjectConfig
from prepmd.engines.factory import EngineFactory
from prepmd.templates.protocol_templates import render_protocol_overview
from prepmd.templates.readme_templates import render_replica_readme


class StructureBuilder:
    """Build organized MD simulation project directory structures."""

    def __init__(self, config: ProjectConfig) -> None:
        self.config = config
        self.root_dir = Path(config.output_dir) / config.project_name
        self._created_dirs: set[Path] = set()
        self._engine = EngineFactory.create(config.engine.name)
        logger.info(f"Initialized StructureBuilder for {self.root_dir}")

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
        sims_base = self.root_dir / "05_simulations"
        for variant in self.config.protein.variants:
            variant_dir = sims_base / variant
            for replica_idx in range(1, self.config.simulation.replicas + 1):
                replica_num = f"{replica_idx:03d}"
                replica_dir = variant_dir / f"replica_{replica_num}"

                min_base = replica_dir / "01_minimization"
                for stage in ["01_full_restraint", "02_backbone_restraint", "03_no_restraint"]:
                    stage_dir = min_base / stage
                    stage_dir.mkdir(parents=True, exist_ok=True)
                    self._created_dirs.add(stage_dir)
                    self._write_subdirectory_readme(stage_dir, "Minimization stage")

                heat_dir = replica_dir / "02_heating"
                heat_dir.mkdir(parents=True, exist_ok=True)
                self._created_dirs.add(heat_dir)
                self._write_subdirectory_readme(heat_dir, "NVT heating stage")

                equil_base = replica_dir / "03_equilibration"
                for stage in ["01_5kcal", "02_2kcal", "03_1kcal", "04_0.1kcal", "05_0kcal"]:
                    stage_dir = equil_base / stage
                    stage_dir.mkdir(parents=True, exist_ok=True)
                    self._created_dirs.add(stage_dir)
                    self._write_subdirectory_readme(stage_dir, "NPT equilibration stage")

                prod_dir = replica_dir / "04_production"
                prod_dir.mkdir(parents=True, exist_ok=True)
                self._created_dirs.add(prod_dir)
                for run_idx in range(1, self.config.simulation.production_runs + 1):
                    run_dir = prod_dir / f"run_{run_idx:03d}"
                    run_dir.mkdir(parents=True, exist_ok=True)
                    self._created_dirs.add(run_dir)
                    self._write_subdirectory_readme(
                        run_dir, f"Production segment {run_idx}/{self.config.simulation.production_runs}"
                    )

                analysis_base = replica_dir / "05_analysis"
                for analysis_type in ["trajectory", "all_atom", "fluctuation"]:
                    (analysis_base / analysis_type).mkdir(parents=True, exist_ok=True)
                    self._created_dirs.add(analysis_base / analysis_type)

                backup_dir = replica_dir / "06_backup"
                backup_dir.mkdir(parents=True, exist_ok=True)
                self._created_dirs.add(backup_dir)

                (replica_dir / "README.md").write_text(
                    render_replica_readme(self.config, variant, replica_num, self._engine.name),
                    encoding="utf-8",
                )
                (replica_dir / "PROTOCOL.md").write_text(
                    render_protocol_overview(self.config),
                    encoding="utf-8",
                )
                pdb_file = self.config.protein.pdb_files.get(variant)
                prep_contents = self._engine.prepare_from_pdb(pdb_file, self.config)
                (replica_dir / f"{self._engine.name}_prepare.in").write_text(prep_contents, encoding="utf-8")

        return self

    def _write_subdirectory_readme(self, directory: Path, title: str) -> None:
        """Write README.md into each simulation subdirectory."""

        (directory / "README.md").write_text(f"# {title}\n\nGenerated by prepmd.\n", encoding="utf-8")

    def build(self) -> Path:
        (
            self.create_root_directory()
            .create_input_directories()
            .create_script_directories()
            .create_log_directories()
            .create_analysis_template_directories()
            .create_simulation_directories()
        )
        logger.success(
            f"Project structure created: {self.root_dir} "
            f"({len(self._created_dirs)} directories)"
        )
        return self.root_dir

    def get_created_directories(self) -> set[Path]:
        return self._created_dirs.copy()
