# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=1.2,<2", "pywin32>=306", "pillow>=10"]
# ///
"""MCP server that drives a running BricsCAD (V26) through its COM automation interface."""
import glob
import json
import os
import subprocess
import threading
import time

import pythoncom
import win32com.client
from mcp.server.fastmcp import FastMCP

PROGIDS = ("BricscadApp.AcadApplication", "BricscadApp.AcadApplication.26")
mcp = FastMCP("bricscad")


def _app(start: bool = False):
    pythoncom.CoInitialize()
    for pid in PROGIDS:
        try:
            return win32com.client.GetActiveObject(pid)
        except Exception:
            continue
    if start:
        # Start bricscad.exe as a normal program. A COM-launched instance (Dispatch) is owned by this
        # process and can close when the MCP server goes away, taking unsaved work with it.
        exe = _bricscad_exe()
        if exe:
            subprocess.Popen([exe], close_fds=True,
                             creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
            for _ in range(120):
                time.sleep(1)
                for pid in PROGIDS:
                    try:
                        return win32com.client.GetActiveObject(pid)
                    except Exception:
                        continue
            raise RuntimeError(f"started {exe} but it did not register for COM in 120 s - is a dialog open?")
        app = win32com.client.Dispatch(PROGIDS[0])
        app.Visible = True
        return app
    raise RuntimeError("BricsCAD is not running. Start it (or call start_bricscad).")


def _bricscad_exe():
    if os.environ.get("BRICSCAD_EXE") and os.path.exists(os.environ["BRICSCAD_EXE"]):
        return os.environ["BRICSCAD_EXE"]
    found = sorted(glob.glob(os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                                          "Bricsys", "BricsCAD V*", "bricscad.exe")))
    return found[-1] if found else None


def _bricscad_windows() -> dict:
    """Visible top-level windows of bricscad.exe: is the main window enabled (False = a modal dialog is
    open) and the titles of dialog-like windows. Pure Win32, works even while BricsCAD is blocked."""
    import win32api
    import win32con
    import win32gui
    import win32process
    res = {"main_enabled": None, "dialogs": []}
    exes = {}

    def is_bcad(pid):
        if pid not in exes:
            try:
                hp = win32api.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
                exes[pid] = win32process.GetModuleFileNameEx(hp, 0).lower().endswith("bricscad.exe")
                win32api.CloseHandle(hp)
            except Exception:
                exes[pid] = False
        return exes[pid]

    def cb(h, _):
        if win32gui.IsWindowVisible(h) and is_bcad(win32process.GetWindowThreadProcessId(h)[1]):
            title, cls = win32gui.GetWindowText(h), win32gui.GetClassName(h)
            if cls == "BricscadMainWindow":
                res["main_enabled"] = bool(win32gui.IsWindowEnabled(h))
                res["title"] = title
            elif win32gui.IsWindowEnabled(h) and title not in ("", "mini-command-line-frame"):
                owned.append(f"{title} [{cls}]")
        return True

    owned = []
    try:
        win32gui.EnumWindows(cb, None)
    except Exception:
        pass
    if res["main_enabled"] is False:          # modal: the enabled windows are the dialog(s)
        res["dialogs"] = owned
    return res


def _send_com(text: str, timeout: float = 15.0) -> str:
    """COM SendCommand with a guard: it blocks until the command ends, so refuse if a modal dialog is
    open and give up waiting after `timeout` s (the command stays queued in BricsCAD)."""
    w = _bricscad_windows()
    if w["main_enabled"] is False:
        return ("BricsCAD is blocked by a dialog: " + (", ".join(w["dialogs"]) or "unknown") +
                ". Ask the user to answer/close it in BricsCAD, then retry.")
    try:
        active = _doc().GetVariable("CMDNAMES")
        if active:
            return f"BricsCAD is busy: command '{active}' is running. Ask the user to finish or cancel it (Esc)."
    except Exception:
        pass
    err = []

    def run():
        try:
            pythoncom.CoInitialize()
            _doc().SendCommand(text)
        except Exception as e:
            err.append(str(e))

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        w = _bricscad_windows()
        return (f"still running after {timeout:.0f} s: BricsCAD is waiting for input or a dialog"
                + (": " + ", ".join(w["dialogs"]) if w["dialogs"] else "") +
                ". Tell the user what is waiting; do not send more commands until it is done.")
    return "error: " + err[0] if err else "sent"


