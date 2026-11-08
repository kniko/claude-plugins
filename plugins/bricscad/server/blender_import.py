"""Run inside Blender: imports a JSON written by the BricsCAD MCP `export_geometry` tool.
Lines/polylines become curve objects per layer; set EXTRUDE to give them height (e.g. walls).

    exec(open(r"<plugin folder>/server/blender_import.py").read())
    import_bricscad(r"C:/path/plan.json", offset=(0, 0, 0), z=3.25, extrude=0.0)
"""
import json
import bpy


def import_bricscad(path, offset=(0.0, 0.0, 0.0), z=0.0, extrude=0.0, collection="BricsCAD"):
    data = json.load(open(path, encoding="utf-8"))
    k = data["units_to_m"]
    col = bpy.data.collections.get(collection) or bpy.data.collections.new(collection)
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    curves = {}
    def curve(layer):
        if layer not in curves:
            cu = bpy.data.curves.new(f"cad_{layer}", "CURVE")
            cu.dimensions = "2D" if extrude else "3D"
            cu.extrude = extrude / 2
            ob = bpy.data.objects.new(f"cad_{layer}", cu)
            ob.location = (offset[0], offset[1], z + offset[2] + extrude / 2)
            col.objects.link(ob)
            curves[layer] = cu
        return curves[layer]
    n = 0
    for it in data["items"]:
        pts, closed = None, False
        if it["type"] == "AcDbLine":
            pts = [it["start"], it["end"]]
        elif isinstance(it.get("points"), list):
            pts, closed = it["points"], it.get("closed", False)
        if not pts:
            continue
        sp = curve(it["layer"]).splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for p, c in zip(sp.points, pts):
            p.co = (c[0] * k, c[1] * k, (c[2] * k if len(c) > 2 else 0.0), 1.0)
        sp.use_cyclic_u = closed
        n += 1
    print(f"imported {n} shapes on {len(curves)} layers into '{collection}'")
