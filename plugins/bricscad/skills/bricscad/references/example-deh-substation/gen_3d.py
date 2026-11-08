# Generates model3d.lsp: 3D solids of the DEH room + stair hall, offset +OX in x, real levels as z.
import math, sys

OX = 25.0
out = []
def w(s): out.append(s)

# ---- plan geometry (same values as gen_katopsi.py) ----
k = 0.10
yin = lambda x: 3.30 + k*x
yout = lambda x: 3.50 + k*x
XP0, XP1 = 5.20, 5.30
XR0, XR1 = XP1 + 2.77, XP1 + 2.97
XS = XR0 - 1.60
XN = XR0 + 0.12
YBK = yin(XS) - 5.95
XK = XN - 0.34
YD1 = yin(XN) - 0.14; YD0 = YD1 - 2.70
YT = yin(XP0); YF = YT - 3.60; J = 0.025
XC = (XK + XN)/2
YTOP = yin(XC) - 0.14 - 1.58
XE = XN - 1.45; YE = yin(XK) - 2.864
# levels
FL, CEIL, ROOF = -2.00, 0.925, 1.20
REC0, REC1 = 1.52, 1.77
LAND0, LAND1 = -0.53, -0.38

def solid(lay, pts, z0, z1):
    p = ' '.join('(list %.4f %.4f)' % (x + OX, y) for x, y in pts)
    w('(ext3d "%s" (list %s) %.4f %.4f)' % (lay, p, z0, z1))

def box(lay, x0, y0, x1, y1, z0, z1):
    solid(lay, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1)

w('(vl-load-com)')
w('(setq ms (vla-get-modelspace (vla-get-activedocument (vlax-get-acad-object))) nok 0 nfail 0)')
for n, c in [('3D_WALLS', 252), ('3D_FLOOR', 8), ('3D_ROOF_SLAB', 254), ('3D_ROOF_RECESS', 254), ('3D_ROOF_DOWNSTAND', 254), ('3D_BEAMS', 252), ('3D_STAIR', 4), ('3D_DOORS', 2),
             ('3D_EQUIP', 3), ('3D_LIFT', 30)]:
    w('(if (not (tblsearch "LAYER" "%s")) (entmake (list (cons 0 "LAYER") (cons 100 "AcDbSymbolTableRecord") (cons 100 "AcDbLayerTableRecord") (cons 2 "%s") (cons 70 0) (cons 62 %d) (cons 6 "Continuous"))))' % (n, n, c))
# closed LWPOLYLINE at elevation z0 -> region -> extruded solid of height z1-z0
w('(defun ext3d (lay pts z0 z1 / r)'
  ' (entmake (append (list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 "0") (cons 100 "AcDbPolyline") (cons 90 (length pts)) (cons 70 1) (cons 38 z0))'
  ' (mapcar (function (lambda (p) (cons 10 p))) pts)))'
  ' (setq r (vl-catch-all-apply (function (lambda (/ pl arr reg sol)'
  '  (setq pl (vlax-ename->vla-object (entlast)))'
  '  (setq arr (vlax-make-safearray vlax-vbObject (quote (0 . 0)))) (vlax-safearray-put-element arr 0 pl)'
  '  (setq reg (car (vlax-safearray->list (vlax-variant-value (vla-AddRegion ms arr)))))'
  '  (setq sol (vla-AddExtrudedSolid ms reg (- z1 z0) 0.0)) (vla-put-Layer sol lay)'
  '  (vla-Delete reg) (vla-Delete pl) T))))'
  ' (if (vl-catch-all-error-p r) (progn (setq nfail (1+ nfail)) (princ (strcat "\\nFAIL " lay ": " (vl-catch-all-error-message r)))) (setq nok (1+ nok))))')

# ---- floor and roof ----
foot = [(-0.20, -0.20), (XP0, -0.20), (XP0, YBK-0.50), (XR1, YBK-0.50), (XR1, yout(XR1)), (-0.20, yout(-0.20))]
solid('3D_FLOOR', foot, FL-0.20, FL)
solid('3D_ROOF_SLAB', [(-0.20, -0.20), (XP0, -0.20), (XP0, YBK-0.50), (XR1, YBK-0.50), (XR1, YE), (XE, YE), (XE, yout(XE)), (-0.20, yout(-0.20))], CEIL, ROOF)
solid('3D_ROOF_RECESS', [(XE-0.20, YE-0.20), (XR1, YE-0.20), (XR1, yout(XR1)), (XE-0.20, yout(XE-0.20))], REC0, REC1)
# downstand around the ceiling recess (0.595 drop)
solid('3D_ROOF_DOWNSTAND', [(XE-0.20, YE-0.20), (XR1, YE-0.20), (XR1, YE), (XE, YE), (XE, yout(XE)), (XE-0.20, yout(XE-0.20))], CEIL, REC0)

