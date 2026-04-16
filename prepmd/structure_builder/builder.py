"""Directory structure builder for MD simulations."""

from pathlib import Path
from typing import Self

from loguru import logger

from prepmd.config import ProjectConfig


class StructureBuilder:
    """Build organized MD simulation project directory structures."""

    def __init__(self, config: ProjectConfig) -> None:
        self.config = config
        self.root_dir = Path(config.output_dir) / config.project_name
        self._created_dirs: set[Path] = set()
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
                    (min_base / stage).mkdir(parents=True, exist_ok=True)
                    self._created_dirs.add(min_base / stage)

                heat_dir = replica_dir / "02_heating"
                heat_dir.mkdir(parents=True, exist_ok=True)
                self._created_dirs.add(heat_dir)

                equil_base = replica_dir / "03_equilibration"
                for stage in ["01_5kcal", "02_2kcal", "03_1kcal", "04_0.1kcal", "05_0kcal"]:
                    (equil_base / stage).mkdir(parents=True, exist_ok=True)
                    self._created_dirs.add(equil_base / stage)

                prod_dir = replica_dir / "04_production"
                prod_dir.mkdir(parents=True, exist_ok=True)
                self._created_dirs.add(prod_dir)

                analysis_base = replica_dir / "05_analysis"
                for analysis_type in ["trajectory", "all_atom", "fluctuation"]:
                    (analysis_base / analysis_type).mkdir(parents=True, exist_ok=True)
                    self._created_dirs.add(analysis_base / analysis_type)

                backup_dir = replica_dir / "06_backup"
                backup_dir.mkdir(parents=True, exist_ok=True)
                self._created_dirs.add(backup_dir)

        return self

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