def _doc():
    app = _app()
    if app.Documents.Count == 0:
        app.Documents.Add()
    return app.ActiveDocument


def _pt(p):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [float(v) for v in (list(p) + [0, 0, 0])[:3]])


def _ent(e, detail=False):
    d = {"handle": e.Handle, "type": e.ObjectName, "layer": e.Layer}
    try:
        lo, hi = e.GetBoundingBox()
        d["bbox"] = [[round(v, 4) for v in lo], [round(v, 4) for v in hi]]
    except Exception:
        pass
    n = e.ObjectName
    try:
        if n == "AcDbLine":
            d["start"], d["end"] = list(e.StartPoint), list(e.EndPoint)
        elif n in ("AcDbPolyline", "AcDb2dPolyline", "AcDb3dPolyline"):
            c = list(e.Coordinates)
            step = 2 if n == "AcDbPolyline" else 3
            d["points"] = [c[i:i + step] for i in range(0, len(c), step)] if detail or len(c) < 200 else f"{len(c)//step} pts"
            d["closed"] = bool(e.Closed)
        elif n in ("AcDbCircle", "AcDbArc"):
            d["center"], d["radius"] = list(e.Center), e.Radius
        elif n in ("AcDbText", "AcDbMText"):
            d["text"] = e.TextString
            d["insert"] = list(e.InsertionPoint)
        elif n == "AcDbBlockReference":
            d["block"], d["insert"] = e.EffectiveName if hasattr(e, "EffectiveName") else e.Name, list(e.InsertionPoint)
            d["rotation"] = e.Rotation
        elif n.startswith("AcDb") and "Dimension" in n:
            d["measurement"] = e.Measurement
    except Exception:
        pass
    return d


@mcp.tool()
def start_bricscad() -> str:
    """Start BricsCAD (or attach to the running one) and report version and open drawings."""
    app = _app(start=True)
    return status()


@mcp.tool()
def status() -> str:
    """BricsCAD version, open drawings and the active drawing."""
    app = _app()
    docs = [app.Documents.Item(i).FullName or app.Documents.Item(i).Name for i in range(app.Documents.Count)]
    act = app.ActiveDocument.FullName if app.Documents.Count else None
    return json.dumps({"version": app.Version, "documents": docs, "active": act}, ensure_ascii=False)


@mcp.tool()
def open_drawing(path: str) -> str:
    """Open a DWG/DXF file and make it active."""
    app = _app(start=True)
    app.Documents.Open(os.path.abspath(path))
    return status()


@mcp.tool()
def save(path: str = "") -> str:
    """Save the active drawing (optionally Save As to a .dwg/.dxf path)."""
    doc = _doc()
    if path:
        doc.SaveAs(os.path.abspath(path))
    else:
        doc.Save()
    return f"saved {doc.FullName}"


@mcp.tool()
def command(cmd: str) -> str:
    """Send a command line to BricsCAD exactly as typed (end with a space or '\\n' to execute),
    e.g. '_ZOOM _E ' or '(command \"_LINE\" \"0,0\" \"10,0\" \"\") '.
    With the ClaudeBridge add-in loaded, a LISP expression (starting with '(') is evaluated and its value
    returned, like the `lisp` tool, and a plain command line is queued without blocking (if BricsCAD is
    busy you get status "busy" - see `cancel`). Without the add-in it goes through COM SendCommand, which
    BLOCKS until the command finishes: never send an interactive command (e.g. '_LINE ' alone) that way."""
    if _bridge_up():
        if cmd.lstrip().startswith("("):
            return lisp(cmd.strip())
        r = _bridge({"op": "send", "text": cmd if cmd.endswith((" ", "\n")) else cmd + "\n"}, wait=10)
        return json.dumps(r, ensure_ascii=False)
    return _send_com(cmd if cmd.endswith((" ", "\n")) else cmd + "\n")


# ---------------------------------------------------------------- ClaudeBridge add-in (named pipe)
PIPE = r"\\.\pipe\claude-bricscad"
BRIDGE_DLL = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bridge", "bin", "ClaudeBridge.dll"))


