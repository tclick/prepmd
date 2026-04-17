from math import sqrt

import pytest

from prepmd.config.models import ProjectConfig, WaterBoxConfig, WaterBoxShape
from prepmd.core.box_geometry import CubicBox, OrthorhombicBox, TruncatedOctahedronBox, build_box_geometry
from prepmd.engines.factory import EngineFactory
from prepmd.exceptions import BoxShapeNotSupportedError, InvalidBoxDimensionsError


def test_box_geometry_volume_and_surface_area() -> None:
    cubic = CubicBox(side_length=10.0)
    assert cubic.volume == pytest.approx(1000.0)
    assert cubic.surface_area == pytest.approx(600.0)

    octa = TruncatedOctahedronBox(edge_length=10.0)
    assert octa.volume == pytest.approx(8.0 * sqrt(2.0) * (10.0**3))
    assert octa.surface_area == pytest.approx(6.0 * (1.0 + (2.0 * sqrt(3.0))) * (10.0**2))

    ortho = OrthorhombicBox(10.0, 12.0, 15.0)
    assert ortho.volume == pytest.approx(1800.0)
    assert ortho.surface_area == pytest.approx(900.0)


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
    config.engine.name = "namd"
    config.water_box = WaterBoxConfig(shape=WaterBoxShape.TRUNCATED_OCTAHEDRON, edge_length=10.0)
    engine = EngineFactory.create(config.engine.name)

    with pytest.raises(BoxShapeNotSupportedError):
        engine.get_box_geometry(config)
