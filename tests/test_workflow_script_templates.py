import pytest

from prepmd.templates.workflow_script_templates import render_replica_workflow_scripts


@pytest.mark.parametrize("engine_name", ["amber", "gromacs", "charmm", "namd", "openmm"])
def test_render_replica_workflow_scripts_contains_required_steps(engine_name: str) -> None:
    scripts = render_replica_workflow_scripts(engine_name)
    paths = set(scripts)
    assert any(path.startswith("05_post_processing/01_strip_waters") for path in paths)
    assert any(path.startswith("05_post_processing/02_center") for path in paths)
    assert any(path.startswith("05_post_processing/03_merge_production") for path in paths)
    assert any(path.startswith("05_post_processing/04_visualize_merged") for path in paths)
    assert any(path.startswith("06_analysis/01_rmsd") for path in paths)
    assert any(path.startswith("06_analysis/02_rmsf") for path in paths)
    assert any(path.startswith("06_analysis/03_radius_of_gyration") for path in paths)
    assert any(path.startswith("06_analysis/04_hbond") for path in paths)
    assert any(path.startswith("06_analysis/05_sasa") for path in paths)