def _bridge(req: dict, wait: float = 5.0):
    """One request/reply over the add-in's pipe. Returns the reply dict, or None if the add-in isn't loaded."""
    import pywintypes
    import win32file
    import win32pipe
    deadline = time.time() + wait
    while True:
        try:
            h = win32file.CreateFile(PIPE, win32file.GENERIC_READ | win32file.GENERIC_WRITE, 0, None,
                                     win32file.OPEN_EXISTING, 0, None)
            break
        except pywintypes.error as e:
            if e.winerror == 2:                       # no such pipe: add-in not loaded
                return None
            if e.winerror == 231 and time.time() < deadline:   # pipe busy: previous request still running
                try:
                    win32pipe.WaitNamedPipe(PIPE, 1000)
                except pywintypes.error:
                    time.sleep(0.2)
                continue
            raise
    try:
        win32file.WriteFile(h, (json.dumps(req, ensure_ascii=False) + "\n").encode("utf-8"))
        buf = b""
        while not buf.endswith(b"\n"):
            _, chunk = win32file.ReadFile(h, 65536)
            if not chunk:
                break
            buf += chunk
    finally:
        win32file.CloseHandle(h)
    return json.loads(buf.decode("utf-8"))


def _bridge_up() -> bool:
    try:
        return _bridge({"op": "ping"}, wait=2) is not None
    except Exception:
        return False


NOT_LOADED = "ClaudeBridge add-in is not loaded in BricsCAD - call bridge_load first (save open drawings before)."


@mcp.tool()
def bridge_load() -> str:
    """Load the ClaudeBridge add-in (NETLOAD) into the running BricsCAD. Needed once per BricsCAD session for
    lisp/selection/bridge_status. Save open drawings first: a crash in an add-in closes BricsCAD."""
    if _bridge_up():
        return bridge_status()
    if not os.path.exists(BRIDGE_DLL):
        return f"add-in not built: {BRIDGE_DLL} missing"
    w = _bricscad_windows()
    if w["main_enabled"] is False:
        return "NETLOAD not done: BricsCAD is blocked by a dialog: " + (", ".join(w["dialogs"]) or "unknown")
    # NETLOAD with a PVcase drawing (Sagia) active froze BricsCAD before .NET even started (twice); with a
    # blank drawing active it loads in ~1 s. So load from a temporary blank drawing, then switch back.
    app = _app()
    orig = app.ActiveDocument if app.Documents.Count else None
    tmp = app.Documents.Add()
    dll = BRIDGE_DLL.replace("\\", "/")
    r = _send_com(f'(progn (setq claude-fd (getvar "FILEDIA")) (setvar "FILEDIA" 0) (command "_.NETLOAD" "{dll}") '
                  f'(setvar "FILEDIA" claude-fd) (princ)) ')
    if r != "sent":
        return "NETLOAD not done: " + r
    up = False
    for _ in range(40):
        time.sleep(0.25)
        if _bridge_up():
            up = True
            break
    if orig is not None:
        try:
            orig.Activate()
            tmp.Close(False)
        except Exception:
            pass
    return bridge_status() if up else "NETLOAD sent but the bridge did not answer in 10 s - check the BricsCAD command line."


@mcp.tool()
def bridge_status() -> str:
    """ClaudeBridge state: active drawing, open drawings, whether BricsCAD is idle (quiescent) or which
    command is running. Tells you if a modal dialog or a pending prompt is blocking BricsCAD."""
    r = _bridge({"op": "ping"}, wait=5)
    return NOT_LOADED if r is None else json.dumps(r, ensure_ascii=False)


@mcp.tool()
def lisp(expr: str, timeout: int = 60) -> str:
    """Evaluate AutoLISP in the active drawing and return its value (vl-prin1-to-string form), e.g.
    '(getvar "CLAYER")', '(load "C:/x/gen.lsp")'. Errors come back as {"ok": false, "error": ...};
    if BricsCAD is busy (a command waiting for input, a dialog) you get status "busy" instead of a hang.
    Greek and other Unicode text can be passed directly. Needs the ClaudeBridge add-in (bridge_load)."""
    r = _bridge({"op": "lisp", "expr": expr, "timeout": int(timeout)}, wait=10)
    return NOT_LOADED if r is None else json.dumps(r, ensure_ascii=False)


