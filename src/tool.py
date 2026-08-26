import dataclasses

from chimerax.core.tools import ToolInstance
from chimerax.core.commands import run
from chimerax.ui import MainToolWindow

from Qt.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QScrollArea, QWidget, QSizePolicy,
    QListWidget, QPushButton, QLabel, QLineEdit, QTabWidget, QStackedWidget,
    QComboBox, QCheckBox, QDoubleSpinBox, QSpinBox, QColorDialog,
    QMessageBox, QFileDialog,
)
from Qt.QtCore import Qt, QSize

from .style_model import (
    FigureStyleTemplate, DEFAULT_TEMPLATES, load_templates, save_templates,
    export_templates, import_templates,
)

_DEFAULT_NAMES = {t.name for t in DEFAULT_TEMPLATES}

_COLOR_MODES = [
    ("none", "None"),
    ("single", "Single color"),
    ("chain", "By chain"),
    ("bfactor", "By B-factor"),
    ("heteroatom", "By heteroatom"),
    ("alphafold", "AlphaFold pLDDT"),
]

_CHAIN_PALETTES = ["pastel2-4", "rainbow", "spectral-11", "set1-9"]
_BFACTOR_PALETTES = ["blue:white:red", "blue:red:yellow", "grayscale", "cyan:yellow:maroon"]
_FORMAT_EXTENSIONS = {"png": "png", "jpeg": "jpg", "tiff": "tiff"}

_LABEL_WIDTH = 120
MIN_PANEL_HEIGHT = 800


class _TallSizeHintScrollArea(QScrollArea):
    """A QScrollArea whose sizeHint has a floor, so ChimeraX docks it tall on
    first show without a hard setMinimumHeight fighting later resizes."""

    def __init__(self, min_height):
        super().__init__()
        self._min_height = min_height

    def sizeHint(self):
        hint = super().sizeHint()
        return QSize(hint.width(), max(hint.height(), self._min_height))


def make_scrollable(widget, min_height=MIN_PANEL_HEIGHT):
    scroll = _TallSizeHintScrollArea(min_height)
    scroll.setWidgetResizable(True)
    scroll.setWidget(widget)
    return scroll


