# bricscad

[Ελληνικά](README.md) · **English**

Drive a running **BricsCAD** (Windows, V26, COM automation) from Claude Code.

- **MCP server** `bricscad` (`server/server.py`, run with `uv`): status, open/save drawings, LISP and command
  line, entities/solids/layers/extents queries, delete, zoom, screenshot, plot to PDF, DXF export, and
  `export_geometry` (JSON; `server/blender_import.py` brings it into Blender).
- **Skill** `bricscad`: how to draw plans, sections and elevations with Greek text, measured dimensions,
  concrete hatches and 3D solids - Python generators that write ASCII LISP (`scripts/cadlisp.py`),
  reading results back, and the pitfalls (PNGOUT hang, PDF Save As dialog, lost selections).

## Requirements

- Windows with BricsCAD running (or let `start_bricscad` launch it).
- [`uv`](https://docs.astral.sh/uv/) on PATH (`winget install astral-sh.uv`); the server's dependencies
  (`mcp`, `pywin32`, `pillow`) are installed by `uv` on first run.

## Install

```bash
claude plugin marketplace add kniko/claude-plugins
claude plugin install bricscad@kniko-tools
```

If you had the server added by hand before (`claude mcp add bricscad ...`), remove that entry
(`claude mcp remove bricscad -s user`) so it does not run twice.
