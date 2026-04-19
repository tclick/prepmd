"""Water-box configuration widget."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from prepmd.config.models import AnionType, CationType, WaterBoxConfig, WaterBoxShape
from prepmd.core.box_geometry import (
    build_box_geometry,
    compute_box_from_protein,
    protein_extents_from_pdb,
)

WATER_MOLECULE_DENSITY_PER_A3 = 0.0334


class WaterBoxConfigWidget(QGroupBox):
    """Configure water-box shape and dimensions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Water Box", parent)
        self._pdb_path: str | None = None

        # --- shape selector ---
        self._shape = QComboBox()
        for shape in WaterBoxShape:
            self._shape.addItem(shape.value)

        # --- manual dimension spinboxes ---
        self._side_length = self._build_spinbox()
        self._edge_length = self._build_spinbox()
        self._x_dim = self._build_spinbox()
        self._y_dim = self._build_spinbox()
        self._z_dim = self._build_spinbox()

        # --- auto-box controls ---
        self._auto_box_check = QCheckBox("Auto-size from PDB")

        self._pdb_line = QLineEdit()
        self._pdb_line.setPlaceholderText("Select PDB file…")
        self._pdb_line.setReadOnly(True)
        self._pdb_browse_btn = QPushButton("Browse…")
        self._pdb_browse_btn.clicked.connect(self._browse_pdb)  # pyright: ignore[reportUnknownMemberType]

        pdb_row = QWidget()
        pdb_layout = QHBoxLayout()
        pdb_layout.setContentsMargins(0, 0, 0, 0)
        pdb_layout.addWidget(self._pdb_line)
        pdb_layout.addWidget(self._pdb_browse_btn)
        pdb_row.setLayout(pdb_layout)

        self._padding_spin = QDoubleSpinBox()
        self._padding_spin.setDecimals(1)
        self._padding_spin.setRange(0.1, 500.0)
        self._padding_spin.setSingleStep(0.5)
        self._padding_spin.setValue(10.0)

        # --- ion controls ---
        self._include_ions_check = QCheckBox("Include ions")
        self._neutralize_protein_check = QCheckBox("Neutralize protein")
        self._ion_concentration_spin = QDoubleSpinBox()
        self._ion_concentration_spin.setDecimals(3)
        self._ion_concentration_spin.setRange(0.001, 5.0)
        self._ion_concentration_spin.setSingleStep(0.01)
        self._ion_concentration_spin.setValue(0.15)
        self._cation = QComboBox()
        for ion in CationType:
            self._cation.addItem(ion.value)
        self._anion = QComboBox()
        for ion in AnionType:
            self._anion.addItem(ion.value)

        # --- labels ---
        self._volume_label = QLabel("Volume: -")
        self._water_estimate_label = QLabel("Estimated waters: -")
        self._validation_label = QLabel("")

        # --- layout ---
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
        layout.addWidget(self._auto_box_check)

        self._auto_form = QFormLayout()
        self._auto_form.addRow("PDB file", pdb_row)
        self._auto_form.addRow("Padding (Å)", self._padding_spin)
        layout.addLayout(self._auto_form)
        layout.addWidget(self._include_ions_check)

        self._ion_form = QFormLayout()
        self._ion_form.addRow("Ion concentration (M)", self._ion_concentration_spin)
        self._ion_form.addRow("Cation", self._cation)
        self._ion_form.addRow("Anion", self._anion)
        self._ion_form.addRow("", self._neutralize_protein_check)
        layout.addLayout(self._ion_form)

        layout.addWidget(self._volume_label)
        layout.addWidget(self._water_estimate_label)
        layout.addWidget(self._validation_label)
        self.setLayout(layout)

        # signals
        self._shape.currentTextChanged.connect(self._sync_inputs)  # pyright: ignore[reportUnknownMemberType]
        for box in [self._side_length, self._edge_length, self._x_dim, self._y_dim, self._z_dim]:
            box.valueChanged.connect(self._update_metrics)  # pyright: ignore[reportUnknownMemberType]
        self._auto_box_check.toggled.connect(self._on_auto_toggled)  # pyright: ignore[reportUnknownMemberType]
        self._padding_spin.valueChanged.connect(self._update_metrics)  # pyright: ignore[reportUnknownMemberType]
        self._pdb_line.textChanged.connect(self._update_metrics)  # pyright: ignore[reportUnknownMemberType]
        self._include_ions_check.toggled.connect(self._sync_ion_controls)  # pyright: ignore[reportUnknownMemberType]

        self._sync_inputs()
        self._set_auto_controls_visible(False)
        self._sync_ion_controls()

    @staticmethod
    def _build_spinbox() -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setDecimals(3)
        box.setRange(0.1, 1_000.0)
        box.setSingleStep(0.5)
        box.setValue(10.0)
        return box

    def _set_auto_controls_visible(self, visible: bool) -> None:
        self._pdb_line.setVisible(visible)
        self._pdb_browse_btn.setVisible(visible)
        self._padding_spin.setVisible(visible)
        # show/hide labels in the auto form rows
        for row in range(self._auto_form.rowCount()):
            label = self._auto_form.itemAt(row, QFormLayout.ItemRole.LabelRole)
            if label and label.widget():
                label.widget().setVisible(visible)  # pyright: ignore[reportOptionalMemberAccess]

    def _on_auto_toggled(self, checked: bool) -> None:
        self._set_auto_controls_visible(checked)
        self._sync_inputs()

    def _sync_ion_controls(self) -> None:
        enabled = self._include_ions_check.isChecked()
        self._ion_concentration_spin.setEnabled(enabled)
        self._cation.setEnabled(enabled)
        self._anion.setEnabled(enabled)
        self._neutralize_protein_check.setEnabled(enabled)
        if not enabled:
            self._neutralize_protein_check.setChecked(False)

    def _browse_pdb(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select PDB file", "", "PDB files (*.pdb);;All files (*)")
        if path:
            self._pdb_line.setText(path)
            self._pdb_path = path

    def _sync_inputs(self) -> None:
        auto = self._auto_box_check.isChecked()
        shape = WaterBoxShape(self._shape.currentText())
        is_cubic = shape == WaterBoxShape.CUBIC
        is_octa = shape == WaterBoxShape.TRUNCATED_OCTAHEDRON
        is_ortho = shape == WaterBoxShape.ORTHORHOMBIC

        # manual inputs enabled only when NOT in auto mode
        self._side_length.setEnabled(is_cubic and not auto)
        self._edge_length.setEnabled(is_octa and not auto)
        self._x_dim.setEnabled(is_ortho and not auto)
        self._y_dim.setEnabled(is_ortho and not auto)
        self._z_dim.setEnabled(is_ortho and not auto)
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
        estimated_waters = geometry.volume * WATER_MOLECULE_DENSITY_PER_A3
        self._water_estimate_label.setText(f"Estimated waters: {estimated_waters:.0f}")

    def get_value(self) -> WaterBoxConfig:
        """Return normalized widget value."""
        shape = WaterBoxShape(self._shape.currentText())
        padding = self._padding_spin.value()
        include_ions = self._include_ions_check.isChecked()
        neutralize_protein = self._neutralize_protein_check.isChecked()
        ion_concentration_molar = self._ion_concentration_spin.value()
        cation = CationType(self._cation.currentText())
        anion = AnionType(self._anion.currentText())

        if self._auto_box_check.isChecked():
            pdb_text = self._pdb_line.text().strip()
            if pdb_text:
                auto_cfg = WaterBoxConfig(
                    shape=shape,
                    auto_box_padding=padding,
                    include_ions=include_ions,
                    neutralize_protein=neutralize_protein,
                    ion_concentration_molar=ion_concentration_molar,
                    cation=cation,
                    anion=anion,
                )
                extents = protein_extents_from_pdb(Path(pdb_text))
                geometry = compute_box_from_protein(extents, auto_cfg)
                dims = geometry.dimensions
                match shape:
                    case WaterBoxShape.CUBIC:
                        return WaterBoxConfig(
                            shape=shape,
                            side_length=dims[0],
                            auto_box_padding=padding,
                            include_ions=include_ions,
                            neutralize_protein=neutralize_protein,
                            ion_concentration_molar=ion_concentration_molar,
                            cation=cation,
                            anion=anion,
                        )
                    case WaterBoxShape.TRUNCATED_OCTAHEDRON:
                        from prepmd.core.box_geometry import TruncatedOctahedronBox

                        if isinstance(geometry, TruncatedOctahedronBox):
                            return WaterBoxConfig(
                                shape=shape,
                                edge_length=geometry.edge_length,
                                auto_box_padding=padding,
                                include_ions=include_ions,
                                neutralize_protein=neutralize_protein,
                                ion_concentration_molar=ion_concentration_molar,
                                cation=cation,
                                anion=anion,
                            )
                        return WaterBoxConfig(
                            shape=shape,
                            auto_box_padding=padding,
                            include_ions=include_ions,
                            neutralize_protein=neutralize_protein,
                            ion_concentration_molar=ion_concentration_molar,
                            cation=cation,
                            anion=anion,
                        )
                    case _:
                        return WaterBoxConfig(
                            shape=shape,
                            dimensions=dims,
                            auto_box_padding=padding,
                            include_ions=include_ions,
                            neutralize_protein=neutralize_protein,
                            ion_concentration_molar=ion_concentration_molar,
                            cation=cation,
                            anion=anion,
                        )
            # no PDB selected yet; fall back to padding-only defaults
            return WaterBoxConfig(
                shape=shape,
                auto_box_padding=padding,
                include_ions=include_ions,
                neutralize_protein=neutralize_protein,
                ion_concentration_molar=ion_concentration_molar,
                cation=cation,
                anion=anion,
            )

        match shape:
            case WaterBoxShape.CUBIC:
                return WaterBoxConfig(
                    shape=shape,
                    side_length=self._side_length.value(),
                    include_ions=include_ions,
                    neutralize_protein=neutralize_protein,
                    ion_concentration_molar=ion_concentration_molar,
                    cation=cation,
                    anion=anion,
                )
            case WaterBoxShape.TRUNCATED_OCTAHEDRON:
                return WaterBoxConfig(
                    shape=shape,
                    edge_length=self._edge_length.value(),
                    include_ions=include_ions,
                    neutralize_protein=neutralize_protein,
                    ion_concentration_molar=ion_concentration_molar,
                    cation=cation,
                    anion=anion,
                )
            case _:
                return WaterBoxConfig(
                    shape=shape,
                    dimensions=(self._x_dim.value(), self._y_dim.value(), self._z_dim.value()),
                    include_ions=include_ions,
                    neutralize_protein=neutralize_protein,
                    ion_concentration_molar=ion_concentration_molar,
                    cation=cation,
                    anion=anion,
                )

    def set_shape(self, shape: WaterBoxShape) -> None:
        """Set the active shape in the widget."""
        self._shape.setCurrentText(shape.value)

    def set_pdb_path(self, path: str | None) -> None:
        """Set the PDB file path used for auto-sizing."""
        self._pdb_path = path
        self._pdb_line.setText(path or "")

    def is_auto_box(self) -> bool:
        """Return True when the widget is in auto-size mode."""
        return self._auto_box_check.isChecked()

    def validation_text(self) -> str:
        """Return current validation text."""
        return self._validation_label.text()

    def volume_text(self) -> str:
        """Return current volume text."""
        return self._volume_label.text()