class FigureStyleTool(ToolInstance):

    SESSION_ENDURING = False
    SESSION_SAVE = False

    def __init__(self, session, tool_name):
        super().__init__(session, tool_name)
        self.tool_window = MainToolWindow(self)
        self.templates = load_templates()
        self.current = None
        self._build_ui()
        self.tool_window.manage("side")

    def _row(self, layout, label_text, widget):
        row = QHBoxLayout()
        row.setSpacing(6)
        label = QLabel(label_text)
        label.setFixedWidth(_LABEL_WIDTH)
        row.addWidget(label)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row.addWidget(widget, 1)
        layout.addLayout(row)

    def _row_layout(self, layout, label_text, sub_layout):
        row = QHBoxLayout()
        row.setSpacing(6)
        label = QLabel(label_text)
        label.setFixedWidth(_LABEL_WIDTH)
        row.addWidget(label)
        row.addLayout(sub_layout, 1)
        layout.addLayout(row)

    def _section(self, layout, title, desc):
        header = QLabel(f"<b>{title}</b>")
        layout.addWidget(header)
        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(desc_label)

    def _panel(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setAlignment(Qt.AlignTop)
        widget.setLayout(layout)
        return widget, layout

    def _build_ui(self):
        container = QVBoxLayout()
        container.setContentsMargins(4, 4, 4, 4)
        container.setSpacing(0)
        self.tool_window.ui_area.setLayout(container)

        top = QHBoxLayout()
        top.setSpacing(6)
        container.addLayout(top)

        # --- Templates column ---
        left = QVBoxLayout()
        left.setSpacing(4)
        top.addLayout(left, 1)
        left.addWidget(QLabel("<b>TEMPLATES</b>"))
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        self.add_btn = QPushButton("+")
        self.add_btn.setToolTip("New template.")
        self.del_btn = QPushButton("–")
        self.del_btn.setToolTip("Delete selected (built-ins locked).")
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setToolTip("Duplicate selected.")
        for b in (self.add_btn, self.del_btn, self.copy_btn):
            btn_row.addWidget(b)
        left.addLayout(btn_row)

        self.list_widget = QListWidget()
        left.addWidget(self.list_widget)

        self.add_btn.clicked.connect(self._on_add)
        self.del_btn.clicked.connect(self._on_delete)
        self.copy_btn.clicked.connect(self._on_copy)
        self.list_widget.currentRowChanged.connect(self._on_select)

        # --- Right side: tabs ---
        right = QVBoxLayout()
        top.addLayout(right, 2)

        self.tabs = QTabWidget()
        right.addWidget(self.tabs)
        self.tabs.addTab(make_scrollable(self._build_style_tab()), "Style")
        self.tabs.addTab(make_scrollable(self._build_coloring_tab()), "Coloring")
        self.tabs.addTab(make_scrollable(self._build_export_tab()), "Image Export")
        self.tabs.addTab(make_scrollable(self._build_import_export_tab()), "Templates I/O")

        # --- Persistent actions: sibling of the tabs, always visible ---
        action_row = QHBoxLayout()
        self.apply_btn = QPushButton("Apply to Session")
        self.apply_btn.setToolTip("Apply this style to what's open now. Doesn't save.")
        self.save_btn = QPushButton("Save")
        self.save_btn.setToolTip("Save changes to this template. Doesn't touch the session.")
        action_row.addWidget(self.apply_btn)
        action_row.addWidget(self.save_btn)
        container.addLayout(action_row)

        self.apply_btn.clicked.connect(self._on_apply)
        self.save_btn.clicked.connect(self._on_save)

        self._refresh_list()

    def _build_style_tab(self):
        widget, layout = self._panel()

        self.name_edit = QLineEdit()
        self._row(layout, "Name:", self.name_edit)

        self._section(layout, "Appearance", "Lighting, background, camera.")

        self.lighting_combo = QComboBox()
        self.lighting_combo.addItems(["default", "simple", "full", "soft", "gentle", "flat"])
        self.lighting_combo.setToolTip("Lighting preset.")
        self._row(layout, "Lighting:", self.lighting_combo)

        self.lighting_shadows_check = QCheckBox()
        self.lighting_shadows_check.setChecked(True)
        self.lighting_shadows_check.setToolTip("Shadows on/off, independent of the preset.")
        self._row(layout, "Shadows:", self.lighting_shadows_check)

        self.lighting_intensity_spin = QDoubleSpinBox()
        self.lighting_intensity_spin.setRange(0.0, 5.0)
        self.lighting_intensity_spin.setSingleStep(0.1)
        self.lighting_intensity_spin.setToolTip("Key light brightness multiplier.")
        self._row(layout, "Intensity:", self.lighting_intensity_spin)

        bg_row = QHBoxLayout()
        bg_row.setSpacing(4)
        self.bg_edit = QLineEdit()
        self.bg_edit.setToolTip("Background hex color.")
        self.bg_pick_btn = QPushButton("Pick")
        bg_row.addWidget(self.bg_edit)
        bg_row.addWidget(self.bg_pick_btn)
        self._row_layout(layout, "Background:", bg_row)
        self.bg_pick_btn.clicked.connect(lambda: self._pick_color(self.bg_edit))

        self.silhouettes_check = QCheckBox()
        self.silhouettes_check.setToolTip("Outline around the structure.")
        self._row(layout, "Silhouettes:", self.silhouettes_check)

        self.silhouette_width_spin = QDoubleSpinBox()
        self.silhouette_width_spin.setRange(0.0, 20.0)
        self.silhouette_width_spin.setToolTip("Outline thickness (px).")
        self._row(layout, "Sil. width:", self.silhouette_width_spin)

        self.camera_combo = QComboBox()
        self.camera_combo.addItems(["ortho", "perspective"])
        self.camera_combo.setToolTip("ortho = no perspective distortion.")
        self._row(layout, "Camera:", self.camera_combo)

        self._section(
            layout, "Cartoon",
            "Backbone ribbon. Uncheck 'Custom cartoon style' for ChimeraX's default look.")

        self.show_cartoon_check = QCheckBox()
        self.show_cartoon_check.setChecked(True)
        self.show_cartoon_check.setToolTip("Show the ribbon at all.")
        self.show_cartoon_check.toggled.connect(self._on_show_cartoon_toggled)
        self._row(layout, "Show cartoon:", self.show_cartoon_check)

        self.cartoon_custom_style_check = QCheckBox()
        self.cartoon_custom_style_check.setChecked(True)
        self.cartoon_custom_style_check.setToolTip(
            "Off = ChimeraX's default helix/strand look, not this plugin's uniform style.")
        self.cartoon_custom_style_check.toggled.connect(self._on_cartoon_custom_style_toggled)
        self._row(layout, "Custom style:", self.cartoon_custom_style_check)

        self.helix_combo = QComboBox()
        self.helix_combo.addItems(["default", "tube", "wrap"])
        self.helix_combo.setToolTip("How helices are drawn.")
        self._row(layout, "Helix mode:", self.helix_combo)

        _xsection_items = ["oval", "rectangle", "barbell", "piping", "round", "square"]

        helix_group = QGroupBox("Helix shape")
        layout.addWidget(helix_group)
        helix_layout = QVBoxLayout()
        helix_layout.setSpacing(4)
        helix_group.setLayout(helix_layout)
        self.helix_xsection_combo = QComboBox()
        self.helix_xsection_combo.addItems(_xsection_items)
        self.helix_xsection_combo.setToolTip("Helix ribbon cross-section shape.")
        self._row(helix_layout, "Cross-section:", self.helix_xsection_combo)
        self.helix_width_spin = QDoubleSpinBox()
        self.helix_width_spin.setRange(0.1, 20.0)
        self._row(helix_layout, "Width:", self.helix_width_spin)
        self.helix_thickness_spin = QDoubleSpinBox()
        self.helix_thickness_spin.setRange(0.1, 20.0)
        self._row(helix_layout, "Thickness:", self.helix_thickness_spin)

        strand_group = QGroupBox("Strand (sheet) shape")
        layout.addWidget(strand_group)
        strand_layout = QVBoxLayout()
        strand_layout.setSpacing(4)
        strand_group.setLayout(strand_layout)
        self.strand_xsection_combo = QComboBox()
        self.strand_xsection_combo.addItems(_xsection_items)
        self.strand_xsection_combo.setToolTip(
            "Strand ribbon cross-section shape — 'rectangle' is the flat sheet look; if this is "
            "'oval' the sheet can look like a round tube and be hard to tell apart from a coil.")
        self._row(strand_layout, "Cross-section:", self.strand_xsection_combo)
        self.strand_width_spin = QDoubleSpinBox()
        self.strand_width_spin.setRange(0.1, 20.0)
        self._row(strand_layout, "Width:", self.strand_width_spin)
        self.strand_thickness_spin = QDoubleSpinBox()
        self.strand_thickness_spin.setRange(0.1, 20.0)
        self._row(strand_layout, "Thickness:", self.strand_thickness_spin)

        coil_group = QGroupBox("Coil shape")
        layout.addWidget(coil_group)
        coil_layout = QVBoxLayout()
        coil_layout.setSpacing(4)
        coil_group.setLayout(coil_layout)
        self.coil_xsection_combo = QComboBox()
        self.coil_xsection_combo.addItems(_xsection_items)
        self.coil_xsection_combo.setToolTip("Coil ribbon cross-section shape.")
        self._row(coil_layout, "Cross-section:", self.coil_xsection_combo)
        self.coil_thickness_spin = QDoubleSpinBox()
        self.coil_thickness_spin.setRange(0.1, 20.0)
        self._row(coil_layout, "Thickness:", self.coil_thickness_spin)

        self.cartoon_sides_spin = QSpinBox()
        self.cartoon_sides_spin.setRange(4, 24)
        self.cartoon_sides_spin.setSingleStep(2)
        self.cartoon_sides_spin.setToolTip("Roundness segments (even, 4-24).")
        self._row(layout, "Sides:", self.cartoon_sides_spin)

        self.arrows_check = QCheckBox()
        self.arrows_check.setToolTip("Arrowheads on strands.")
        self._row(layout, "Arrows:", self.arrows_check)

        self.arrows_helix_check = QCheckBox()
        self.arrows_helix_check.setToolTip("Arrowheads on helices too.")
        self._row(layout, "Arrows (helix):", self.arrows_helix_check)

        self.arrow_scale_spin = QDoubleSpinBox()
        self.arrow_scale_spin.setRange(1.0, 5.0)
        self.arrow_scale_spin.setToolTip("Arrowhead width multiplier.")
        self._row(layout, "Arrow scale:", self.arrow_scale_spin)

        self.divisions_spin = QSpinBox()
        self.divisions_spin.setRange(2, 40)
        self.divisions_spin.setToolTip("Smoothness per residue.")
        self._row(layout, "Divisions:", self.divisions_spin)

        self.bar_scale_spin = QDoubleSpinBox()
        self.bar_scale_spin.setRange(0.01, 5.0)
        self.bar_scale_spin.setSingleStep(0.1)
        self.bar_scale_spin.setToolTip("Barbell center thickness ratio (xsection=barbell).")
        self._row(layout, "Bar scale:", self.bar_scale_spin)

        self.bar_sides_spin = QSpinBox()
        self.bar_sides_spin.setRange(4, 24)
        self.bar_sides_spin.setSingleStep(2)
        self.bar_sides_spin.setToolTip("Barbell roundness segments (even, 4-24).")
        self._row(layout, "Bar sides:", self.bar_sides_spin)

        self.radius_edit = QLineEdit()
        self.radius_edit.setToolTip("Tube/cylinder radius: 'auto' or a number.")
        self._row(layout, "Radius:", self.radius_edit)

        self.worm_check = QCheckBox()
        self.worm_check.setToolTip("Smooth tube instead of ribbon.")
        self._row(layout, "Worm:", self.worm_check)

        self._section(layout, "Atoms", "Individual atoms/bonds alongside the cartoon.")

        self.show_atoms_check = QCheckBox()
        self.show_atoms_check.setToolTip("Show atoms/bonds.")
        self._row(layout, "Show atoms:", self.show_atoms_check)

        self.atom_style_combo = QComboBox()
        self.atom_style_combo.addItems(["ball", "sphere", "stick"])
        self.atom_style_combo.setToolTip("How atoms are drawn.")
        self._row(layout, "Style:", self.atom_style_combo)

        return widget

    def _build_export_tab(self):
        widget, layout = self._panel()

        self._section(layout, "Image Export", "Size/quality/format for saving a rendered image.")

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 20000)
        self.width_spin.setToolTip("Image width (px).")
        self._row(layout, "Width:", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 20000)
        self.height_spin.setToolTip("Image height (px).")
        self._row(layout, "Height:", self.height_spin)

        self.supersample_combo = QComboBox()
        self.supersample_combo.addItems(["1", "2", "4", "8"])
        self.supersample_combo.setToolTip("Anti-aliasing: higher = smoother, slower.")
        self._row(layout, "Supersample:", self.supersample_combo)

        self.image_format_combo = QComboBox()
        self.image_format_combo.addItems(["png", "jpeg", "tiff"])
        self.image_format_combo.setToolTip("Image file format.")
        self._row(layout, "Format:", self.image_format_combo)

        self.transparent_check = QCheckBox()
        self.transparent_check.setToolTip("Transparent background (png/tiff only).")
        self._row(layout, "Transparent:", self.transparent_check)

        self.save_image_btn = QPushButton("Save Image...")
        self.save_image_btn.setToolTip(
            "Choose where to save a rendered image with the settings above. Uses the current "
            "ChimeraX view — click 'Apply to Session' first if you haven't yet.")
        layout.addWidget(self.save_image_btn)
        self.save_image_btn.clicked.connect(self._on_save_image)

        return widget

    def _build_coloring_tab(self):
        widget, layout = self._panel()

        desc = QLabel("Optional coloring applied after the style above.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(desc)

        self.color_mode_combo = QComboBox()
        self.color_mode_combo.addItems([label for _, label in _COLOR_MODES])
        self._row(layout, "Color mode:", self.color_mode_combo)

        self.color_stack = QStackedWidget()
        layout.addWidget(self.color_stack)
        self.color_mode_combo.currentIndexChanged.connect(self.color_stack.setCurrentIndex)

        # None
        none_page = QLabel("No extra coloring.")
        self.color_stack.addWidget(none_page)

        # Single color
        single_page, single_layout = self._panel()
        single_layout.addWidget(QLabel("One solid color, whole structure or one chain."))
        single_row = QHBoxLayout()
        single_row.setSpacing(4)
        self.color_single_edit = QLineEdit()
        self.color_single_edit.setToolTip("Hex color.")
        single_pick_btn = QPushButton("Pick")
        single_pick_btn.clicked.connect(lambda: self._pick_color(self.color_single_edit))
        single_row.addWidget(self.color_single_edit)
        single_row.addWidget(single_pick_btn)
        self._row_layout(single_layout, "Color:", single_row)

        target_row = QHBoxLayout()
        target_row.setSpacing(4)
        self.color_single_target_combo = QComboBox()
        self.color_single_target_combo.setToolTip(
            "Restrict to one open chain, or leave as '(whole structure)'.")
        self.color_single_target_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedWidth(28)
        refresh_btn.setToolTip("Re-scan currently open models for chains.")
        refresh_btn.clicked.connect(lambda: self._refresh_chain_targets())
        target_row.addWidget(self.color_single_target_combo)
        target_row.addWidget(refresh_btn)
        self._row_layout(single_layout, "Chain:", target_row)

        self.color_stack.addWidget(single_page)

        # By chain
        chain_page, chain_layout = self._panel()
        chain_layout.addWidget(QLabel("Different color per chain."))
        self.chain_palette_combo = QComboBox()
        self.chain_palette_combo.addItems(_CHAIN_PALETTES)
        self.chain_palette_combo.setToolTip("Palette name.")
        self._row(chain_layout, "Palette:", self.chain_palette_combo)
        self.color_stack.addWidget(chain_page)

        # By B-factor
        bfactor_page, bfactor_layout = self._panel()
        bfactor_layout.addWidget(QLabel("Color by B-factor value."))
        self.bfactor_palette_combo = QComboBox()
        self.bfactor_palette_combo.addItems(_BFACTOR_PALETTES)
        self._row(bfactor_layout, "Palette:", self.bfactor_palette_combo)
        self.bfactor_min_spin = QDoubleSpinBox()
        self.bfactor_min_spin.setRange(-1000.0, 1000.0)
        self._row(bfactor_layout, "Min:", self.bfactor_min_spin)
        self.bfactor_max_spin = QDoubleSpinBox()
        self.bfactor_max_spin.setRange(-1000.0, 1000.0)
        self._row(bfactor_layout, "Max:", self.bfactor_max_spin)
        self.bfactor_key_check = QCheckBox()
        self.bfactor_key_check.setToolTip("Show color legend.")
        self._row(bfactor_layout, "Show key:", self.bfactor_key_check)
        self.color_stack.addWidget(bfactor_page)

        # By heteroatom
        het_page = QLabel("Color ligands/ions/waters by element.")
        self.color_stack.addWidget(het_page)

        # AlphaFold pLDDT
        af_page = QLabel(
            "Color by AlphaFold's per-residue confidence (pLDDT), stored in the B-factor "
            "column: blue = very high, cyan = confident, yellow = low, orange = very low.")
        af_page.setWordWrap(True)
        self.color_stack.addWidget(af_page)

        self._refresh_chain_targets()
        return widget

    def _build_import_export_tab(self):
        widget, outer = self._panel()

        json_group = QGroupBox("Templates (JSON)")
        outer.addWidget(json_group)
        json_layout = QVBoxLayout()
        json_layout.setSpacing(4)
        json_group.setLayout(json_layout)
        json_layout.addWidget(QLabel("Save/load the template list as JSON."))
        json_row = QHBoxLayout()
        json_row.setSpacing(4)
        self.export_btn = QPushButton("Export...")
        self.import_btn = QPushButton("Import...")
        self.import_btn.setToolTip("Same-named templates are overwritten, others added.")
        json_row.addWidget(self.export_btn)
        json_row.addWidget(self.import_btn)
        json_layout.addLayout(json_row)
        self.export_btn.clicked.connect(self._on_export)
        self.import_btn.clicked.connect(self._on_import)

        cxc_group = QGroupBox("ChimeraX Scripts (.cxc)")
        outer.addWidget(cxc_group)
        cxc_layout = QVBoxLayout()
        cxc_layout.setSpacing(4)
        cxc_group.setLayout(cxc_layout)
        cxc_layout.addWidget(QLabel("Save the template as a script, or run one."))
        cxc_row = QHBoxLayout()
        cxc_row.setSpacing(4)
        self.save_cxc_btn = QPushButton("Save as .cxc...")
        self.run_cxc_btn = QPushButton("Run .cxc...")
        cxc_row.addWidget(self.save_cxc_btn)
        cxc_row.addWidget(self.run_cxc_btn)
        cxc_layout.addLayout(cxc_row)
        self.save_cxc_btn.clicked.connect(self._on_save_cxc)
        self.run_cxc_btn.clicked.connect(self._on_run_cxc)

        preset_group = QGroupBox("ChimeraX Built-in Presets")
        outer.addWidget(preset_group)
        preset_layout = QVBoxLayout()
        preset_layout.setSpacing(4)
        preset_group.setLayout(preset_layout)
        preset_layout.addWidget(QLabel("Apply one of ChimeraX's own presets directly to the session."))
        self.preset_category_combo = QComboBox()
        self.preset_category_combo.currentTextChanged.connect(self._on_preset_category_changed)
        self._row(preset_layout, "Category:", self.preset_category_combo)
        self.preset_name_combo = QComboBox()
        self._row(preset_layout, "Preset:", self.preset_name_combo)
        preset_btn_row = QHBoxLayout()
        preset_btn_row.setSpacing(4)
        preset_refresh_btn = QPushButton("↻")
        preset_refresh_btn.setFixedWidth(28)
        preset_refresh_btn.setToolTip("Re-scan available presets.")
        preset_refresh_btn.clicked.connect(self._refresh_presets)
        self.load_preset_btn = QPushButton("Load")
        self.load_preset_btn.clicked.connect(self._on_load_preset)
        preset_btn_row.addWidget(preset_refresh_btn)
        preset_btn_row.addWidget(self.load_preset_btn)
        preset_layout.addLayout(preset_btn_row)
        self._refresh_presets()

        return widget

    # --- template list handling ---

    def _refresh_list(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for t in self.templates:
            self.list_widget.addItem(t.name)
        self.list_widget.blockSignals(False)

        if self.templates:
            self.list_widget.setCurrentRow(0)

    def _on_select(self, row):
        if row < 0 or row >= len(self.templates):
            self.current = None
            return
        self.current = self.templates[row]
        self._populate_form(self.current)

    def _on_show_cartoon_toggled(self, checked):
        self.cartoon_custom_style_check.setEnabled(checked)
        self._update_cartoon_style_fields_enabled()

    def _on_cartoon_custom_style_toggled(self, checked):
        self._update_cartoon_style_fields_enabled()

    def _update_cartoon_style_fields_enabled(self):
        enabled = self.show_cartoon_check.isChecked() and self.cartoon_custom_style_check.isChecked()
        for w in (self.helix_combo,
                  self.helix_xsection_combo, self.helix_width_spin, self.helix_thickness_spin,
                  self.strand_xsection_combo, self.strand_width_spin, self.strand_thickness_spin,
                  self.coil_xsection_combo, self.coil_thickness_spin,
                  self.cartoon_sides_spin, self.arrows_check,
                  self.arrows_helix_check, self.arrow_scale_spin, self.divisions_spin,
                  self.bar_scale_spin, self.bar_sides_spin, self.radius_edit, self.worm_check):
            w.setEnabled(enabled)

    def _color_mode_index(self, mode):
        for i, (value, _) in enumerate(_COLOR_MODES):
            if value == mode:
                return i
        return 0

    def _list_open_chains(self):
        try:
            from chimerax.atomic import Structure
        except ImportError:
            return []
        items = []
        for s in self.session.models.list(type=Structure):
            for c in s.chains:
                spec = f"#{s.id_string}{c.atomspec}"
                items.append((f"{spec} — {s.name}", spec))
        return items

    def _refresh_chain_targets(self):
        current = self.color_single_target_combo.currentData()
        self.color_single_target_combo.blockSignals(True)
        self.color_single_target_combo.clear()
        self.color_single_target_combo.addItem("(whole structure)", "")
        for label, spec in self._list_open_chains():
            self.color_single_target_combo.addItem(label, spec)
        idx = self.color_single_target_combo.findData(current)
        self.color_single_target_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.color_single_target_combo.blockSignals(False)

    def _refresh_presets(self):
        try:
            categories = list(self.session.presets.presets_by_category.keys())
        except Exception:
            categories = []
        self.preset_category_combo.blockSignals(True)
        self.preset_category_combo.clear()
        self.preset_category_combo.addItems(categories)
        self.preset_category_combo.blockSignals(False)
        self._on_preset_category_changed()

    def _on_preset_category_changed(self):
        self.preset_name_combo.clear()
        cat = self.preset_category_combo.currentText()
        try:
            names = list(self.session.presets.presets_by_category.get(cat, []))
        except Exception:
            names = []
        self.preset_name_combo.addItems(names)

    def _on_load_preset(self):
        cat = self.preset_category_combo.currentText()
        name = self.preset_name_combo.currentText()
        if not cat or not name:
            QMessageBox.warning(None, "FigureStyle", "No preset selected.")
            return
        from chimerax.core.commands import quote_if_necessary
        try:
            run(self.session, f"preset {quote_if_necessary(cat)} {quote_if_necessary(name)}")
        except Exception as e:
            self.session.logger.error(f"FigureStyle: could not load preset: {e}")
            QMessageBox.warning(None, "FigureStyle", f"Could not load preset: {e}")

    def _populate_form(self, t):
        self.name_edit.setText(t.name)
        self.lighting_combo.setCurrentText(t.lighting)
        self.lighting_shadows_check.setChecked(t.lighting_shadows)
        self.lighting_intensity_spin.setValue(t.lighting_intensity)
        self.bg_edit.setText(t.bg_color)
        self.transparent_check.setChecked(t.transparent_bg)
        self.silhouettes_check.setChecked(t.silhouettes)
        self.silhouette_width_spin.setValue(t.silhouette_width)
        self.camera_combo.setCurrentText(t.camera_mode)
        self.show_cartoon_check.setChecked(t.show_cartoon)
        self.cartoon_custom_style_check.setChecked(t.cartoon_custom_style)
        self.helix_combo.setCurrentText(t.cartoon_helix_mode)
        self.helix_xsection_combo.setCurrentText(t.cartoon_helix_xsection)
        self.helix_width_spin.setValue(t.cartoon_helix_width)
        self.helix_thickness_spin.setValue(t.cartoon_helix_thickness)
        self.strand_xsection_combo.setCurrentText(t.cartoon_strand_xsection)
        self.strand_width_spin.setValue(t.cartoon_strand_width)
        self.strand_thickness_spin.setValue(t.cartoon_strand_thickness)
        self.coil_xsection_combo.setCurrentText(t.cartoon_coil_xsection)
        self.coil_thickness_spin.setValue(t.cartoon_coil_thickness)
        self.cartoon_sides_spin.setValue(t.cartoon_sides)
        self.arrows_check.setChecked(t.cartoon_arrows)
        self.arrows_helix_check.setChecked(t.cartoon_arrows_helix)
        self.arrow_scale_spin.setValue(t.cartoon_arrow_scale)
        self.divisions_spin.setValue(t.cartoon_divisions)
        self.bar_scale_spin.setValue(t.cartoon_bar_scale)
        self.bar_sides_spin.setValue(t.cartoon_bar_sides)
        self.radius_edit.setText(t.cartoon_radius)
        self.worm_check.setChecked(t.cartoon_worm)
        self.show_atoms_check.setChecked(t.show_atoms)
        self.atom_style_combo.setCurrentText(t.atom_style)
        self.width_spin.setValue(t.image_width)
        self.height_spin.setValue(t.image_height)
        self.supersample_combo.setCurrentText(str(t.supersample))
        self.image_format_combo.setCurrentText(t.image_format)

        self.color_mode_combo.setCurrentIndex(self._color_mode_index(t.color_mode))
        self.color_single_edit.setText(t.color_single)
        self._refresh_chain_targets()
        idx = self.color_single_target_combo.findData(t.color_single_target)
        self.color_single_target_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.chain_palette_combo.setCurrentText(t.color_palette)
        self.bfactor_palette_combo.setCurrentText(t.bfactor_palette)
        self.bfactor_min_spin.setValue(t.bfactor_min)
        self.bfactor_max_spin.setValue(t.bfactor_max)
        self.bfactor_key_check.setChecked(t.bfactor_key)

    def _form_to_template(self, name):
        return FigureStyleTemplate(
            name=name,
            lighting=self.lighting_combo.currentText(),
            lighting_shadows=self.lighting_shadows_check.isChecked(),
            lighting_intensity=self.lighting_intensity_spin.value(),
            bg_color=self.bg_edit.text().strip(),
            transparent_bg=self.transparent_check.isChecked(),
            silhouettes=self.silhouettes_check.isChecked(),
            silhouette_width=self.silhouette_width_spin.value(),
            camera_mode=self.camera_combo.currentText(),
            show_cartoon=self.show_cartoon_check.isChecked(),
            cartoon_custom_style=self.cartoon_custom_style_check.isChecked(),
            cartoon_helix_mode=self.helix_combo.currentText(),
            cartoon_helix_xsection=self.helix_xsection_combo.currentText(),
            cartoon_helix_width=self.helix_width_spin.value(),
            cartoon_helix_thickness=self.helix_thickness_spin.value(),
            cartoon_strand_xsection=self.strand_xsection_combo.currentText(),
            cartoon_strand_width=self.strand_width_spin.value(),
            cartoon_strand_thickness=self.strand_thickness_spin.value(),
            cartoon_coil_xsection=self.coil_xsection_combo.currentText(),
            cartoon_coil_thickness=self.coil_thickness_spin.value(),
            cartoon_sides=self.cartoon_sides_spin.value(),
            cartoon_arrows=self.arrows_check.isChecked(),
            cartoon_arrows_helix=self.arrows_helix_check.isChecked(),
            cartoon_arrow_scale=self.arrow_scale_spin.value(),
            cartoon_divisions=self.divisions_spin.value(),
            cartoon_bar_scale=self.bar_scale_spin.value(),
            cartoon_bar_sides=self.bar_sides_spin.value(),
            cartoon_radius=self.radius_edit.text().strip() or "auto",
            cartoon_worm=self.worm_check.isChecked(),
            show_atoms=self.show_atoms_check.isChecked(),
            atom_style=self.atom_style_combo.currentText(),
            color_mode=_COLOR_MODES[self.color_mode_combo.currentIndex()][0],
            color_single=self.color_single_edit.text().strip(),
            color_single_target=self.color_single_target_combo.currentData() or "",
            color_palette=self.chain_palette_combo.currentText(),
            bfactor_palette=self.bfactor_palette_combo.currentText(),
            bfactor_min=self.bfactor_min_spin.value(),
            bfactor_max=self.bfactor_max_spin.value(),
            bfactor_key=self.bfactor_key_check.isChecked(),
            image_width=self.width_spin.value(),
            image_height=self.height_spin.value(),
            supersample=int(self.supersample_combo.currentText()),
            image_format=self.image_format_combo.currentText(),
        )

    # --- button handlers ---

    def _unique_name(self, base):
        existing = {t.name for t in self.templates}
        name = base
        i = 1
        while name in existing:
            i += 1
            name = f"{base} {i}"
        return name

    def _on_add(self):
        t = FigureStyleTemplate(name=self._unique_name("New Template"))
        self.templates.append(t)
        save_templates(self.templates)
        self._refresh_list()
        self.list_widget.setCurrentRow(len(self.templates) - 1)

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            None, "Export Templates", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            export_templates(self.templates, path)
        except OSError as e:
            QMessageBox.warning(None, "FigureStyle", f"Could not export: {e}")

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            None, "Import Templates", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            imported = import_templates(path)
        except (OSError, ValueError, TypeError) as e:
            QMessageBox.warning(None, "FigureStyle", f"Could not import: {e}")
            return
        existing = {t.name: i for i, t in enumerate(self.templates)}
        for t in imported:
            if t.name in existing:
                self.templates[existing[t.name]] = t
            else:
                self.templates.append(t)
        save_templates(self.templates)
        self._refresh_list()

    def _on_delete(self):
        if self.current is None:
            return
        if self.current.name in _DEFAULT_NAMES:
            QMessageBox.warning(None, "FigureStyle",
                                 "Built-in templates cannot be deleted.")
            return
        self.templates = [t for t in self.templates if t is not self.current]
        save_templates(self.templates)
        self._refresh_list()

    def _on_copy(self):
        if self.current is None:
            return
        t = dataclasses.replace(self.current, name=self._unique_name(self.current.name + " copy"))
        self.templates.append(t)
        save_templates(self.templates)
        self._refresh_list()
        self.list_widget.setCurrentRow(len(self.templates) - 1)

    def _pick_color(self, line_edit):
        from Qt.QtGui import QColor
        color = QColorDialog.getColor(QColor(line_edit.text() or "#ffffff"), None)
        if color.isValid():
            line_edit.setText(color.name())

    def _on_save(self):
        if self.current is None:
            return
        new_name = self.name_edit.text().strip()
        if not new_name:
            QMessageBox.warning(None, "FigureStyle", "Name cannot be empty.")
            return
        if new_name != self.current.name and new_name in {t.name for t in self.templates}:
            resp = QMessageBox.question(
                None, "FigureStyle",
                f"A template named '{new_name}' already exists. Overwrite it?",
                QMessageBox.Yes | QMessageBox.No)
            if resp != QMessageBox.Yes:
                return
            self.templates = [t for t in self.templates if t.name != new_name]
        updated = self._form_to_template(new_name)
        idx = self.templates.index(self.current)
        self.templates[idx] = updated
        self.current = updated
        save_templates(self.templates)
        self._refresh_list()
        self.list_widget.setCurrentRow(min(idx, len(self.templates) - 1))

    def _on_apply(self):
        name = self.current.name if self.current else "Untitled"
        t = self._form_to_template(name).resolve_for_session(self.session)
        for cmd in t.to_cxc():
            run(self.session, cmd)

    def _on_save_image(self):
        name = self.current.name if self.current else "Untitled"
        t = self._form_to_template(name)
        ext = _FORMAT_EXTENSIONS.get(t.image_format, "png")
        path, _ = QFileDialog.getSaveFileName(
            None, "Save Image", f"{name}.{ext}", f"Images (*.{ext})")
        if not path:
            return
        if not path.lower().endswith(f".{ext}"):
            path += f".{ext}"
        from chimerax.core.commands import quote_if_necessary
        try:
            run(self.session, t.export_cmd(quote_if_necessary(path)))
        except Exception as e:
            self.session.logger.error(f"FigureStyle: could not save image: {e}")
            QMessageBox.warning(None, "FigureStyle", f"Could not save image: {e}")

    def _on_save_cxc(self):
        name = self.current.name if self.current else "Untitled"
        t = self._form_to_template(name)
        path, _ = QFileDialog.getSaveFileName(
            None, "Save as .cxc", f"{name}.cxc", "ChimeraX Scripts (*.cxc)")
        if not path:
            return
        try:
            with open(path, "w") as f:
                f.write("\n".join(t.to_cxc()) + "\n")
        except OSError as e:
            QMessageBox.warning(None, "FigureStyle", f"Could not save .cxc: {e}")

    def _on_run_cxc(self):
        path, _ = QFileDialog.getOpenFileName(
            None, "Run .cxc", "", "ChimeraX Scripts (*.cxc)")
        if not path:
            return
        from chimerax.core.commands import quote_if_necessary
        try:
            run(self.session, f"open {quote_if_necessary(path)}")
        except Exception as e:
            self.session.logger.error(f"FigureStyle: could not run {path}: {e}")
            QMessageBox.warning(None, "FigureStyle", f"Could not run script: {e}")