@mcp.tool()
def selection() -> str:
    """What the user has selected in BricsCAD: `current` = live pickfirst selection, `last` = the last
    non-empty selection (kept after it is cleared), each with handle, type, layer and bbox.
    Use it when the user says 'this one' / 'the selected wall'. Needs the ClaudeBridge add-in."""
    r = _bridge({"op": "selection"}, wait=5)
    return NOT_LOADED if r is None else json.dumps(r, ensure_ascii=False)


@mcp.tool()
def cancel() -> str:
    """Press Esc twice in BricsCAD: cancels a command or LISP left waiting for input (after a "busy" reply).
    Only use it on work you started - it would also cancel something the user is doing."""
    r = _bridge({"op": "cancel"}, wait=10)
    return NOT_LOADED if r is None else json.dumps(r, ensure_ascii=False)


@mcp.tool()
def layers() -> str:
    """List layers with on/frozen/locked state, colour and entity counts."""
    doc = _doc()
    counts = {}
    for e in doc.ModelSpace:
        counts[e.Layer] = counts.get(e.Layer, 0) + 1
    out = []
    for i in range(doc.Layers.Count):
        l = doc.Layers.Item(i)
        out.append({"name": l.Name, "on": l.LayerOn, "frozen": l.Freeze, "locked": l.Lock, "color": l.color,
                    "entities": counts.get(l.Name, 0)})
    return json.dumps(out, ensure_ascii=False)


@mcp.tool()
def entities(layer: str = "", type_filter: str = "", bbox: list[float] | None = None, limit: int = 300,
             detail: bool = False) -> str:
    """List model-space entities. Filters: layer name (exact, case-insensitive), entity type substring
    (e.g. 'Line', 'Polyline', 'BlockReference', 'Text'), bbox [xmin, ymin, xmax, ymax]. Returns geometry."""
    doc = _doc()
    out = []
    for e in doc.ModelSpace:
        if layer and e.Layer.lower() != layer.lower():
            continue
        if type_filter and type_filter.lower() not in e.ObjectName.lower():
            continue
        d = _ent(e, detail)
        if bbox and "bbox" in d:
            (x0, y0, _), (x1, y1, _) = d["bbox"]
            if x1 < bbox[0] or x0 > bbox[2] or y1 < bbox[1] or y0 > bbox[3]:
                continue
        out.append(d)
        if len(out) >= limit:
            break
    return json.dumps({"count": len(out), "entities": out}, ensure_ascii=False)


@mcp.tool()
def extents() -> str:
    """Drawing extents and units."""
    doc = _doc()
    return json.dumps({"extmin": list(doc.GetVariable("EXTMIN")), "extmax": list(doc.GetVariable("EXTMAX")),
                       "insunits": doc.GetVariable("INSUNITS"), "measurement": doc.GetVariable("MEASUREMENT")})


@mcp.tool()
def add_line(start: list[float], end: list[float], layer: str = "0") -> str:
    """Draw a line in model space."""
    doc = _doc()
    e = doc.ModelSpace.AddLine(_pt(start), _pt(end))
    e.Layer = _ensure_layer(doc, layer)
    return e.Handle


@mcp.tool()
def add_polyline(points: list[list[float]], closed: bool = False, layer: str = "0") -> str:
    """Draw a 2D lightweight polyline from [[x, y], ...]."""
    doc = _doc()
    flat = [float(c) for p in points for c in p[:2]]
    arr = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, flat)
    e = doc.ModelSpace.AddLightWeightPolyline(arr)
    e.Closed = closed
    e.Layer = _ensure_layer(doc, layer)
    return e.Handle


@mcp.tool()
def add_text(text: str, insert: list[float], height: float = 0.25, layer: str = "0") -> str:
    """Place single-line text."""
    doc = _doc()
    e = doc.ModelSpace.AddText(text, _pt(insert), height)
    e.Layer = _ensure_layer(doc, layer)
    return e.Handle


@mcp.tool()
def delete(handles: list[str]) -> str:
    """Delete entities by handle."""
    doc = _doc()
    n = 0
    for h in handles:
        try:
            doc.HandleToObject(h).Delete()
            n += 1
        except Exception:
            pass
    return f"deleted {n}"


@mcp.tool()
def export_dxf(path: str) -> str:
    """Save the active drawing as DXF (the open drawing then continues as that DXF file)."""
    doc = _doc()
    path = os.path.abspath(path)
    doc.SaveAs(path, 61)   # 61 = R2013 DXF in the AutoCAD-compatible save-type enum
    return f"written {path}"


