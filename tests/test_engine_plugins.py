from pathlib import Path

import pytest

from prepmd.config.models import ProjectConfig, ProteinConfig, WaterBoxConfig
from prepmd.engines.base import EngineCapabilities
from prepmd.engines.factory import EngineFactory, _build_engine_registry
from prepmd.engines.plugins.amber.engine import AmberEngine as PluginAmberEngine
from prepmd.engines.plugins.charmm.engine import CharmmEngine as PluginCharmmEngine
from prepmd.engines.plugins.gromacs.engine import GromacsEngine as PluginGromacsEngine
from prepmd.engines.plugins.namd.engine import NamdEngine as PluginNamdEngine
from prepmd.engines.plugins.openmm.engine import OpenmmEngine as PluginOpenmmEngine

ENGINE_CLASSES = {
    "amber": PluginAmberEngine,
    "gromacs": PluginGromacsEngine,
    "namd": PluginNamdEngine,
    "charmm": PluginCharmmEngine,
    "openmm": PluginOpenmmEngine,
}


@pytest.mark.parametrize("engine_name", sorted(ENGINE_CLASSES))
def test_engine_factory_create_all_builtin_plugins(engine_name: str) -> None:
    config = ProjectConfig(project_name="plugin-demo", protein=ProteinConfig(pdb_file="/tmp/input.pdb"))
    engine = EngineFactory.create(engine_name)
    assert isinstance(engine, ENGINE_CLASSES[engine_name])
    assert engine.name == engine_name
    assert engine.generate_inputs(config)


def test_legacy_engine_module_shims_reexport_plugin_classes() -> None:
    from prepmd.engines.amber import AmberEngine
    from prepmd.engines.charmm import CharmmEngine
    from prepmd.engines.gromacs import GromacsEngine
    from prepmd.engines.namd import NamdEngine
    from prepmd.engines.openmm import OpenmmEngine

    assert AmberEngine is PluginAmberEngine
    assert GromacsEngine is PluginGromacsEngine
    assert NamdEngine is PluginNamdEngine
    assert CharmmEngine is PluginCharmmEngine
    assert OpenmmEngine is PluginOpenmmEngine


def test_entry_points_config_targets_plugin_modules() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    assert 'amber = "prepmd.engines.plugins.amber.engine:AmberEngine"' in text
    assert 'gromacs = "prepmd.engines.plugins.gromacs.engine:GromacsEngine"' in text
    assert 'namd = "prepmd.engines.plugins.namd.engine:NamdEngine"' in text
    assert 'charmm = "prepmd.engines.plugins.charmm.engine:CharmmEngine"' in text
    assert 'openmm = "prepmd.engines.plugins.openmm.engine:OpenmmEngine"' in text


def test_engine_registry_keeps_builtin_engine_names() -> None:
    registry = _build_engine_registry()
    assert set(registry) >= set(ENGINE_CLASSES)


@pytest.mark.parametrize(
    ("engine_name", "ensembles", "box_shapes"),
    [
        ("amber", {"NVT", "NPT", "NVE"}, {"cubic", "truncated_octahedron", "orthorhombic"}),
        ("gromacs", {"NVT", "NPT", "NVE"}, {"cubic", "truncated_octahedron", "orthorhombic"}),
        ("namd", {"NVT", "NPT"}, {"cubic", "orthorhombic"}),
        ("charmm", {"NVT", "NPT"}, {"cubic", "orthorhombic"}),
        ("openmm", {"NVT", "NPT", "NVE"}, {"cubic", "truncated_octahedron", "orthorhombic"}),
    ],
)
def test_builtin_engine_capabilities_are_exposed(engine_name: str, ensembles: set[str], box_shapes: set[str]) -> None:
    engine = EngineFactory.create(engine_name)
    capabilities = engine.capabilities
    assert isinstance(capabilities, EngineCapabilities)
    assert set(capabilities.supported_ensembles) == ensembles
    assert set(capabilities.supported_box_shapes) == box_shapes
    assert engine.supported_box_shapes == set(capabilities.supported_box_shapes)
    assert engine.supported_box_shapes == box_shapes


def test_amber_prepare_includes_ion_commands_when_enabled() -> None:
    config = ProjectConfig(
        project_name="ions-demo",
        protein=ProteinConfig(pdb_file="/tmp/input.pdb"),
        water_box=WaterBoxConfig(
            shape="cubic",
            side_length=60.0,
            include_ions=True,
            neutralize_protein=True,
            ion_concentration_molar=0.2,
            cation="K+",
            anion="Cl-",
        ),
    )
    engine = EngineFactory.create("amber")
    prepare_text = engine.prepare_from_pdb("/tmp/input.pdb", config)
    assert "addions2 mol K+ 0 Cl- 0" in prepare_text
    assert "addionsrand mol K+ 26 Cl- 26" in prepare_text
