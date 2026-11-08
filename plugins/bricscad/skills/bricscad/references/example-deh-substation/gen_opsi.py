# Generates opsi.lsp: elevation (ΟΨΙΣ), placed right of section A-A at the same levels.
import math, sys

out = []
def w(s): out.append(s)
OX, DY = 12.5, -8.5   # local x 0 -> drawing x OX; level 0.00 -> drawing y DY

def esc(s):
    r = []
    for ch in s:
        if ord(ch) < 128:
            r.append('\\\\' if ch == '\\' else ('\\"' if ch == '"' else ch))
        else:
            r.append('\\\\U+%04X' % ord(ch))
    return ''.join(r)

def P(p): return '(list %.4f %.4f 0.0)' % (p[0] + OX, p[1] + DY)

def line(lay, a, b, lt=None):
    extra = ' (cons 6 "%s")' % lt if lt else ''
    w('(entmake (list (cons 0 "LINE") (cons 8 "%s")%s (cons 10 %s) (cons 11 %s)))' % (lay, extra, P(a), P(b)))

def pline(lay, pts, closed=False, width=0.0, lt=None):
    s = '(entmake (append (list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 "%s")' % lay
    if lt: s += ' (cons 6 "%s")' % lt
    s += ' (cons 100 "AcDbPolyline") (cons 90 %d) (cons 70 %d) (cons 43 %.3f))' % (len(pts), 1 if closed else 0, width)
    s += ' (list ' + ' '.join('(cons 10 (list %.4f %.4f))' % (p[0] + OX, p[1] + DY) for p in pts) + ')))'
    w(s)

def solid(lay, p1, p2, p3):
    w('(entmake (list (cons 0 "SOLID") (cons 8 "%s") (cons 10 %s) (cons 11 %s) (cons 12 %s) (cons 13 %s)))'
      % (lay, P(p1), P(p2), P(p3), P(p3)))

def text(lay, s, p, h, rot=0.0):
    w('(entmake (list (cons 0 "TEXT") (cons 8 "%s") (cons 7 "GR") (cons 10 %s) (cons 40 %.3f) (cons 50 %.6f) (cons 1 "%s")))'
      % (lay, P(p), h, math.radians(rot), esc(s)))

def arrowhead(lay, tip, frm, L=0.15, W=0.05):
    dx, dy = tip[0]-frm[0], tip[1]-frm[1]; d = math.hypot(dx, dy); ux, uy = dx/d, dy/d
    b = (tip[0]-ux*L, tip[1]-uy*L)
    solid(lay, tip, (b[0]-uy*W, b[1]+ux*W), (b[0]+uy*W, b[1]-ux*W))

# ---- stair (side view): 9 risers of 0.18 from -2.00 to -0.38, treads 0.25 ----
# measured: 10 risers (-2.00 -> -0.38), treads 0.28, landing 1.58 from column face (column 0.14 proud of door plane 3.88)
XTOP = 3.88 - 0.14 - 1.58
R, T = 0.162, 0.28
X0 = XTOP - 9*T
prof = [(X0, -2.00)]
for i in range(10):
    x = X0 + i*T; y = -2.00 + (i+1)*R
    prof += [(x, y)] + ([(x + T, y)] if i < 9 else [])
stair = prof + [(XTOP, -0.53), (X0 + 0.18, -2.00)]

def inside(pt, poly):
    x, y = pt; c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i+1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1)*(x2 - x1)/(y2 - y1):
            c = not c
    return c

def clipped(lay, a, b, poly=stair, lt=None):
    """Draw segment a-b minus the part hidden behind the stair."""
    ts = [0.0, 1.0]
    for i in range(len(poly)):
        p, q = poly[i], poly[(i+1) % len(poly)]
        d = (b[0]-a[0])*(q[1]-p[1]) - (b[1]-a[1])*(q[0]-p[0])
        if abs(d) < 1e-12: continue
        t = ((p[0]-a[0])*(q[1]-p[1]) - (p[1]-a[1])*(q[0]-p[0])) / d
        s = ((p[0]-a[0])*(b[1]-a[1]) - (p[1]-a[1])*(b[0]-a[0])) / d
        if 0 < t < 1 and 0 <= s <= 1: ts.append(t)
    ts.sort()
    for t0, t1 in zip(ts, ts[1:]):
        if t1 - t0 < 1e-6: continue
        m = (a[0] + (b[0]-a[0])*(t0+t1)/2, a[1] + (b[1]-a[1])*(t0+t1)/2)
        if not inside(m, poly):
            line(lay, (a[0]+(b[0]-a[0])*t0, a[1]+(b[1]-a[1])*t0), (a[0]+(b[0]-a[0])*t1, a[1]+(b[1]-a[1])*t1), lt)

w('(vl-load-com)')
w('(setq ms (vla-get-modelspace (vla-get-activedocument (vlax-get-acad-object))))')
w('(setq oldos (getvar "OSMODE")) (setvar "OSMODE" 0) (setvar "CMDECHO" 0)')
w('(defun hatchlast (pat sc / pl h r) (setq pl (vlax-ename->vla-object (entlast)))'
  ' (setq r (vl-catch-all-apply (function (lambda () (setq h (vla-AddHatch ms 1 pat :vlax-true)) (vla-put-Layer h "HATCH") (vla-put-PatternScale h sc)'
  ' (vla-AppendOuterLoop h (vlax-make-variant (vlax-safearray-fill (vlax-make-safearray vlax-vbObject (quote (0 . 0))) (list pl)))) (vla-Evaluate h)))))'
  ' (if (and (vl-catch-all-error-p r) h) (vl-catch-all-apply (quote vla-Delete) (list h))) (princ))')

