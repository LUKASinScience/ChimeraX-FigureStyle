# ChimeraX-FigureStyle

You rewrite the same lighting, background, cartoon-style, and export commands for every figure?
FigureStyle turns that into a one-click template: define lighting, per-secondary-structure cartoon
style, coloring (including AlphaFold pLDDT), and export settings once, save it under a name, and
apply it to any structure — from the GUI or the command line.

**Full walkthrough with screenshots: [GUIDE.md](GUIDE.md) or [https://lukasinscience.github.io/ChimeraX-FigureStyle/](live Guide) .**

## Opening the tool

- **Tools menu** → General → FigureStyle, or
- **Toolbar**: Graphics tab → Figure Style section → FigureStyle button, or
- **Command line**: `ui tool show "FigureStyle"`

The tool docks as a panel with a template list on the left and four tabs on the right: **Style**,
**Coloring**, **Image Export**, **Templates I/O**.

## Creating and editing a template

1. Click **+** in the template list to create a new blank template (or **Copy** to duplicate the
   selected one under a new name).
2. Edit its settings across the **Style** (lighting, background, cartoon, atoms), **Coloring**, and
   **Image Export** tabs.
3. Click **Save** (bottom of the panel, always visible) to write your changes back to the selected
   template. Save does *not* touch your current ChimeraX session.
4. Click **Apply to Session** to actually run the template's style on whatever is open right now.

Renaming: change the **Name** field on the Style tab, then **Save** — if the new name collides with
an existing template you'll be asked whether to overwrite it.

## Where templates are stored

Templates save themselves **automatically** — there's no separate "save to disk" step. Every time
you click **Save**, **+**, **Copy**, or delete a template, the full list is written to a JSON file
inside ChimeraX's own per-version data folder (via `chimerax.app_dirs.user_data_dir`):

- macOS: `~/Library/Application Support/ChimeraX/<version>/figure_style_templates.json`
- Windows/Linux: the equivalent per-user ChimeraX data folder for your platform/version

This means your templates **persist automatically across restarts** — close and reopen ChimeraX and
they're still there, no action needed. The three built-ins (Publication White, Dark EMDB, Minimal
Stick) are seeded automatically the first time the tool runs if that file doesn't exist yet.

## Deleting a template

Select it in the list and click **–**. The three built-in templates can't be deleted this way (to
avoid accidentally losing the starting points) — but they *can* be copied and the copy edited or
deleted freely. There's no undo for deletion, so use **Export...** first (below) if you want a
backup.

## Backing up / sharing templates (Templates I/O tab)

- **Export...** — save your entire template list to a JSON file you choose, anywhere on disk. Use
  this to back up your templates or move them to another computer.
- **Import...** — load templates from a JSON file. Templates with the same name as one you already
  have are overwritten; new names are added alongside your existing ones.
- **Save as .cxc...** — write the selected template's commands out as a standalone ChimeraX script,
  runnable outside this plugin entirely (`open mytemplate.cxc` in any ChimeraX).
- **Run .cxc...** — run any existing `.cxc` script file in the current session.
- **ChimeraX Built-in Presets** — apply one of ChimeraX's own built-in presets (e.g. "Publication 1
  (silhouettes)") directly, independent of your saved templates.

## CLI

```
figurestyle apply "Template Name"
```
Applies a saved template's style to the current session from the ChimeraX command line — useful in
scripts or when scripting a batch of figures yourself.

## Notes

- "Custom cartoon style" (Style tab) controls whether the plugin applies its own uniform ribbon
  shape to helices/strands/coils, or leaves ChimeraX's own default look (which distinguishes
  helices from strands) untouched — turn it off if secondary structure looks flattened after
  applying a template.
- Coloring's "Single color" mode can target a specific open chain (e.g. `#1/A`) instead of the whole
  structure; if that chain no longer exists when the template is applied later, it falls back to
  coloring the whole structure instead of erroring.
