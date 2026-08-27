from dataclasses import dataclass, asdict, replace, fields
import json
import pathlib


@dataclass
class FigureStyleTemplate:
    name: str

    # Lighting
    lighting: str = "soft"            # "default" | "simple" | "full" | "soft" | "gentle" | "flat"
    lighting_shadows: bool = True
    lighting_intensity: float = 1.0

    # Background
    bg_color: str = "#ffffff"         # hex color
    transparent_bg: bool = True

    # Silhouettes
    silhouettes: bool = True
    silhouette_width: float = 3.0

    # Camera
    camera_mode: str = "ortho"        # "ortho" | "perspective"

    # Cartoon — protein
    show_cartoon: bool = True
    cartoon_custom_style: bool = True     # False = keep ChimeraX's own default helix/strand look
    cartoon_helix_mode: str = "default"   # "default" | "tube" | "wrap"
    # xsection values: "oval" | "rectangle" | "barbell" | "piping" | "round" | "square"
    cartoon_helix_xsection: str = "oval"
    cartoon_helix_width: float = 2.0
    cartoon_helix_thickness: float = 2.0
    cartoon_strand_xsection: str = "rectangle"
    cartoon_strand_width: float = 2.0
    cartoon_strand_thickness: float = 2.0
    cartoon_coil_xsection: str = "oval"
    cartoon_coil_thickness: float = 2.0   # width doesn't apply to coil
    cartoon_sides: int = 12               # even integer, 4-24: segments for tube/oval cross-sections
    cartoon_arrows: bool = False
    cartoon_arrows_helix: bool = False
    cartoon_arrow_scale: float = 2.0      # 1.0-5.0
    cartoon_divisions: int = 20           # 2-40
    cartoon_bar_scale: float = 0.5
    cartoon_bar_sides: int = 18           # even integer, 4-24
    cartoon_radius: str = "auto"          # "auto" or a number > 0
    cartoon_worm: bool = False            # smooth worm/tube through the backbone

    # Atoms
    show_atoms: bool = False
    atom_style: str = "stick"         # "ball" | "sphere" | "stick"

    # Coloring (V2) — structured, verified against the real ChimeraX command parser
    color_mode: str = "none"          # "none" | "single" | "chain" | "bfactor" | "heteroatom" | "alphafold"
    color_single: str = "#ffff00"
    color_single_target: str = ""     # e.g. "#1/A"; empty = whole structure
    color_palette: str = "pastel2-4"          # for "chain" mode (rainbow palette)
    bfactor_palette: str = "blue:white:red"   # for "bfactor" mode
    bfactor_min: float = 0.0
    bfactor_max: float = 40.0
    bfactor_key: bool = True

    # Export
    image_width: int = 2400
    image_height: int = 2400
    supersample: int = 4              # 1 | 2 | 4 | 8
    image_format: str = "png"         # "png" | "jpeg" | "tiff"

    def to_cxc(self) -> list[str]:
        """Return list of ChimeraX commands that apply this template."""
        sil = "true" if self.silhouettes else "false"
        arrows = "true" if self.cartoon_arrows else "false"
        arrows_helix = "true" if self.cartoon_arrows_helix else "false"
        worm = "true" if self.cartoon_worm else "false"
        shadows = "true" if self.lighting_shadows else "false"
        cmds = [
            f"lighting {self.lighting} shadows {shadows} intensity {self.lighting_intensity}",
            f"set bgColor {self.bg_color}",
            f"graphics silhouettes {sil} width {self.silhouette_width}",
            f"camera {'ortho' if self.camera_mode == 'ortho' else 'mono'}",
        ]
        if self.show_cartoon:
            if self.cartoon_custom_style:
                cmds.append(
                    f"cartoon style helix xsection {self.cartoon_helix_xsection} "
                    f"width {self.cartoon_helix_width} thickness {self.cartoon_helix_thickness}")
                cmds.append(
                    f"cartoon style strand xsection {self.cartoon_strand_xsection} "
                    f"width {self.cartoon_strand_width} thickness {self.cartoon_strand_thickness}")
                cmds.append(
                    f"cartoon style coil xsection {self.cartoon_coil_xsection} "
                    f"thickness {self.cartoon_coil_thickness}")
                cmds.append(
                    f"cartoon style protein modeHelix {self.cartoon_helix_mode} "
                    f"sides {self.cartoon_sides} worm {worm} "
                    f"divisions {self.cartoon_divisions} radius {self.cartoon_radius} "
                    f"barScale {self.cartoon_bar_scale} barSides {self.cartoon_bar_sides}")
                cmds.append(
                    f"cartoon style protein arrows {arrows} arrowsHelix {arrows_helix} "
                    f"arrowScale {self.cartoon_arrow_scale}")
            else:
                # Explicitly restore ChimeraX's real per-type initial defaults — skipping the
                # commands above isn't enough, since a previous apply may have already changed
                # the style and nothing would undo it.
                cmds.append(
                    "cartoon style helix modeHelix default xsection oval width 2.0 thickness 0.4")
                cmds.append("cartoon style strand xsection rectangle width 2.0 thickness 0.4")
                cmds.append("cartoon style coil xsection oval thickness 0.4")
                cmds.append("cartoon style nucleic xsection rectangle width 2.0 thickness 0.4")
                cmds.append(
                    "cartoon style protein sides 12 arrows true arrowsHelix false "
                    "arrowScale 2.0 barScale 0.5 barSides 18 radius auto worm false")
        else:
            cmds.append("hide cartoon")
        if not self.show_atoms:
            cmds.append("hide atoms")
        else:
            cmds.append("show atoms")
            cmds.append(f"style {self.atom_style}")
        if self.color_mode == "single":
            if self.color_single_target:
                cmds.append(f"color {self.color_single_target} {self.color_single}")
            else:
                cmds.append(f"color {self.color_single}")
        elif self.color_mode == "chain":
            cmds.append(f"rainbow palette {self.color_palette}")
        elif self.color_mode == "bfactor":
            key = "true" if self.bfactor_key else "false"
            cmds.append(
                f"color bfactor palette {self.bfactor_palette} "
                f"range {self.bfactor_min},{self.bfactor_max} key {key}")
        elif self.color_mode == "heteroatom":
            cmds.append("color byhetero")
        elif self.color_mode == "alphafold":
            cmds.append("color bfactor palette alphafold range 0,100 key true")
        return cmds

    def export_cmd(self, path: str) -> str:
        # JPEG has no alpha channel — never request transparency for it.
        transparent = "true" if (self.transparent_bg and self.image_format != "jpeg") else "false"
        return (f"save {path} width {self.image_width} height {self.image_height} "
                f"supersample {self.supersample} transparentBackground {transparent}")

    def resolve_for_session(self, session) -> "FigureStyleTemplate":
        """Return self, or a copy with an invalid color_single_target cleared."""
        if self.color_mode != "single" or not self.color_single_target:
            return self
        try:
            from chimerax.atomic import Structure
        except ImportError:
            return self
        for s in session.models.list(type=Structure):
            for c in s.chains:
                if f"#{s.id_string}{c.atomspec}" == self.color_single_target:
                    return self
        return replace(self, color_single_target="")


