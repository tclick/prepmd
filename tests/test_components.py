import json
from pathlib import Path
from zipfile import ZipFile

import pytest
import yaml
from typer.testing import CliRunner

from prepmd.caching import memoize
from prepmd.cli.commands import setup as setup_command
from prepmd.cli.main import LICENSE_TEXT, app
from prepmd.config.loader import ConfigLoader
from prepmd.config.models import EngineName, ProjectConfig, ProteinConfig
from prepmd.config.validators.compatibility import CompatibilityValidator
from prepmd.config.validators.ensemble import EnsembleValidator
from prepmd.config.validators.pipeline import ValidationPipeline
from prepmd.config.validators.restraint import RestraintValidator
from prepmd.config.validators.temperature import TemperatureValidator
from prepmd.config.versioning import migrate_config
from prepmd.core import run as core_run
from prepmd.engines.base import EngineCapabilities
from prepmd.engines.factory import EngineFactory
from prepmd.engines.plugins.amber.engine import AmberEngine as PluginAmberEngine
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


def test_compatibility_validator_uses_engine_capabilities_for_ensemble(
    config: ProjectConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        PluginAmberEngine,
        "_CAPABILITIES",
        EngineCapabilities(
            supported_ensembles=frozenset({"NVT"}),
            supported_box_shapes=frozenset({"cubic", "truncated_octahedron", "orthorhombic"}),
        ),
    )
    config.simulation.ensemble = "NVE"
    with pytest.raises(ValidationError, match="ensemble NVE is not supported by amber"):
        CompatibilityValidator().validate(config)


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


