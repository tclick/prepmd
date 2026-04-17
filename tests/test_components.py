from pathlib import Path

import pytest
from typer.testing import CliRunner

from prepmd.caching import memoize
from prepmd.cli.main import LICENSE_TEXT, app
from prepmd.config.models import EngineName, ProjectConfig, ProteinConfig
from prepmd.config.validators.compatibility import CompatibilityValidator
from prepmd.config.validators.ensemble import EnsembleValidator
from prepmd.config.validators.pipeline import ValidationPipeline
from prepmd.config.validators.restraint import RestraintValidator
from prepmd.config.validators.temperature import TemperatureValidator
from prepmd.config.versioning import migrate_config
from prepmd.engines.factory import EngineFactory
from prepmd.exceptions import ConfigurationError, EngineError, StructureBuildError, ValidationError
from prepmd.file_generator.templates.equilibration import EquilibrationFileGenerator, render_equilibration
from prepmd.file_generator.templates.heating import HeatingFileGenerator, render_heating
from prepmd.file_generator.templates.minimization import MinimizationFileGenerator, render_minimization
from prepmd.file_generator.templates.production import ProductionFileGenerator, render_production
from prepmd.logging_config import configure_logging
from prepmd.models.results import RunResult, StepResult
from prepmd.performance import profile
from prepmd.structure_builder.builder import StructureBuilder
from prepmd.tleap.builder import build_tleap_commands


@pytest.fixture
def config() -> ProjectConfig:
    return ProjectConfig(project_name="demo", protein=ProteinConfig(pdb_file="/tmp/input.pdb"))


def test_template_rendering_and_tleap(config: ProjectConfig) -> None:
    assert "imin=1" in render_minimization(config)
    assert "temp0=300.0" in render_heating(config)
    assert "ensemble=NVT" in render_equilibration(config)
    assert "nstlim=500000" in render_production(config)
    assert "source leaprc.protein.ff14SB" in build_tleap_commands(config)


def test_file_generator_classes(config: ProjectConfig) -> None:
    """Concrete FileGenerator subclasses produce the same output as the standalone helpers."""
    assert MinimizationFileGenerator().render(config) == render_minimization(config)
    assert HeatingFileGenerator().render(config) == render_heating(config)
    assert EquilibrationFileGenerator().render(config) == render_equilibration(config)
    assert ProductionFileGenerator().render(config) == render_production(config)


def test_engine_name_enum() -> None:
    assert EngineName.AMBER == "amber"
    assert EngineName("gromacs") is EngineName.GROMACS
    assert str(EngineName.NAMD) == "namd"
    all_names = {e.value for e in EngineName}
    assert all_names == {"amber", "gromacs", "namd", "charmm", "openmm"}


def test_engine_factory(config: ProjectConfig) -> None:
    engine = EngineFactory.create("amber")
    lines = engine.generate_inputs(config)
    assert engine.name == "amber"
    assert any("Project: demo" in line for line in lines)

    # Also works with EngineName enum
    engine_via_enum = EngineFactory.create(EngineName.GROMACS)
    assert engine_via_enum.name == "gromacs"

    with pytest.raises(EngineError):
        EngineFactory.create("unknown")


def test_validators(config: ProjectConfig) -> None:
    RestraintValidator().validate(config)
    TemperatureValidator().validate(config)
    EnsembleValidator().validate(config)
    CompatibilityValidator().validate(config)

    bad_temp = config.model_copy(deep=True)
    bad_temp.simulation.temperature = 1500.0
    with pytest.raises(ValidationError):
        TemperatureValidator().validate(bad_temp)

    bad_ensemble = config.model_copy(update={"simulation": config.simulation.model_copy(update={"ensemble": "BAD"})})
    with pytest.raises(ValidationError):
        EnsembleValidator().validate(bad_ensemble)


def test_validation_pipeline(config: ProjectConfig) -> None:
    """ValidationPipeline runs all validators in sequence."""
    pipeline = ValidationPipeline()
    pipeline.validate(config)  # valid config passes without exception

    # Custom pipeline with single validator
    custom = ValidationPipeline(validators=[TemperatureValidator()])
    bad_temp = config.model_copy(deep=True)
    bad_temp.simulation.temperature = 9999.0
    with pytest.raises(ValidationError):
        custom.validate(bad_temp)


def test_memoize_and_profile() -> None:
    calls = {"count": 0}

    @memoize(maxsize=32)
    def cached(x: int) -> int:
        calls["count"] += 1
        return x * 2

    @profile("double")
    def doubled(x: int) -> int:
        return x * 2

    assert cached(2) == 4
    assert cached(2) == 4
    assert calls["count"] == 1
    assert doubled(3) == 6