DEFAULT_TEMPLATES = [
    FigureStyleTemplate(
        name="Publication White",
        lighting="soft", bg_color="#ffffff", transparent_bg=True,
        silhouettes=True, silhouette_width=3.0,
        camera_mode="ortho",
        cartoon_helix_mode="tube",
        cartoon_arrows=True,
        show_atoms=False,
        image_width=2400, image_height=2400, supersample=4,
    ),
    FigureStyleTemplate(
        name="Dark EMDB",
        lighting="full", bg_color="#1a1a1a", transparent_bg=False,
        silhouettes=False, silhouette_width=3.0,
        camera_mode="perspective",
        cartoon_helix_mode="tube",
        cartoon_helix_width=2.5, cartoon_helix_thickness=2.5,
        cartoon_strand_width=2.5, cartoon_strand_thickness=2.5,
        cartoon_coil_thickness=2.5,
        cartoon_arrows=False,
        show_atoms=False,
        image_width=2400, image_height=2400, supersample=4,
    ),
    FigureStyleTemplate(
        name="Minimal Stick",
        lighting="simple", bg_color="#ffffff", transparent_bg=True,
        silhouettes=False,
        camera_mode="perspective",
        show_atoms=True, atom_style="stick",
        image_width=1800, image_height=1800, supersample=2,
    ),
]


def _template_path() -> pathlib.Path:
    try:
        import chimerax
        data_dir = pathlib.Path(chimerax.app_dirs.user_data_dir)
        return data_dir / "figure_style_templates.json"
    except (ImportError, AttributeError):
        return pathlib.Path.home() / ".figure_style_templates.json"


def export_templates(templates: list[FigureStyleTemplate], path) -> None:
    with open(path, "w") as f:
        json.dump([asdict(t) for t in templates], f, indent=2)


_FIELD_NAMES = {f.name for f in fields(FigureStyleTemplate)}


def import_templates(path) -> list[FigureStyleTemplate]:
    with open(path) as f:
        data = json.load(f)
    templates = []
    for entry in data:
        # Drop stale keys from an older schema version instead of crashing — the plugin has
        # renamed/removed fields before, and existing saved JSON shouldn't stop loading.
        filtered = {k: v for k, v in entry.items() if k in _FIELD_NAMES}
        templates.append(FigureStyleTemplate(**filtered))
    return templates


def load_templates() -> list[FigureStyleTemplate]:
    path = _template_path()
    if not path.exists():
        save_templates(DEFAULT_TEMPLATES)
        return list(DEFAULT_TEMPLATES)
    return import_templates(path)


def save_templates(templates: list[FigureStyleTemplate]) -> None:
    export_templates(templates, _template_path())
