# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=1.2,<2", "pywin32>=306", "pillow>=10"]
# ///
"""MCP server that drives a running BricsCAD (V26) through its COM automation interface."""
import json
import os
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
        app = win32com.client.Dispatch(PROGIDS[0])
        app.Visible = True
        for _ in range(60):
            try:
                if app.Documents.Count >= 0:
                    return app
            except Exception:
                time.sleep(1)
        return app
    raise RuntimeError("BricsCAD is not running. Start it (or call start_bricscad).")


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
    e.g. '_ZOOM _E ' or '(command \"_LINE\" \"0,0\" \"10,0\" \"\") '. Runs asynchronously in the drawing."""
    doc = _doc()
    doc.SendCommand(cmd if cmd.endswith((" ", "\n")) else cmd + "\n")
    return "sent"


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

