# bricscad

[Ελληνικά](README.md) · **English**

Drive a running **BricsCAD** (Windows, V26, COM automation) from Claude Code.

- **MCP server** `bricscad` (`server/server.py`, run with `uv`): status, open/save drawings, LISP and command
  line, entities/solids/layers/extents queries, delete, zoom, screenshot, plot to PDF, DXF export, and
  `export_geometry` (JSON; `server/blender_import.py` brings it into Blender).
- **Skill** `bricscad`: how to draw plans, sections and elevations with Greek text, measured dimensions,
  concrete hatches and 3D solids - Python generators that write ASCII LISP (`scripts/cadlisp.py`),
  reading results back, and the pitfalls (PNGOUT hang, PDF Save As dialog, lost selections).
- **ClaudeBridge add-in** (`bridge/`, C# .NET 8, loaded into BricsCAD with the `bridge_load` tool): a named
  pipe (current Windows user only) that gives the MCP `lisp` with return values, the user's `selection`,
  `bridge_status`, `cancel`, and commands that answer "busy" instead of hanging on a dialog or prompt.
  `bridge/bin/ClaudeBridge.dll` is prebuilt; to rebuild: `dotnet build -c Release -o ..\bin` in
  `bridge/src` (.NET 8 SDK, BricsCAD V26 installed; other folder: set `BRICSCAD_DIR`).

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
