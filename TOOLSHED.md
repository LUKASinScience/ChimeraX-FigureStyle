# FigureStyle

You rewrite the same lighting, background, cartoon-style, and export commands for every figure?
FigureStyle turns that into a one-click template: define lighting, per-secondary-structure cartoon
style, coloring (including AlphaFold pLDDT), and export settings once, save it under a name, and
apply it to any structure — from the GUI or the command line.

## Features

- **Named style templates** — lighting (preset, shadows, intensity), background color/transparency,
  silhouettes, camera mode, per-type cartoon styling (helix/strand/coil each get their own
  cross-section, width, thickness), and atom display, all saved under a name you choose.
- **Structured coloring** — single color (whole structure or one chain), by-chain rainbow palettes,
  by-B-factor, by-heteroatom, or AlphaFold pLDDT confidence coloring.
- **Image export** — width/height/supersample/format (PNG, JPEG, TIFF), transparent background where
  the format supports it.
- **Templates persist automatically** across ChimeraX restarts — no manual save step.
- **JSON export/import** to back up or share templates between machines.
- **.cxc script export** — turn any template into a standalone ChimeraX script that runs without
  the plugin installed.
- **CLI command**: `figurestyle apply "Template Name"` — apply a saved style from scripts or the
  ChimeraX command line.
- **Built-in preset loader** — apply any of ChimeraX's own built-in presets directly from the same
  panel.
- Three ready-to-use starting templates: Publication White, Dark EMDB, Minimal Stick.

## Getting started

Install from the Toolshed, then open it via **Tools → General → FigureStyle**, the **Graphics** tab
toolbar button, or the command line: `ui tool show "FigureStyle"`.

## Citation

If FigureStyle helped produce a figure in a paper or presentation, a mention of "ChimeraX-FigureStyle
(Lukas W. Bauer)" is appreciated but not required.

## License

MIT — see `LICENSE.txt`.

## Authors

Lukas W. Bauer, with AI-assisted development by Claude (Anthropic).
