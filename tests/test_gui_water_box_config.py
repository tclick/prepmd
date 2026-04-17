import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


def test_water_box_config_widget_modes_and_metrics() -> None:
    qt_widgets = pytest.importorskip("PyQt6.QtWidgets", exc_type=ImportError)
    from prepmd.gui.widgets.water_box_config import WaterBoxConfigWidget

    app = qt_widgets.QApplication.instance()
    if app is None:
        app = qt_widgets.QApplication([])

    widget = WaterBoxConfigWidget()
    value = widget.get_value()
    assert value.shape == "cubic"
    assert "Volume:" in widget._volume_label.text()

    widget._shape.setCurrentText("orthorhombic")
    value = widget.get_value()
    assert value.shape == "orthorhombic"
    assert value.dimensions is not None