def test_cli_setup_dry_run_makes_no_output_writes(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "cfg.yaml"
    config_path.write_text(
        f"project_name: dry-demo\noutput_dir: {tmp_path}\nprotein:\n  pdb_file: /tmp/input.pdb\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["setup", str(config_path), "--dry-run"])
    assert result.exit_code == 0
    assert not (tmp_path / "dry-demo").exists()
    assert not (tmp_path / "manifest.json").exists()


def test_cli_prepare_dry_run_makes_no_output_writes(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "prepare",
            "--project-name",
            "dry-prepare-demo",
            "--output-dir",
            str(tmp_path),
            "--pdb-file",
            str(tmp_path / "input.pdb"),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert not (tmp_path / "dry-prepare-demo").exists()
    assert not (tmp_path / "manifest.json").exists()


@pytest.mark.parametrize(
    ("format_name", "filename"),
    [("yaml", "prepmd.yaml"), ("toml", "prepmd.toml")],
)
def test_cli_init_generates_valid_config_and_setup_dry_run(tmp_path: Path, format_name: str, filename: str) -> None:
    runner = CliRunner()
    config_path = tmp_path / filename
    init_result = runner.invoke(app, ["init", "--format", format_name, "--output", str(config_path)])
    assert init_result.exit_code == 0
    assert config_path.exists()

    config = ConfigLoader().load_project_config(config_path)
    assert isinstance(config, ProjectConfig)

    setup_result = runner.invoke(app, ["setup", str(config_path), "--dry-run"])
    assert setup_result.exit_code == 0


@pytest.mark.parametrize(
    ("format_name", "filename"),
    [("yaml", "prepmd.yaml"), ("toml", "prepmd.toml")],
)
def test_cli_init_defaults_output_and_force_overwrite(tmp_path: Path, format_name: str, filename: str) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        config_path = Path.cwd() / filename
        first_result = runner.invoke(app, ["init", "--format", format_name])
        assert first_result.exit_code == 0
        assert config_path.exists()

        second_result = runner.invoke(app, ["init", "--format", format_name])
        assert second_result.exit_code != 0

        forced_result = runner.invoke(app, ["init", "--format", format_name, "--force"])
        assert forced_result.exit_code == 0


def test_cli_setup_apply_writes_manifest_and_outputs(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "cfg.yaml"
    config_path.write_text(
        f"project_name: apply-demo\noutput_dir: {tmp_path}\nprotein:\n  pdb_file: /tmp/input.pdb\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["setup", str(config_path)])
    assert result.exit_code == 0
    project_root = tmp_path / "apply-demo"
    manifest_path = tmp_path / "manifest.json"
    assert project_root.exists()
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 1
    assert isinstance(manifest["plan_sha256"], str)
    assert len(manifest["plan_sha256"]) == 64
    assert manifest["outputs"]["output_dir"] == str(tmp_path.resolve())
    assert manifest["outputs"]["files"]


def test_cli_setup_manifest_tracks_output_dir_override_provenance(tmp_path: Path) -> None:
    runner = CliRunner()
    config_dir = tmp_path / "config-out"
    cli_dir = tmp_path / "cli-out"
    config_path = tmp_path / "cfg.yaml"
    config_path.write_text(
        f"project_name: provenance-demo\noutput_dir: {config_dir}\nprotein:\n  pdb_file: /tmp/input.pdb\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["setup", str(config_path), "--output-dir", str(cli_dir)])
    assert result.exit_code == 0
    manifest_path = cli_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_resolution = manifest["config_resolution"]["output_dir"]
    assert output_resolution["source"] == "cli"
    assert output_resolution["value"] == str(cli_dir.resolve())


def test_cli_setup_debug_bundle_contains_expected_members(tmp_path: Path) -> None:
    runner = CliRunner()
    output_dir = tmp_path / "bundle-out"
    bundle_path = tmp_path / "debug.zip"
    config_path = tmp_path / "cfg.toml"
    config_path.write_text(
        (f'project_name = "bundle-demo"\noutput_dir = "{output_dir}"\n[protein]\npdb_file = "/tmp/input.pdb"\n'),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["setup", str(config_path), "--debug-bundle", str(bundle_path)])
    assert result.exit_code == 0
    assert bundle_path.exists()
    with ZipFile(bundle_path) as archive:
        names = set(archive.namelist())
        env = json.loads(archive.read("env.json").decode("utf-8"))
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    assert "config.input.toml" in names
    assert "config.resolved.yaml" in names
    assert "plan.json" in names
    assert "manifest.json" in names
    assert "env.json" in names
    assert "logs.txt" in names
    assert "command.txt" in names
    assert isinstance(env["plan_sha256"], str)
    assert env["plan_sha256"] == manifest["plan_sha256"]


def test_cli_prepare_debug_bundle_contains_expected_members(tmp_path: Path) -> None:
    runner = CliRunner()
    bundle_path = tmp_path / "debug.zip"
    result = runner.invoke(
        app,
        [
            "prepare",
            "--project-name",
            "bundle-prepare-demo",
            "--output-dir",
            str(tmp_path),
            "--pdb-file",
            str(tmp_path / "input.pdb"),
            "--debug-bundle",
            str(bundle_path),
        ],
    )
    assert result.exit_code == 0
    assert bundle_path.exists()
    with ZipFile(bundle_path) as archive:
        names = set(archive.namelist())
    assert "config.input.yaml" in names
    assert "config.resolved.yaml" in names
    assert "plan.json" in names
    assert "manifest.json" in names
    assert "env.json" in names
    assert "logs.txt" in names
    assert "command.txt" in names


def test_cli_setup_plan_out_is_deterministic(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "cfg.yaml"
    config_path.write_text(
        f"project_name: plan-demo\noutput_dir: {tmp_path}\nprotein:\n  pdb_file: /tmp/input.pdb\n",
        encoding="utf-8",
    )
    first_plan = tmp_path / "plan-1.json"
    second_plan = tmp_path / "plan-2.json"

    result_1 = runner.invoke(app, ["setup", str(config_path), "--dry-run", "--plan-out", str(first_plan)])
    result_2 = runner.invoke(app, ["setup", str(config_path), "--dry-run", "--plan-out", str(second_plan)])

    assert result_1.exit_code == 0
    assert result_2.exit_code == 0
    assert first_plan.read_text(encoding="utf-8") == second_plan.read_text(encoding="utf-8")


def test_cli_setup_resume_skips_completed_steps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "cfg.yaml"
    config_path.write_text(
        f"project_name: resume-demo\noutput_dir: {tmp_path}\nprotein:\n  pdb_file: /tmp/input.pdb\n",
        encoding="utf-8",
    )
    project_root = tmp_path / "resume-demo"
    state_path = project_root / ".prepmd_state.json"

    original_write_prepare_action = core_run._write_prepare_action
    interrupted = {"raised": False}

    def make_interruptible_write_action(path: Path, contents: str):
        wrapped = original_write_prepare_action(path, contents)

        def run_once() -> None:
            if not interrupted["raised"]:
                interrupted["raised"] = True
                raise RuntimeError("simulated interruption")
            wrapped()

        return run_once

    monkeypatch.setattr(core_run, "_write_prepare_action", make_interruptible_write_action)
    first = runner.invoke(app, ["setup", str(config_path)])
    assert first.exit_code != 0
    assert state_path.exists()
    first_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert isinstance(first_state["config_fingerprints"]["plan_sha256"], str)
    done_steps = {step_id: step for step_id, step in first_state["steps"].items() if step["status"] == "done"}
    assert done_steps
    assert any(step["status"] == "failed" for step in first_state["steps"].values())

    monkeypatch.setattr(core_run, "_write_prepare_action", original_write_prepare_action)
    resumed = runner.invoke(app, ["setup", str(config_path), "--resume"])
    assert resumed.exit_code == 0
    resumed_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert all(step["status"] == "done" for step in resumed_state["steps"].values())
    for step_id, step in done_steps.items():
        assert step["started_at_utc"] is not None
        assert step["finished_at_utc"] is not None
        assert resumed_state["steps"][step_id]["started_at_utc"] == step["started_at_utc"]
        assert resumed_state["steps"][step_id]["finished_at_utc"] == step["finished_at_utc"]


def test_cli_prepare_resume_skips_completed_steps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    project_root = tmp_path / "resume-prepare-demo"
    state_path = project_root / ".prepmd_state.json"

    original_write_prepare_action_fn = core_run._write_prepare_action
    interrupted = {"raised": False}

    def make_interruptible_write_action(path: Path, contents: str):
        wrapped = original_write_prepare_action_fn(path, contents)

        def run_once() -> None:
            if not interrupted["raised"]:
                interrupted["raised"] = True
                raise RuntimeError("simulated interruption")
            wrapped()

        return run_once

    monkeypatch.setattr(core_run, "_write_prepare_action", make_interruptible_write_action)
    first = runner.invoke(
        app,
        [
            "prepare",
            "--project-name",
            "resume-prepare-demo",
            "--output-dir",
            str(tmp_path),
            "--pdb-file",
            str(tmp_path / "input.pdb"),
        ],
    )
    assert first.exit_code != 0
    assert state_path.exists()
    first_state = json.loads(state_path.read_text(encoding="utf-8"))
    done_steps = {step_id: step for step_id, step in first_state["steps"].items() if step["status"] == "done"}
    assert done_steps
    assert any(step["status"] == "failed" for step in first_state["steps"].values())

    monkeypatch.setattr(core_run, "_write_prepare_action", original_write_prepare_action_fn)
    resumed = runner.invoke(
        app,
        [
            "prepare",
            "--project-name",
            "resume-prepare-demo",
            "--output-dir",
            str(tmp_path),
            "--pdb-file",
            str(tmp_path / "input.pdb"),
            "--resume",
        ],
    )
    assert resumed.exit_code == 0
    resumed_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert all(step["status"] == "done" for step in resumed_state["steps"].values())
    for step_id, step in done_steps.items():
        assert step["started_at_utc"] is not None
        assert step["finished_at_utc"] is not None
        assert resumed_state["steps"][step_id]["started_at_utc"] == step["started_at_utc"]
        assert resumed_state["steps"][step_id]["finished_at_utc"] == step["finished_at_utc"]


def test_cli_setup_overwrite_resets_state_and_regenerates(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "cfg.yaml"
    config_path.write_text(
        f"project_name: overwrite-demo\noutput_dir: {tmp_path}\nprotein:\n  pdb_file: /tmp/input.pdb\n",
        encoding="utf-8",
    )

    first = runner.invoke(app, ["setup", str(config_path)])
    assert first.exit_code == 0
    project_root = tmp_path / "overwrite-demo"
    state_path = project_root / ".prepmd_state.json"
    first_state = json.loads(state_path.read_text(encoding="utf-8"))
    readme_path = project_root / "05_simulations" / "apo" / "replica_001" / "README.md"
    readme_path.write_text("user-modified", encoding="utf-8")

    second = runner.invoke(app, ["setup", str(config_path), "--overwrite"])
    assert second.exit_code == 0
    second_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert second_state["run_id"] != first_state["run_id"]
    assert readme_path.read_text(encoding="utf-8") != "user-modified"


def test_cli_prepare_overwrite_resets_state_and_regenerates(tmp_path: Path) -> None:
    runner = CliRunner()

    first = runner.invoke(
        app,
        [
            "prepare",
            "--project-name",
            "overwrite-prepare-demo",
            "--output-dir",
            str(tmp_path),
            "--pdb-file",
            str(tmp_path / "input.pdb"),
        ],
    )
    assert first.exit_code == 0
    project_root = tmp_path / "overwrite-prepare-demo"
    state_path = project_root / ".prepmd_state.json"
    first_state = json.loads(state_path.read_text(encoding="utf-8"))
    readme_path = project_root / "05_simulations" / "apo" / "replica_001" / "README.md"
    readme_path.write_text("user-modified", encoding="utf-8")

    second = runner.invoke(
        app,
        [
            "prepare",
            "--project-name",
            "overwrite-prepare-demo",
            "--output-dir",
            str(tmp_path),
            "--pdb-file",
            str(tmp_path / "input.pdb"),
            "--overwrite",
        ],
    )
    assert second.exit_code == 0
    second_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert second_state["run_id"] != first_state["run_id"]
    assert readme_path.read_text(encoding="utf-8") != "user-modified"


def test_cli_setup_json_logging_outputs_json_lines_with_step_transitions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    config_path = tmp_path / "cfg.yaml"
    config_path.write_text(
        f"project_name: json-log-demo\noutput_dir: {tmp_path}\nprotein:\n  pdb_file: /tmp/input.pdb\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_command.console, "print", lambda *args, **kwargs: None)

    result = runner.invoke(app, ["setup", str(config_path), "--log-format", "json"])
    assert result.exit_code == 0
    parsed_lines = [json.loads(line) for line in result.output.splitlines() if line.strip()]
    assert parsed_lines
    transitions = [
        entry for entry in parsed_lines if entry.get("record", {}).get("extra", {}).get("event") == "step_transition"
    ]
    assert transitions
    statuses = {entry["record"]["extra"]["status"] for entry in transitions}
    assert "running" in statuses
    assert "done" in statuses


def test_cli_prepare_json_logging_outputs_json_lines_with_step_transitions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    monkeypatch.setattr(setup_command.console, "print", lambda *args, **kwargs: None)

    result = runner.invoke(
        app,
        [
            "prepare",
            "--project-name",
            "json-log-prepare-demo",
            "--output-dir",
            str(tmp_path),
            "--pdb-file",
            str(tmp_path / "input.pdb"),
            "--log-format",
            "json",
        ],
    )
    assert result.exit_code == 0
    parsed_lines = [json.loads(line) for line in result.output.splitlines() if line.strip()]
    assert parsed_lines
    transitions = [
        entry for entry in parsed_lines if entry.get("record", {}).get("extra", {}).get("event") == "step_transition"
    ]
    assert transitions
    statuses = {entry["record"]["extra"]["status"] for entry in transitions}
    assert "running" in statuses
    assert "done" in statuses


@pytest.mark.parametrize("subcommand", ["setup", "prepare"])
def test_cli_offline_mode_validates_pdb_cache_availability(subcommand: str, tmp_path: Path) -> None:
    runner = CliRunner()
    cache_dir = tmp_path / "cache"
    config_path = tmp_path / "cfg.yaml"
    config_payload = {
        "project_name": "offline-demo",
        "output_dir": str(tmp_path),
        "protein": {"pdb_id": "1abc", "pdb_cache_dir": str(cache_dir)},
    }
    config_path.write_text(yaml.safe_dump(config_payload, sort_keys=True), encoding="utf-8")
    if subcommand == "setup":
        command_args = [subcommand, str(config_path), "--offline"]
    else:
        command_args = [
            subcommand,
            "--project-name",
            "offline-demo",
            "--output-dir",
            str(tmp_path),
            "--pdb-id",
            "1abc",
            "--pdb-cache-dir",
            str(cache_dir),
            "--offline",
        ]
    missing_cache = runner.invoke(app, command_args)
    assert missing_cache.exit_code != 0
    assert "Offline mode is enabled" in missing_cache.output

    cache_dir.mkdir(parents=True)
    (cache_dir / "1ABC.pdb").write_text("HEADER OFFLINE CACHE\n", encoding="utf-8")
    with_cache = runner.invoke(app, command_args)
    assert with_cache.exit_code == 0


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


def test_cli_prepare_offline_uses_cached_pdb_without_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "1ABC.pdb").write_text("cached", encoding="utf-8")

    def should_not_download(*args: object, **kwargs: object) -> str:
        raise AssertionError("network should not be used in offline mode")

    monkeypatch.setattr("prepmd.structure.pdb_handler.PDBList.retrieve_pdb_file", should_not_download)

    result = runner.invoke(
        app,
        [
            "prepare",
            "--project-name",
            "prep-offline",
            "--output-dir",
            str(tmp_path),
            "--pdb-id",
            "1abc",
            "--pdb-cache-dir",
            str(cache_dir),
            "--offline",
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "prep-offline" / "05_simulations" / "apo" / "replica_001" / "amber_prepare.in").exists()


def test_cli_setup_offline_fails_fast_on_cache_miss(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    cache_dir = tmp_path / "cache"
    config_path = tmp_path / "cfg.yaml"
    config_path.write_text(
        (
            "project_name: setup-offline\n"
            f"output_dir: {tmp_path}\n"
            "protein:\n"
            "  pdb_id: 1abc\n"
            f"  pdb_cache_dir: {cache_dir}\n"
        ),
        encoding="utf-8",
    )

    def should_not_download(*args: object, **kwargs: object) -> str:
        raise AssertionError("network should not be used in offline mode")

    monkeypatch.setattr("prepmd.structure.pdb_handler.PDBList.retrieve_pdb_file", should_not_download)

    result = runner.invoke(app, ["setup", str(config_path), "--offline"])

    assert result.exit_code != 0
    assert "Offline mode is enabled" in result.output
    assert "Pre-populate this cache file" in result.output
    assert "--pdb-cache-dir" in result.output
    assert "protein.pdb_cache_dir" in result.output


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