# ---------------------------------------------------------------- view / screenshot
@mcp.tool()
def screenshot(path: str = "", zoom_extents: bool = False) -> str:
    """Capture the BricsCAD window to a PNG (default: %TEMP%\\bricscad_view.png) and return its path.
    Read the returned file to see the drawing."""
    import win32gui
    from PIL import ImageGrab
    doc = _doc()
    if zoom_extents:
        _app().ZoomExtents()
    hwnd = _app().HWND
    win32gui.ShowWindow(hwnd, 9)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(0.6)
    rect = win32gui.GetWindowRect(hwnd)
    path = os.path.abspath(path or os.path.join(os.environ["TEMP"], "bricscad_view.png"))
    ImageGrab.grab(bbox=rect, all_screens=True).save(path)
    return path


@mcp.tool()
def zoom(xmin: float = 0, ymin: float = 0, xmax: float = 0, ymax: float = 0) -> str:
    """Zoom to a window [xmin, ymin]-[xmax, ymax]; all zeros = zoom extents."""
    app = _app()
    if xmin == ymin == xmax == ymax == 0:
        app.ZoomExtents()
    else:
        app.ZoomWindow(_pt([xmin, ymin]), _pt([xmax, ymax]))
    return "ok"


# ---------------------------------------------------------------- areas and lengths
@mcp.tool()
def measure(handles: list[str] | None = None, layer: str = "", closed_only: bool = True) -> str:
    """Area and length/perimeter of entities: by handles, or every (closed) polyline/circle/hatch/region on a
    layer. Returns per-entity values and totals in drawing units (see extents().insunits)."""
    doc = _doc()
    ents = [doc.HandleToObject(h) for h in handles] if handles else [
        e for e in doc.ModelSpace if (not layer or e.Layer.lower() == layer.lower())
        and e.ObjectName in ("AcDbPolyline", "AcDb2dPolyline", "AcDbCircle", "AcDbHatch", "AcDbRegion", "AcDbEllipse")]
    rows, ta, tl = [], 0.0, 0.0
    for e in ents:
        if closed_only and e.ObjectName in ("AcDbPolyline", "AcDb2dPolyline") and not e.Closed:
            continue
        a = l = None
        for prop in ("Area",):
            try: a = float(getattr(e, prop))
            except Exception: pass
        for prop in ("Length", "Circumference", "Perimeter"):
            try: l = float(getattr(e, prop)); break
            except Exception: pass
        rows.append({"handle": e.Handle, "type": e.ObjectName, "layer": e.Layer, "area": a, "length": l})
        ta += a or 0; tl += l or 0
    return json.dumps({"count": len(rows), "total_area": round(ta, 4), "total_length": round(tl, 4), "items": rows})


@mcp.tool()
def area_of_points(points: list[list[float]]) -> str:
    """Area and perimeter of a polygon given its [[x, y], ...] corners (shoelace)."""
    n = len(points)
    a = sum(points[i][0] * points[(i + 1) % n][1] - points[(i + 1) % n][0] * points[i][1] for i in range(n)) / 2
    p = sum(((points[(i + 1) % n][0] - points[i][0]) ** 2 + (points[(i + 1) % n][1] - points[i][1]) ** 2) ** 0.5 for i in range(n))
    return json.dumps({"area": abs(a), "perimeter": p})


# ---------------------------------------------------------------- blocks
@mcp.tool()
def blocks() -> str:
    """Block definitions in the drawing (names and how many times each is inserted in model space)."""
    doc = _doc()
    used = {}
    for e in doc.ModelSpace:
        if e.ObjectName == "AcDbBlockReference":
            n = getattr(e, "EffectiveName", e.Name)
            used[n] = used.get(n, 0) + 1
    names = [doc.Blocks.Item(i).Name for i in range(doc.Blocks.Count)]
    return json.dumps([{"name": n, "inserts": used.get(n, 0)} for n in names if not n.startswith("*")], ensure_ascii=False)


