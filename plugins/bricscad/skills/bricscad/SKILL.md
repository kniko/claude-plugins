---
name: bricscad
description: Draw and edit drawings in the user's live BricsCAD through the bricscad MCP server (tools named mcp__bricscad__* or mcp__plugin_bricscad_bricscad__*) - 2D plans, sections, elevations with Greek text, real measured dimensions and concrete hatches, and simple 3D solid models. Use whenever the user asks to draw, redraw, trace, update or dimension something in BricsCAD/AutoCAD/a .dwg, to turn a photo, sketch or scanned drawing into CAD, to build a 3D model of a space in CAD, or to change layers/walls/doors/beams in an open drawing. Covers the generator-script workflow (Python -> ASCII LISP -> load), Greek text escaping, dimensions, hatches, 3D extrusions and booleans, how to read results back (command returns nothing), and the pitfalls that hung or broke past sessions.
---

# BricsCAD via MCP

The `bricscad` MCP server (this plugin's `server/server.py`, run with `uv`) drives the user's running
BricsCAD (Windows, COM). If its tools are deferred, load them all with ToolSearch query `bricscad`. Tools:
`start_bricscad`, `status` (open docs + active), `open_drawing` (also *activates* an open doc),
`command` (param **`cmd`**: LISP or command line, async, returns only `"sent"`),
`entities` (by layer; gives handle, type, bbox, text, measurement of dims), `solids` (handle, layer,
bbox, volume), `layers` (with entity counts), `extents`, `measure`, `delete` (handles), `save`,
`export_geometry` (JSON of 2D geometry; `server/blender_import.py` imports it into Blender), `export_dxf`, `plot_pdf`, `zoom`, `screenshot`, blocks/insert/layouts.
With the **ClaudeBridge add-in** (below) also: `lisp` (returns the value), `selection`, `bridge_status`,
`cancel`, `bridge_load`.

## ClaudeBridge add-in (use it when you can)

A .NET add-in (`bridge/bin/ClaudeBridge.dll`) running inside BricsCAD, answering on a named pipe. Load it
once per BricsCAD session with `bridge_load` - **ask the user to save open drawings first** (an add-in
crash closes BricsCAD; it cannot be unloaded until BricsCAD restarts). Then:
- `lisp(expr, timeout=60)` returns `{"ok":true,"result":"<prin1 value>"}` or `{"ok":false,"error":...}`:
  no log files needed. Greek text can be passed as-is. Multi-line/long code is fine (sent via a temp file).
  `command` with a LISP string is routed to `lisp` automatically.
- `command` with a plain command line is queued without blocking.
- If BricsCAD is busy (command waiting for input, open dialog, LISP waiting on `getpoint`) you get
  `{"status":"busy", "state":{"cmdnames":...}}` within the timeout instead of a hang. Then `cancel`
  (Esc x2) - only for something *you* started; otherwise tell the user what is blocking.
- `selection` - `current` pickfirst set and `last` non-empty selection (kept after the user clears it),
  each with handle/type/layer/bbox. Use it when the user says "this one" / "the selected beam".
- FILEDIA/CMDDIA are 0 while your LISP runs and restored after, so file prompts stay on the command line.
- Rebuild: `dotnet build -c Release -o ..\bin` in `bridge/src` (.NET 8 SDK). A new DLL needs a BricsCAD
  restart. To test a change side by side, build with `-p:DefineConstants=TESTBUILD
  -p:AssemblyName=ClaudeBridgeTn`: that copy listens on `claude-bricscad-ClaudeBridgeTn` and logs to
  `%TEMP%\claude-bricscad-ClaudeBridgeTn.log`.

Without the add-in, `command` (and `bridge_load` itself) go through COM `SendCommand`, which **blocks
until the command ends** - `'_LINE '` alone, and once `bridge_load` right after a fresh start, hung the MCP
for 30 min. Since 1.1.1 the server refuses when BricsCAD's main window is disabled (modal dialog - it
names the dialog) or a command is active, and gives up waiting after 15 s instead of hanging. When you
get such a reply, tell the user what is waiting in BricsCAD; don't retry blindly.
NETLOAD with a PVcase drawing (Sagia, MESSARITIS) active froze BricsCAD at 100% CPU before .NET started;
`bridge_load` therefore loads from a temporary blank drawing and switches back (1.1.2, ~2 s).
`start_bricscad` starts bricscad.exe as a normal program (a COM-launched BricsCAD could close together with
the MCP server). After starting, wait until the user confirms startup dialogs are gone before `bridge_load`.

## Workflow that works

1. **Never draw entity-by-entity with tool calls.** Write a Python *generator* that emits a `.lsp`
   file, then `command` → `(load "C:/.../file.lsp")` (forward slashes). Keep all dimensions as named
   variables at the top of the generator (measured values, with comments on where each came from), so a
   corrected measurement is a one-line change + regenerate.
2. Use `scripts/cadlisp.py` (tested): `begin(layers=...)`, `line/pline/arc/text/solid/arrowhead/level`,
   `concrete(pts)` (outline + hatch), `dim(...)`, `ext3d/box` (3D), `log(...)`, `end(path, log=...)`.
   Set `cadlisp.OFFSET` to place a section/elevation/3D model beside the plan in the same model space.
   Worked example of a full set (plan, section, elevation, 3D) in `references/example-deh-substation/`.
3. **Read results back**: with the add-in, `lisp '(load "C:/.../file.lsp")'` returns the value of the
   file's last expression (make it a summary list). Without it, `command` gives no output, so LISP writes
   to a log (`end(..., log=path)` / `logw`) and you `cat` it; if the log is missing, check again before
   assuming failure.
