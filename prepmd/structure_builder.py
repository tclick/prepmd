"""
Directory structure builder for MD simulations using Builder pattern.

This module creates organized project hierarchies for multi-engine,
multi-replica, multi-variant MD simulations with templated documentation.

Classes:
    StructureBuilder: Fluent API for building project structure
    DirectoryConfig: Configuration for directory creation

Design Patterns:
    - Builder: Fluent API for composable structure creation
    - Template Method: Configurable directory templates

License:
    GNU General Public License v3.0 or later (GPLv3+)
"""

from pathlib import Path
from typing import Self

from loguru import logger

from prepmd.config import ProjectConfig


class StructureBuilder:
    """Build organized MD simulation project directory structures.

    This class implements the Builder pattern for creating complex,
    hierarchical directory structures with optional templated files.

    Attributes:
        config: ProjectConfig with project settings
        root_dir: Root directory for the project
        _created_dirs: Set of created directory paths (tracking)

    Example:
        >>> config = ProjectConfig(project_name="my_md", ...)
        >>> (StructureBuilder(config)
        ...     .create_root_directory()
        ...     .create_input_directories()
        ...     .create_simulation_directories()
        ...     .create_analysis_templates()
        ...     .build())
    """

    def __init__(self, config: ProjectConfig) -> None:
        """Initialize structure builder.

        Args:
            config: ProjectConfig with project settings
        """
        self.config = config
        self.root_dir = Path(config.output_dir) / config.project_name
        self._created_dirs: set[Path] = set()
        logger.info(f"Initialized StructureBuilder for {self.root_dir}")

    def create_root_directory(self) -> Self:
        """Create root project directory.

        Returns:
            Self for method chaining

        Example:
            >>> builder.create_root_directory()
        """
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._created_dirs.add(self.root_dir)
        logger.info(f"Created root directory: {self.root_dir}")
        return self

    def create_input_directories(self) -> Self:
        """Create input data directories.

        Creates:
            - 01_input/structures/
            - 01_input/parameters/
            - 01_input/configs/
            - 01_input/tleap_scripts/

        Returns:
            Self for method chaining
        """
        input_base = self.root_dir / "01_input"
        subdirs = [
            "structures",
            "parameters",
            "configs",
            "tleap_scripts",
        ]

        for subdir in subdirs:
            dir_path = input_base / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            self._created_dirs.add(dir_path)

        logger.info(f"Created input directories in {input_base}")
        return self

    def create_script_directories(self) -> Self:
        """Create script directories.

        Creates:
            - 02_scripts/preparation/
            - 02_scripts/simulation/
            - 02_scripts/analysis/
            - 02_scripts/utilities/

        Returns:
            Self for method chaining
        """
        scripts_base = self.root_dir / "02_scripts"
        subdirs = [
            "preparation",
            "simulation",
            "analysis",
            "utilities",
        ]

        for subdir in subdirs:
            dir_path = scripts_base / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            self._created_dirs.add(dir_path)

        logger.info(f"Created script directories in {scripts_base}")
        return self

    def create_log_directories(self) -> Self:
        """Create logging directories.

        Creates:
            - 03_logs/simulation/
            - 03_logs/analysis/
            - 03_logs/errors/

        Returns:
            Self for method chaining
        """
        logs_base = self.root_dir / "03_logs"
        subdirs = ["simulation", "analysis", "errors"]

        for subdir in subdirs:
            dir_path = logs_base / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            self._created_dirs.add(dir_path)

        logger.info(f"Created log directories in {logs_base}")
        return self

    def create_analysis_template_directories(self) -> Self:
        """Create analysis template directories.

        Creates:
            - 04_analysis_templates/trajectory_processing/
            - 04_analysis_templates/all_atom/
            - 04_analysis_templates/fluctuation_analysis/
            - 04_analysis_templates/summary/

        Returns:
            Self for method chaining
        """
        templates_base = self.root_dir / "04_analysis_templates"
        subdirs = [
            "trajectory_processing",
            "all_atom",
            "fluctuation_analysis",
            "summary",
        ]

        for subdir in subdirs:
            dir_path = templates_base / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            self._created_dirs.add(dir_path)

        logger.info(f"Created analysis template directories in {templates_base}")
        return self

    def create_simulation_directories(self) -> Self:
        """Create simulation replica and variant directories.

        Creates hierarchical structure for all variants and replicas:
            05_simulations/
            ├── {variant}/
            │   ├── replica_001/
            │   ├── replica_002/
            │   └── ...
            └── {next_variant}/

        For each replica:
            ├── 01_minimization/
            │   ├── 01_full_restraint/
            │   ├── 02_backbone_restraint/
            │   └── 03_no_restraint/
            ├── 02_heating/
            ├── 03_equilibration/
            │   ├── 01_5kcal/
            │   ├── 02_2kcal/
            │   ├── 03_1kcal/
            │   ├── 04_0.1kcal/
            │   └── 05_0kcal/
            ├── 04_production/
            ├── 05_analysis/
            │   ├── trajectory/
            │   ├── all_atom/
            │   └── fluctuation/
            └── 06_backup/

        Returns:
            Self for method chaining
        """
        sims_base = self.root_dir / "05_simulations"

        for variant in self.config.protein.variants:
            variant_dir = sims_base / variant

            for replica_idx in range(1, self.config.simulation.replicas + 1):
                replica_num = f"{replica_idx:03d}"
                replica_dir = variant_dir / f"replica_{replica_num}"

                # Minimization stages
                min_base = replica_dir / "01_minimization"
                for stage in ["01_full_restraint", "02_backbone_restraint", "03_no_restraint"]:
                    (min_base / stage).mkdir(parents=True, exist_ok=True)
                    self._created_dirs.add(min_base / stage)

                # Heating
                heat_dir = replica_dir / "02_heating"
                heat_dir.mkdir(parents=True, exist_ok=True)
                self._created_dirs.add(heat_dir)

                # Equilibration stages
                equil_base = replica_dir / "03_equilibration"
                for stage in ["01_5kcal", "02_2kcal", "03_1kcal", "04_0.1kcal", "05_0kcal"]:
                    (equil_base / stage).mkdir(parents=True, exist_ok=True)
                    self._created_dirs.add(equil_base / stage)

                # Production
                prod_dir = replica_dir / "04_production"
                prod_dir.mkdir(parents=True, exist_ok=True)
                self._created_dirs.add(prod_dir)

                # Analysis
                analysis_base = replica_dir / "05_analysis"
                for analysis_type in ["trajectory", "all_atom", "fluctuation"]:
                    (analysis_base / analysis_type).mkdir(parents=True, exist_ok=True)
                    self._created_dirs.add(analysis_base / analysis_type)

                # Backup
                backup_dir = replica_dir / "06_backup"
                backup_dir.mkdir(parents=True, exist_ok=True)
                self._created_dirs.add(backup_dir)

                logger.debug(f"Created replica structure: {replica_dir}")

        logger.info(
            f"Created simulation directories: {len(self.config.protein.variants)} "
            f"variants × {self.config.simulation.replicas} replicas"
        )
        return self

    def build(self) -> Path:
        """Build complete project structure.

        This is a convenience method that calls all builder steps.

        Returns:
            Path to root project directory

        Example:
            >>> root = builder.build()
            >>> print(f"Project created at: {root}")
        """
        (self.create_root_directory()
            .create_input_directories()
            .create_script_directories()
            .create_log_directories()
            .create_analysis_template_directories()
            .create_simulation_directories())

        logger.success(
            f"Project structure created: {self.root_dir} "
            f"({len(self._created_dirs)} directories)"
        )
        return self.root_dir

    def get_created_directories(self) -> set[Path]:
        """Get set of all created directories.

        Returns:
            Set of Path objects for created directories
        """
        return self._created_dirs.copy()

    def __repr__(self) -> str:
        """String representation of builder state."""
        return (
            f"StructureBuilder(project={self.config.project_name}, "
            f"root={self.root_dir}, created={len(self._created_dirs)})"
        )