@mcp.tool()
def insert_block(name_or_file: str, insert: list[float], scale: float = 1.0, rotation_deg: float = 0.0,
                 layer: str = "0") -> str:
    """Insert a block by name (defined in the drawing) or from a .dwg file path."""
    import math
    doc = _doc()
    e = doc.ModelSpace.InsertBlock(_pt(insert), name_or_file, scale, scale, scale, math.radians(rotation_deg))
    e.Layer = _ensure_layer(doc, layer)
    return e.Handle


@mcp.tool()
def block_attributes(handle: str, set_values: dict[str, str] | None = None) -> str:
    """Read (and optionally set) the attributes of a block reference: set_values = {TAG: value}."""
    doc = _doc()
    e = doc.HandleToObject(handle)
    out = {}
    if getattr(e, "HasAttributes", False):
        for a in e.GetAttributes():
            if set_values and a.TagString in set_values:
                a.TextString = str(set_values[a.TagString])
            out[a.TagString] = a.TextString
    return json.dumps(out, ensure_ascii=False)


# ---------------------------------------------------------------- layouts and PDF
@mcp.tool()
def layouts() -> str:
    """Paper-space layouts and the plotters/PDF configs BricsCAD offers."""
    doc = _doc()
    names = [doc.Layouts.Item(i).Name for i in range(doc.Layouts.Count)]
    try:
        devs = list(doc.ActiveLayout.GetPlotDeviceNames())
    except Exception:
        devs = []
    return json.dumps({"layouts": names, "devices": devs}, ensure_ascii=False)


@mcp.tool()
def plot_pdf(path: str, layout: str = "", device: str = "") -> str:
    """Plot a layout (default: the active one) to a PDF file. device defaults to the first PDF config found."""
    doc = _doc()
    if layout:
        doc.ActiveLayout = doc.Layouts.Item(layout)
    lay = doc.ActiveLayout
    if not device:
        devs = list(lay.GetPlotDeviceNames())
        device = next((d for d in devs if "pdf" in d.lower()), devs[0] if devs else "")
    lay.ConfigName = device
    doc.SetVariable("BACKGROUNDPLOT", 0)
    ok = doc.Plot.PlotToFile(os.path.abspath(path), device)
    return f"{'plotted' if ok else 'plot reported failure'}: {os.path.abspath(path)} via {device}"


# ---------------------------------------------------------------- BIM / 3D solids
@mcp.tool()
def solids(layer: str = "", limit: int = 300) -> str:
    """3D solids (BricsCAD BIM walls, slabs, openings are solids): bbox, volume and BIM type if readable."""
    doc = _doc()
    out = []
    for e in doc.ModelSpace:
        if e.ObjectName != "AcDb3dSolid" or (layer and e.Layer.lower() != layer.lower()):
            continue
        d = _ent(e)
        for prop in ("Volume", "SolidType"):
            try: d[prop.lower()] = getattr(e, prop)
            except Exception: pass
        out.append(d)
        if len(out) >= limit:
            break
    return json.dumps({"count": len(out), "solids": out}, ensure_ascii=False)


# ---------------------------------------------------------------- bridge to Blender
@mcp.tool()
def export_geometry(path: str, layers: list[str] | None = None, bbox: list[float] | None = None,
                    to_metres: float = 0.0) -> str:
    """Write lines/polylines/arcs/circles/block inserts (optionally per layer and inside bbox) to a JSON file,
    scaled to metres (to_metres = factor; 0 = from INSUNITS). Import it in Blender with blender_import.py."""
    doc = _doc()
    if not to_metres:
        to_metres = {1: 0.0254, 2: 0.3048, 4: 0.001, 5: 0.01, 6: 1.0}.get(int(doc.GetVariable("INSUNITS")), 1.0)
    want = {l.lower() for l in layers} if layers else None
    items = []
    for e in doc.ModelSpace:
        if want and e.Layer.lower() not in want:
            continue
        d = _ent(e, detail=True)
        if bbox and "bbox" in d:
            (x0, y0, _), (x1, y1, _) = d["bbox"]
            if x1 < bbox[0] or x0 > bbox[2] or y1 < bbox[1] or y0 > bbox[3]:
                continue
        items.append(d)
    json.dump({"units_to_m": to_metres, "items": items}, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return f"{len(items)} items -> {os.path.abspath(path)}"


def _ensure_layer(doc, name):
    try:
        doc.Layers.Item(name)
    except Exception:
        doc.Layers.Add(name)
    return name


if __name__ == "__main__":
    mcp.run()

