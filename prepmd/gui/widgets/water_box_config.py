"""Water-box configuration widget."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)

from prepmd.config.models import WaterBoxConfig, WaterBoxShape
from prepmd.core.box_geometry import build_box_geometry


class WaterBoxConfigWidget(QGroupBox):
    """Configure water-box shape and dimensions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Water Box", parent)
        self._shape = QComboBox()
        self._shape.addItems([s.value for s in WaterBoxShape])

        self._side_length = self._build_spinbox()
        self._edge_length = self._build_spinbox()
        self._x_dim = self._build_spinbox()
        self._y_dim = self._build_spinbox()
        self._z_dim = self._build_spinbox()

        self._volume_label = QLabel("Volume: -")
        self._water_estimate_label = QLabel("Estimated waters: -")
        self._validation_label = QLabel("")

        layout = QVBoxLayout()
        form = QFormLayout()
        form.addRow("Shape", self._shape)
        form.addRow("Side length (Å)", self._side_length)
        form.addRow("Edge length (Å)", self._edge_length)

        dimensions_row = QWidget()
        dimensions_layout = QHBoxLayout()
        dimensions_layout.setContentsMargins(0, 0, 0, 0)
        dimensions_layout.addWidget(self._x_dim)
        dimensions_layout.addWidget(self._y_dim)
        dimensions_layout.addWidget(self._z_dim)
        dimensions_row.setLayout(dimensions_layout)
        form.addRow("Dimensions X/Y/Z (Å)", dimensions_row)

        layout.addLayout(form)
        layout.addWidget(self._volume_label)
        layout.addWidget(self._water_estimate_label)
        layout.addWidget(self._validation_label)
        self.setLayout(layout)

        self._shape.currentTextChanged.connect(self._sync_inputs)  # pyright: ignore[reportUnknownMemberType]
        for box in [self._side_length, self._edge_length, self._x_dim, self._y_dim, self._z_dim]:
            box.valueChanged.connect(self._update_metrics)  # pyright: ignore[reportUnknownMemberType]
        self._sync_inputs()

    @staticmethod
    def _build_spinbox() -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setDecimals(3)
        box.setRange(0.1, 1_000.0)
        box.setSingleStep(0.5)
        box.setValue(10.0)
        return box

    def _sync_inputs(self) -> None:
        shape = WaterBoxShape(self._shape.currentText())
        is_cubic = shape == WaterBoxShape.CUBIC
        is_octa = shape == WaterBoxShape.TRUNCATED_OCTAHEDRON
        is_ortho = shape == WaterBoxShape.ORTHORHOMBIC

        self._side_length.setEnabled(is_cubic)
        self._edge_length.setEnabled(is_octa)
        self._x_dim.setEnabled(is_ortho)
        self._y_dim.setEnabled(is_ortho)
        self._z_dim.setEnabled(is_ortho)
        self._update_metrics()

    def _update_metrics(self) -> None:
        try:
            geometry = build_box_geometry(self.get_value())
        except Exception as exc:
            self._validation_label.setText(str(exc))
            self._volume_label.setText("Volume: -")
            self._water_estimate_label.setText("Estimated waters: -")
            return
        self._validation_label.setText("Configuration valid")
        self._volume_label.setText(f"Volume: {geometry.volume:.2f} Å³")
        estimated_waters = geometry.volume * 0.0334
        self._water_estimate_label.setText(f"Estimated waters: {estimated_waters:.0f}")

    def get_value(self) -> WaterBoxConfig:
        """Return normalized widget value."""
        shape = WaterBoxShape(self._shape.currentText())
        if shape == WaterBoxShape.CUBIC:
            return WaterBoxConfig(shape=shape, side_length=self._side_length.value())
        if shape == WaterBoxShape.TRUNCATED_OCTAHEDRON:
            return WaterBoxConfig(shape=shape, edge_length=self._edge_length.value())
        return WaterBoxConfig(
            shape=shape,
            dimensions=(self._x_dim.value(), self._y_dim.value(), self._z_dim.value()),
        )