# ---- walls (floor to ceiling) ----
solid('3D_WALLS', [(-0.20, yin(-0.20)), (XR1, yin(XR1)), (XR1, yout(XR1)), (-0.20, yout(-0.20))], FL, CEIL)   # street wall
box('3D_WALLS', -0.20, -0.20, 0.0, yin(0.0), FL, CEIL)                    # DEH left wall
box('3D_WALLS', 0.0, -0.20, XP0, 0.0, FL, CEIL)                           # DEH back wall
box('3D_WALLS', XP0, YBK, XP1, YF+J, FL, CEIL)                            # hall wall below DEH front
solid('3D_WALLS', [(XP0, YT-J), (XP1, YT-J), (XP1, yin(XP1)), (XP0, yin(XP0))], FL, CEIL)   # jamb at street wall
box('3D_WALLS', XP0, YF, XP1, YT, 0.85, CEIL)                             # lintel over folding door
box('3D_WALLS', XR0, YBK, XR1, YD0, FL, CEIL)                             # side wall
box('3D_WALLS', XR0, YD0, XR1, YD1, FL, LAND1)                            # retaining wall under the exit door
box('3D_WALLS', XN+0.04, YD0, XR1, YD1, 1.506, REC0)                      # lintel over exit door
box('3D_WALLS', XR0, YD1, XR1, yin(XR1), FL, REC0)                        # wall beside the column
solid('3D_WALLS', [(XK, yin(XK)-0.14), (XN, YD1), (XN, yin(XN)), (XK, yin(XK))], FL, REC0)  # column 0.34 x 0.14
box('3D_BEAMS', XP0-0.20, YBK-0.50, XR1, YBK, CEIL-0.35, CEIL)            # beam at the hall end (0.35 drop), open under it
box('3D_WALLS', XR0-0.31, YBK, XR0, YBK+0.52, FL, CEIL)                   # back column

# ---- stair: 10 risers 0.162, treads 0.28, landing at -0.38 ----
for i in range(9):
    y0 = YTOP - (9 - i)*0.28
    box('3D_STAIR', XS, y0, XR0, y0 + 0.28, FL, FL + (i + 1)*0.162)
solid('3D_STAIR', [(XS, YTOP), (XN, YTOP), (XN, YD1), (XK, yin(XK)-0.14), (XK, yin(XK)), (XS, yin(XS))], LAND0, LAND1)

# ---- doors ----
y = YF + J + 0.025
for i in range(4):                                                        # DEH folding door 4 x 0.875
    box('3D_DOORS', XP0+0.03, y + 0.005, XP0+0.07, y + 0.870, FL, 0.85)
    y += 0.875
YM = (YD0 + YD1)/2                                                        # exit door 2.70, two leaves
for ya, yb in ((YD0, YM), (YM, YD1)):
    box('3D_DOORS', XN, ya+0.005, XN+0.04, yb-0.005, LAND1, 1.506)

# ---- DEH cubicles over the cable trench (2.90 x 0.60, parallel to the street wall) ----
a = math.atan(k); u = (math.cos(a), math.sin(a)); n = (math.sin(a), -math.cos(a))
add = lambda p, q, f=1.0: (p[0] + f*q[0], p[1] + f*q[1])
B = (0.0, 3.30 - 1.10/math.cos(a))
P3 = add(B, u, 1.00); P2 = add(P3, u, 2.90); P0 = add(P3, n, -0.60); P1 = add(P2, n, -0.60)
cells = [0.0, 0.50, 1.15, 1.75, 2.50, 2.90]
for s0, s1 in zip(cells, cells[1:]):
    q0 = add(P0, u, s0 + 0.005); q1 = add(P0, u, s1 - 0.005)
    solid('3D_EQUIP', [q0, q1, add(q1, n, 0.60), add(q0, n, 0.60)], FL, 0.10)

# ---- goods lift: open cage (4 thin panels) ----
for x0, y0, x1, y1 in [(XP1, 2.80, XS, 2.83), (XP1, 3.77, XS, 3.80), (XP1, 2.83, XP1+0.03, 3.77), (XS-0.03, 2.83, XS, 3.77)]:
    box('3D_LIFT', x0, y0, x1, y1, FL, CEIL)

w('(princ (strcat "\\n3D solids: " (itoa nok) " ok, " (itoa nfail) " failed")) (princ)')
open(sys.argv[1], 'w', encoding='ascii').write('\n'.join(out) + '\n')
print(len(out), 'lines')
