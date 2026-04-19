import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest

from prepmd.config.models import WaterBoxShape


def _make_app() -> object:
    qt_widgets = pytest.importorskip("PyQt6.QtWidgets", exc_type=ImportError)
    app = qt_widgets.QApplication.instance()
    if app is None:
        app = qt_widgets.QApplication([])
    return app


def _write_minimal_pdb(path: Path, coords: list[tuple[float, float, float]]) -> None:
    lines: list[str] = []
    for i, (x, y, z) in enumerate(coords, start=1):
        lines.append(f"ATOM  {i:5d}  CA  ALA A{i:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00           C")
    lines.append("END")
    path.write_text("\n".join(lines), encoding="utf-8")


def test_water_box_config_widget_modes_and_metrics() -> None:
    _make_app()
    from prepmd.gui.widgets.water_box_config import WaterBoxConfigWidget

    widget = WaterBoxConfigWidget()
    value = widget.get_value()
    assert value.shape == "cubic"
    assert "Volume:" in widget.volume_text()

    widget.set_shape(WaterBoxShape.ORTHORHOMBIC)
    value = widget.get_value()
    assert value.shape == "orthorhombic"
    assert value.dimensions is not None


def test_water_box_auto_mode_no_pdb() -> None:
    """Auto mode without a PDB file falls back to padding defaults."""
    _make_app()
    from prepmd.gui.widgets.water_box_config import WaterBoxConfigWidget

    widget = WaterBoxConfigWidget()
    widget._auto_box_check.setChecked(True)
    assert widget.is_auto_box()
    value = widget.get_value()
    # No PDB set – falls back to WaterBoxConfig with auto_box_padding defaults
    assert value.shape == WaterBoxShape.CUBIC
    assert value.side_length is not None


def test_water_box_auto_mode_with_pdb(tmp_path: Path) -> None:
    """Auto mode with a PDB file computes box from protein bounding box."""
    _make_app()
    from prepmd.gui.widgets.water_box_config import WaterBoxConfigWidget

    pdb = tmp_path / "protein.pdb"
    _write_minimal_pdb(pdb, [(0.0, 0.0, 0.0), (20.0, 30.0, 25.0)])

    widget = WaterBoxConfigWidget()
    widget._auto_box_check.setChecked(True)
    widget._padding_spin.setValue(10.0)
    widget.set_pdb_path(str(pdb))

    value = widget.get_value()
    assert value.shape == WaterBoxShape.CUBIC
    # extents: x=20, y=30, z=25  -> side = max(20,30,25) + 2*10 = 50
    assert value.side_length == pytest.approx(50.0)
    assert "Volume:" in widget.volume_text()


def test_water_box_auto_mode_orthorhombic(tmp_path: Path) -> None:
    """Auto mode with orthorhombic shape computes per-axis dimensions."""
    _make_app()
    from prepmd.gui.widgets.water_box_config import WaterBoxConfigWidget

    pdb = tmp_path / "protein.pdb"
    _write_minimal_pdb(pdb, [(0.0, 0.0, 0.0), (20.0, 30.0, 25.0)])

    widget = WaterBoxConfigWidget()
    widget.set_shape(WaterBoxShape.ORTHORHOMBIC)
    widget._auto_box_check.setChecked(True)
    widget._padding_spin.setValue(5.0)
    widget.set_pdb_path(str(pdb))

    value = widget.get_value()
    assert value.shape == WaterBoxShape.ORTHORHOMBIC
    # extents: x=20, y=30, z=25  -> (30, 40, 35)
    assert value.dimensions == pytest.approx((30.0, 40.0, 35.0))


def test_water_box_manual_inputs_disabled_in_auto_mode() -> None:
    """Manual spinboxes are disabled when auto mode is active."""
    _make_app()
    from prepmd.gui.widgets.water_box_config import WaterBoxConfigWidget

    widget = WaterBoxConfigWidget()
    widget._auto_box_check.setChecked(True)
    assert not widget._side_length.isEnabled()


def test_water_box_set_pdb_path() -> None:
    """set_pdb_path updates the line edit and internal path."""
    _make_app()
    from prepmd.gui.widgets.water_box_config import WaterBoxConfigWidget

    widget = WaterBoxConfigWidget()
    widget.set_pdb_path("/tmp/test.pdb")
    assert widget._pdb_line.text() == "/tmp/test.pdb"
    assert widget._pdb_path == "/tmp/test.pdb"

    widget.set_pdb_path(None)
    assert widget._pdb_line.text() == ""
