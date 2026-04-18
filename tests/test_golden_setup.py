from pathlib import Path

import pytest

from tests._golden import GoldenScenario, assert_setup_matches_golden

GOLDEN_ROOT = Path(__file__).parent / "golden"


@pytest.mark.parametrize(
    "scenario",
    [
        GoldenScenario(
            name="basic-pdb-id",
            project_name="basic-pdb-id",
            config_text=(
                "project_name: basic-pdb-id\n"
                "protein:\n"
                "  pdb_id: 1abc\n"
                "engine:\n"
                "  name: amber\n"
                "  force_field: ff19sb\n"
                "  water_model: OPC3\n"
                "simulation:\n"
                "  replicas: 1\n"
                "water_box:\n"
                "  shape: cubic\n"
                "  side_length: 10.0\n"
            ),
            mock_download_path="fixtures/1ABC.pdb",
        ),
        GoldenScenario(
            name="truncated-orthorhombic-opc",
            project_name="truncated-orthorhombic-opc",
            config_text=(
                "project_name: truncated-orthorhombic-opc\n"
                "protein:\n"
                "  pdb_file: fixtures/input.pdb\n"
                "engine:\n"
                "  name: amber\n"
                "  force_field: ff19sb\n"
                "  water_model: OPC\n"
                "simulation:\n"
                "  replicas: 1\n"
                "water_box:\n"
                "  shape: orthorhombic\n"
                "  dimensions: [12.0, 14.0, 16.0]\n"
            ),
        ),
    ],
    ids=lambda scenario: scenario.name,
)
def test_setup_golden_snapshots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: GoldenScenario,
) -> None:
    assert_setup_matches_golden(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        scenario=scenario,
        golden_root=GOLDEN_ROOT,
    )