def test_cli_license_and_setup(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["license"])
    assert result.exit_code == 0
    assert LICENSE_TEXT in result.stdout

    config_path = tmp_path / "cfg.yaml"
    config_path.write_text(
        f"project_name: cli-demo\noutput_dir: {tmp_path}\nprotein:\n  pdb_file: /tmp/input.pdb\n",
        encoding="utf-8",
    )
    setup_result = runner.invoke(app, ["setup", str(config_path)])
    assert setup_result.exit_code == 0
    assert (tmp_path / "cli-demo").exists()
    assert (tmp_path / "cli-demo" / "05_simulations" / "apo" / "replica_001" / "README.md").exists()


def test_cli_prepare(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "prepare",
            "--project-name",
            "prep",
            "--output-dir",
            str(tmp_path),
            "--replicas",
            "2",
            "--engine",
            "gromacs",
            "--pdb-file",
            str(tmp_path / "input.pdb"),
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "prep" / "05_simulations" / "apo" / "replica_001" / "gromacs_prepare.in").exists()
    assert (tmp_path / "prep" / "05_simulations" / "holo" / "replica_002" / "PROTOCOL.md").exists()


def test_cli_prepare_with_config_and_cli_overrides(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "cfg.toml"
    config_path.write_text(
        (
            'project_name = "from-config"\n'
            f'output_dir = "{tmp_path}"\n'
            "[protein]\n"
            'pdb_file = "/tmp/input.pdb"\n'
            "[simulation]\n"
            "replicas = 1\n"
            "[engine]\n"
            'name = "amber"\n'
            'force_field = "ff19sb"\n'
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "prepare",
            "--config",
            str(config_path),
            "--engine",
            "gromacs",
            "--replicas",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "from-config" / "05_simulations" / "apo" / "replica_001" / "gromacs_prepare.in").exists()
    assert (tmp_path / "from-config" / "05_simulations" / "holo" / "replica_002" / "PROTOCOL.md").exists()


def test_cli_prepare_with_orthorhombic_box_dimensions(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "prepare",
            "--project-name",
            "prep-ortho",
            "--output-dir",
            str(tmp_path),
            "--pdb-file",
            str(tmp_path / "input.pdb"),
            "--box-shape",
            "orthorhombic",
            "--box-dimensions",
            "12",
            "12",
            "15",
            "--engine",
            "gromacs",
        ],
    )
    assert result.exit_code == 0
    prep_file = tmp_path / "prep-ortho" / "05_simulations" / "apo" / "replica_001" / "gromacs_prepare.in"
    assert "-box 12.000 12.000 15.000 -bt triclinic" in prep_file.read_text(encoding="utf-8")


def test_cli_prepare_requires_project_name_without_config() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["prepare"])
    assert result.exit_code != 0
    assert "Project name is required" in result.output


def test_cli_prepare_enforces_pdb_input_mutual_exclusivity(tmp_path: Path) -> None:
    runner = CliRunner()
    no_input = runner.invoke(
        app,
        [
            "prepare",
            "--project-name",
            "prep",
            "--output-dir",
            str(tmp_path),
        ],
    )
    assert no_input.exit_code != 0
    assert "Specify exactly one PDB input method" in no_input.output

    both_input = runner.invoke(
        app,
        [
            "prepare",
            "--project-name",
            "prep",
            "--output-dir",
            str(tmp_path),
            "--pdb-file",
            str(tmp_path / "input.pdb"),
            "--pdb-id",
            "1abc",
        ],
    )
    assert both_input.exit_code != 0
    assert "Specify either a local PDB file or a PDB ID" in both_input.output


def test_results_and_migration_and_logging() -> None:
    run = RunResult(steps=[StepResult(name="a", success=True), StepResult(name="b", success=True)])
    assert run.success

    migrated = migrate_config({"project_name": "demo"})
    assert migrated["project_name"] == "demo"

    configure_logging("DEBUG")


def test_unsupported_config_extension(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{}", encoding="utf-8")

    from prepmd.config.loader import ConfigLoader

    with pytest.raises(ConfigurationError):
        ConfigLoader().load_project_config(path)


def test_structure_builder_get_results(tmp_path: Path) -> None:
    """StructureBuilder tracks build steps via RunResult."""
    cfg = ProjectConfig(project_name="test", output_dir=str(tmp_path), protein=ProteinConfig(pdb_file="/tmp/input.pdb"))
    builder = StructureBuilder(cfg)
    builder.build()
    results = builder.get_results()
    assert isinstance(results, RunResult)
    assert results.success
    step_names = [s.name for s in results.steps]
    assert "create_root_directory" in step_names
    assert "create_simulation_directories" in step_names


def test_structure_build_error_exported() -> None:
    """StructureBuildError is part of the public exception hierarchy."""
    assert issubclass(StructureBuildError, Exception)
