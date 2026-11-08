# Rasterise a bricscad export_geometry JSON to PNG (no PIL needed) to check a drawing by eye.
# usage: python -I render_geom.py geom.json out.png xmin ymin xmax ymax pixels_per_unit
# colours per layer in `col`; other layers grey. Handles LINE, (LW)POLYLINE, ARC/CIRCLE.
import json, zlib, struct, sys, math
d = json.load(open(sys.argv[1], encoding='utf-8'))
x0, y0, x1, y1 = map(float, sys.argv[3:7]); S = float(sys.argv[7])
W, H = int((x1-x0)*S), int((y1-y0)*S)
img = bytearray(b'\xff' * (W*H*3))
col = {'WALLS': (0,0,0), 'EQUIP': (0,140,0), 'STAIRS': (0,120,200), 'HIDDEN': (200,0,200), 'HATCH': (190,190,190), 'TEXT': (120,60,0)}
def px(x, y): return int((x-x0)*S), int((y1-y)*S)
def seg(a, b, c):
    (ax, ay), (bx, by) = px(*a), px(*b); n = max(abs(bx-ax), abs(by-ay), 1)
    for i in range(n+1):
        X = ax + (bx-ax)*i//n; Y = ay + (by-ay)*i//n
        if 0 <= X < W and 0 <= Y < H: img[(Y*W+X)*3:(Y*W+X)*3+3] = bytes(c)
for it in d['items']:
    c = col.get(it['layer'], (100,100,100)); t = it['type']
    if 'points' in it:
        p = it['points'] + ([it['points'][0]] if it.get('closed') else [])
        for a, b in zip(p, p[1:]): seg(a[:2], b[:2], c)
    elif 'start' in it: seg(it['start'][:2], it['end'][:2], c)
    elif 'center' in it and 'radius' in it:
        cx, cy = it['center'][:2]; r = it['radius']; a1 = it.get('start_angle', 0); a2 = it.get('end_angle', 2*math.pi)
        if a2 < a1: a2 += 2*math.pi
        pts = [(cx + r*math.cos(a1+(a2-a1)*k/60), cy + r*math.sin(a1+(a2-a1)*k/60)) for k in range(61)]
        for a, b in zip(pts, pts[1:]): seg(a, b, c)
raw = b''.join(b'\x00' + bytes(img[y*W*3:(y+1)*W*3]) for y in range(H))
png = b'\x89PNG\r\n\x1a\n'
def chunk(t, data): return struct.pack('>I', len(data)) + t + data + struct.pack('>I', zlib.crc32(t+data) & 0xffffffff)
png += chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')
open(sys.argv[2], 'wb').write(png); print(W, H)
