from math import sqrt
from pathlib import Path

import pytest

from prepmd.config.models import EngineName, ProjectConfig, WaterBoxConfig, WaterBoxShape
from prepmd.core.box_geometry import (
    CubicBox,
    OrthorhombicBox,
    ProteinExtents,
    TruncatedOctahedronBox,
    build_box_geometry,
    compute_box_from_protein,
    compute_water_box_volume,
    protein_extents_from_pdb,
)
from prepmd.engines.factory import EngineFactory
from prepmd.exceptions import BoxShapeNotSupportedError, InvalidBoxDimensionsError, PDBParseError


def test_box_geometry_volume_and_surface_area() -> None:
    cubic = CubicBox(side_length=10.0)
    assert cubic.volume == 1000.0
    assert cubic.surface_area == 600.0

    octa = TruncatedOctahedronBox(edge_length=10.0)
    assert abs(octa.volume - (8.0 * sqrt(2.0) * (10.0**3))) < 1e-9
    assert abs(octa.surface_area - (6.0 * (1.0 + (2.0 * sqrt(3.0))) * (10.0**2))) < 1e-9

    ortho = OrthorhombicBox(10.0, 12.0, 15.0)
    assert ortho.volume == 1800.0
    assert ortho.surface_area == 900.0


def test_box_geometry_validation() -> None:
    with pytest.raises(InvalidBoxDimensionsError):
        CubicBox(side_length=0.0)

    with pytest.raises(InvalidBoxDimensionsError):
        TruncatedOctahedronBox(edge_length=-1.0)

    with pytest.raises(InvalidBoxDimensionsError):
        OrthorhombicBox(10.0, 0.0, 10.0)


def test_build_box_geometry_from_config() -> None:
    cubic = build_box_geometry(WaterBoxConfig(shape=WaterBoxShape.CUBIC, side_length=12.0))
    assert cubic.get_box_params()["shape"] == "cubic"

    octa = build_box_geometry(WaterBoxConfig(shape=WaterBoxShape.TRUNCATED_OCTAHEDRON, edge_length=9.5))
    assert octa.get_box_params()["shape"] == "truncated_octahedron"

    ortho = build_box_geometry(WaterBoxConfig(shape=WaterBoxShape.ORTHORHOMBIC, dimensions=(12.0, 12.0, 15.0)))
    assert ortho.get_box_params()["dimensions"] == (12.0, 12.0, 15.0)


def test_engine_rejects_unsupported_box_shape() -> None:
    config = ProjectConfig(project_name="demo")
    config.engine.name = EngineName.NAMD
    config.water_box = WaterBoxConfig(shape=WaterBoxShape.TRUNCATED_OCTAHEDRON, edge_length=10.0)
    engine = EngineFactory.create(config.engine.name)

    with pytest.raises(BoxShapeNotSupportedError):
        engine.get_box_geometry(config)


# ---------------------------------------------------------------------------
# protein_extents_from_pdb
# ---------------------------------------------------------------------------


def _write_minimal_pdb(path: Path, coords: list[tuple[float, float, float]]) -> None:
    """Write a minimal PDB file with ATOM records at the given coordinates."""
    lines: list[str] = []
    for i, (x, y, z) in enumerate(coords, start=1):
        lines.append(f"ATOM  {i:5d}  CA  ALA A{i:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00           C")
    lines.append("END")
    path.write_text("\n".join(lines), encoding="utf-8")


def test_protein_extents_from_pdb(tmp_path: Path) -> None:
    pdb = tmp_path / "test.pdb"
    _write_minimal_pdb(pdb, [(0.0, 0.0, 0.0), (10.0, 20.0, 30.0), (5.0, 10.0, 15.0)])
    extents = protein_extents_from_pdb(pdb)
    assert extents.x == pytest.approx(10.0)
    assert extents.y == pytest.approx(20.0)
    assert extents.z == pytest.approx(30.0)


def test_protein_extents_from_pdb_no_atoms(tmp_path: Path) -> None:
    pdb = tmp_path / "empty.pdb"
    pdb.write_text("REMARK empty\nEND\n", encoding="utf-8")
    with pytest.raises(PDBParseError, match="No atomic coordinates"):
        protein_extents_from_pdb(pdb)


def test_protein_extents_from_pdb_missing_file(tmp_path: Path) -> None:
    with pytest.raises((PDBParseError, FileNotFoundError)):
        protein_extents_from_pdb(tmp_path / "nonexistent.pdb")


# ---------------------------------------------------------------------------
# compute_box_from_protein
# ---------------------------------------------------------------------------


def test_compute_box_from_protein_cubic() -> None:
    extents = ProteinExtents(x=20.0, y=30.0, z=25.0)
    cfg = WaterBoxConfig(shape=WaterBoxShape.CUBIC, auto_box_padding=10.0)
    box = compute_box_from_protein(extents, cfg)
    # side = max(20, 30, 25) + 2*10 = 50
    assert isinstance(box, CubicBox)
    assert box.side_length == pytest.approx(50.0)
    assert box.volume == pytest.approx(50.0**3)


def test_compute_box_from_protein_truncated_octahedron() -> None:
    extents = ProteinExtents(x=20.0, y=30.0, z=25.0)
    cfg = WaterBoxConfig(shape=WaterBoxShape.TRUNCATED_OCTAHEDRON, auto_box_padding=10.0)
    box = compute_box_from_protein(extents, cfg)
    # edge = max(20, 30, 25) + 2*10 = 50
    assert isinstance(box, TruncatedOctahedronBox)
    assert box.edge_length == pytest.approx(50.0)


def test_compute_box_from_protein_orthorhombic() -> None:
    extents = ProteinExtents(x=20.0, y=30.0, z=25.0)
    cfg = WaterBoxConfig(shape=WaterBoxShape.ORTHORHOMBIC, auto_box_padding=10.0)
    box = compute_box_from_protein(extents, cfg)
    assert isinstance(box, OrthorhombicBox)
    assert box.dimensions == pytest.approx((40.0, 50.0, 45.0))
    assert box.volume == pytest.approx(40.0 * 50.0 * 45.0)


# ---------------------------------------------------------------------------
# compute_water_box_volume
# ---------------------------------------------------------------------------


def test_compute_water_box_volume_cubic(tmp_path: Path) -> None:
    pdb = tmp_path / "protein.pdb"
    _write_minimal_pdb(pdb, [(0.0, 0.0, 0.0), (20.0, 30.0, 25.0)])
    cfg = WaterBoxConfig(shape=WaterBoxShape.CUBIC, auto_box_padding=10.0)
    volume = compute_water_box_volume(pdb, cfg)
    # extents: x=20, y=30, z=25  ->  side=30+20=50  ->  vol=125000
    assert volume == pytest.approx(125000.0)


def test_compute_water_box_volume_orthorhombic(tmp_path: Path) -> None:
    pdb = tmp_path / "protein.pdb"
    _write_minimal_pdb(pdb, [(0.0, 0.0, 0.0), (20.0, 30.0, 25.0)])
    cfg = WaterBoxConfig(shape=WaterBoxShape.ORTHORHOMBIC, auto_box_padding=5.0)
    volume = compute_water_box_volume(pdb, cfg)
    # extents: x=20, y=30, z=25  -> (30, 40, 35) -> vol=42000
    assert volume == pytest.approx(42000.0)