4. Verify numerically, not with screenshots: `entities` (dim `measurement`, text, bbox), `solids`
   (volume + bbox), `layers` counts. For a visual check, `export_geometry` + `scripts/render_geom.py`
   → PNG you can Read. `screenshot` is unreliable (other windows - TeamViewer, Claude - cover BricsCAD).
5. `save` after each accepted step. Several docs are often open - check `status` → `active` before
   writing; use `open_drawing` with the path to switch. Test new LISP in an empty `Drawing1.dwg`, not the
   user's file.

## Rules the user cares about

- **Dimensions show the measured value** - draw the geometry to the measured size and use real
  `DIMLINEAR`/`DIMALIGNED`; never type a number as a text override. Round values (e.g. 1.90) stay round.
- Each building element on **its own layer** so it can be toggled (e.g. `3D_ROOF_SLAB`,
  `3D_ROOF_RECESS`, `3D_BEAMS`, `3D_BASIN_WALLS`, `LIFT`). Ask before merging layers.
- Don't delete or replace something the user drew without saying so (e.g. their own dim on layer 0).
- Existing vs new state: keep the as-built drawing as `<name> - ΥΦΙΣΤΑΜΕΝΗ.dwg`, work on a copy
  `<name> - ΝΕΑ.dwg`.
- When the user points at an element in a screenshot, identify it by bbox from `solids`/`entities`
  (the 4-entity pick list in their image names the layers under the cursor) and **state which one you
  think it is** before changing it - once a neighbouring wall was changed by mistake. Best: ask them to
  select it and call `selection` (add-in). Without the add-in `(ssget "_I")` usually returns nothing.

## LISP details

- **Files must be ASCII.** Greek → `\U+XXXX`, written as `\\U+XXXX` inside the LISP string in the file
  (`esc()` does it). Text style `GR` = arial.ttf (created by `begin`).
- Entities via `entmake` (LINE, LWPOLYLINE with group 38 = elevation, ARC angles in radians CCW, SOLID
  with vertex order 1-2-4-3, TEXT with 72/73 + 11 for centred).
- Dims: `(command "_.DIMLINEAR" "_non" p1 "_non" p2 "_non" loc)` with OSMODE 0. A vertical dim needs
  `loc` y **between** the two points (or the `_V` option), else it comes out horizontal = 0.00.
- Hatch: `vla-AddHatch ms 1 pat :vlax-true` + `AppendOuterLoop` + `Evaluate`. `AR-CONC` is missing in
  this install → fallback `ANSI31` scale 0.02 (concrete), 0.08 (earth).
- Linetypes DASHED/CENTER/HIDDEN loaded by `begin` from default.lin/iso.lin; `LTSCALE` 0.25 for metres.
- Changing an existing entity: `entget` → `subst` → `entmod` (layer 8, linetype 6 - use `"BYLAYER"` to
  reset). `entdel` inside `foreach` over a selection sometimes leaves items - use the `delete` tool.
- Deleting a region to regenerate it: select by `vla-getboundingbox` ranges in LISP, and **exclude
  `AcDb3dSolid`** if a 3D model lives in the same model space.
- Layer table: `entmake` LAYER with negative colour = created OFF; delete an emptied layer with
  `vla-Delete` on `(vla-item (vla-get-Layers doc) name)` in `vl-catch-all-apply`.

## 3D

- `ext3d(layer, outline, z0, z1)`: closed LWPOLYLINE at z0 → `vla-AddRegion` → `vla-AddExtrudedSolid`.
  Use real levels as z (e.g. floor -2.00, ceiling +0.925) and the plan's x/y + an OFFSET.
- Openings/cuts: make the tool solid, then `vla-Boolean target 2 tool` (2 = subtract) - see
  `subtract_last_from`. Rings (basin walls) = outer minus inner.
- Model elements as separate solids per layer: walls, beams (only the drop below the slab), slabs,
  stairs (one block per tread), doors (one solid per leaf), equipment. Check with `solids` volumes.
- View (tested): `(command "_.-VIEW" "_SEISO")`, `(command "_.ZOOM" "_O" (ssget "_X" (list (cons 8 "3D_*"))) "")`,
  `(command "_.SHADEMODE" "_G")` (Gouraud); `_.PLAN` returns to the top view. Turn roof layers off to see inside.

## Pitfalls that cost time

- **Never `PNGOUT`** - it hung the MCP for 30 min and dropped the connection. Recovery:
  `start_bricscad`, set `FILEDIA` back to 1, `save`.
- `plot_pdf` can open a "Save As" dialog of the PDF driver that blocks everything; cancel it from
  outside (PowerShell: find the dialog of process `pdfSaverL`, PostMessage WM_COMMAND IDCANCEL).
- `plot_pdf` on `Model` plots the **current display** (a 3D iso view comes out skewed): run
  `(command "_.PLAN" "_W")` + `_.ZOOM _W` first and plot in the *next* call (`command` is async). BricsCAD then
  keeps the PDF locked - a second plot to the same path silently does nothing; plot to a new path and copy.
- `_DIMLINEAR` between two points with the same x can still come out horizontal = 0.00: pass `"_V"` before the
  location point; check `measurement` with `entities` after every dim batch.
- Python `exec`-style helper tricks inside generators broke; keep generators plain scripts.
- Scanned PDFs (CCITT G4): `uv run --with pymupdf python -I` renders pages to PNG; without it, wrap the
  G4 stream in a TIFF header by hand and crop/rotate with PowerShell `System.Drawing`. Calibrate the
  scale from two known levels/dimensions on the same sheet.

## Reading the user's sketches

Site sketches are often rotated relative to the drawing - map sketch sides to plan axes explicitly
and confirm. Ask what an ambiguous mark is (niche vs step, door vs wall, beam vs wall, hatched = door)
rather than guessing; record the answer as a comment next to the variable in the generator.