ys = lambda x: -0.26 + (x + 1.27) * (-0.12 / 6.75)   # sidewalk line, slight fall to the street

# ---- earth below the sidewalk (hatched, boundary on HATCH layer) ----
for poly in ([(-1.24, -2.00), (4.39, -2.00), (4.39, ys(4.39)), (-1.24, ys(-1.24))],
             [(4.39, -2.10), (5.45, -2.10), (5.45, ys(5.45)), (4.39, ys(4.39))]):
    pline('HATCH', poly, closed=True)
    w('(hatchlast "ANSI31" 0.08)')

# ---- ground, outer wall, sidewalk ----
pline('WALLS', [(-1.24, -2.00), (4.39, -2.00), (4.39, ys(4.39))], width=0.04)
line('WALLS', (-1.27, ys(-1.27)), (5.48, ys(5.48)))
line('WALLS', (-2.10, -0.65), (-1.56, -0.65))
line('HIDDEN', (4.27, 2.10), (4.27, -2.30), lt='CENTER')

# ---- top box: ceiling recess at the entrance (measured: 2.864 long, 1.90 above landing, 0.595 drop) ----
XD = 3.88 - 2.864
pline('WALLS', [(XD, 0.925), (XD, 1.77), (4.27, 1.77), (4.27, -0.38)])
line('WALLS', (XD, 1.52), (4.27, 1.52))
line('WALLS', (-0.80, 1.20), (XD, 1.20))
line('WALLS', (-0.80, 0.925), (XD, 0.925))
clipped('WALLS', (3.88, 1.52), (3.88, -2.00))

# ---- cubicle doors: frame and 4 leaves, floor -2.00 to +1.00 ----
pline('EQUIP', [(0.00, -2.00), (0.00, 0.90), (3.82, 0.90), (3.82, -2.00)])
line('EQUIP', (0.06, 0.85), (3.76, 0.85))
leaves = [(0.06, 1.01), (1.05, 1.88), (1.92, 2.80), (2.83, 3.76)]
for x0, x1 in leaves:
    for x in (x0, x1):
        clipped('EQUIP', (x, -2.00), (x, 0.85))
    for yh in (0.70, -0.85, -1.75):            # hinge marks
        clipped('EQUIP', (x1 - 0.04, yh), (x1 - 0.04, yh + 0.08))
# louvres: upper +0.40..+0.81, lower -1.81..-1.43
up = [(0.16, 0.88), (1.08, 1.77), (1.99, 2.72), (2.92, 3.61)]
lo = [(0.20, 0.90), (1.13, 1.82), (2.04, 2.74), (2.95, 3.63)]
for (xa, xb), (ya, yb) in [(u, (0.40, 0.81)) for u in up] + [(l, (-1.81, -1.43)) for l in lo]:
    for x in (xa, xb):
        clipped('EQUIP', (x, ya), (x, yb))
    n = 11
    for i in range(n + 1):
        y = ya + (yb - ya) * i / n
        clipped('EQUIP', (xa, y), (xb, y))

# ---- stair and landing ----
pline('STAIRS', stair, closed=True)
pline('WALLS', [(XTOP, -0.38), (3.88, -0.38), (3.88, -0.53), (XTOP, -0.53)])
line('HIDDEN', (0.70, -0.38), (XTOP, -0.38), lt='DASHED')

# ---- notes ----
text('TEXT', '%%uΟΨΙΣ', (1.40, 2.40), 0.30)
text('TEXT', 'ΣΤΑΘΜΗ ΠΛΑΚΑΣ', (-2.90, 1.55), 0.13)
text('TEXT', 'ΠΛΑΤΥΣΚΑΛΟΥ', (-2.90, 1.30), 0.13)
line('TEXT', (-2.95, 1.22), (-0.64, 1.22)); line('TEXT', (-0.64, 1.22), (0.70, -0.38)); arrowhead('TEXT', (0.70, -0.38), (-0.64, 1.22))
text('TEXT', 'ΚΛΙΣΙΣ ΠΕΖΟΔΡΟΜΙΟΥ', (4.60, 0.02), 0.13)
line('TEXT', (4.55, -0.05), (6.40, -0.05)); line('TEXT', (4.55, -0.05), (4.80, ys(4.80))); arrowhead('TEXT', (4.80, ys(4.80)), (4.55, -0.05))


# ---- dimensions (measured on site) ----
def dim(a, b, loc):
    w('(command "_.DIMLINEAR" "_non" %s "_non" %s "_non" %s)' % (P(a), P(b), P(loc)))
w('(setvar "CLAYER" "DIM")')
dim((XD, 1.77), (3.88, 1.77), (2.4, 2.05))
dim((XD, 0.925), (XD, 1.52), (0.70, 1.2))
dim((2.80, -0.38), (2.80, 1.52), (2.95, 0.55))
w('(setvar "CLAYER" "0") (setvar "OSMODE" oldos) (setvar "CMDECHO" 1)')
w('(princ "\\nOPSI OK") (princ)')

open(sys.argv[1], 'w', encoding='ascii').write('\n'.join(out) + '\n')
print(len(out), 'lines')
