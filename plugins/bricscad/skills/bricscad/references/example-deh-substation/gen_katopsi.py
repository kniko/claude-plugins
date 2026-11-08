# Generates katopsi.lsp (ASCII only; Greek as \U+XXXX) for BricsCAD.
import math, sys

out = []
def w(s): out.append(s)

def esc(s):
    r = []
    for ch in s:
        if ord(ch) < 128:
            r.append('\\\\' if ch == '\\' else ('\\"' if ch == '"' else ch))
        else:
            r.append('\\\\U+%04X' % ord(ch))
    return ''.join(r)

def P(p): return '(list %.4f %.4f 0.0)' % (p[0], p[1])

def line(lay, a, b, lt=None):
    extra = ' (cons 6 "%s")' % lt if lt else ''
    w('(entmake (list (cons 0 "LINE") (cons 8 "%s")%s (cons 10 %s) (cons 11 %s)))' % (lay, extra, P(a), P(b)))

def pline(lay, pts, closed=False, width=0.0, lt=None):
    s = '(entmake (append (list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 "%s")' % lay
    if lt: s += ' (cons 6 "%s")' % lt
    s += ' (cons 100 "AcDbPolyline") (cons 90 %d) (cons 70 %d) (cons 43 %.3f))' % (len(pts), 1 if closed else 0, width)
    s += ' (list ' + ' '.join('(cons 10 (list %.4f %.4f))' % (p[0], p[1]) for p in pts) + ')))'
    w(s)

def arc(lay, c, r, a1, a2, lt=None):
    extra = ' (cons 6 "%s")' % lt if lt else ''
    w('(entmake (list (cons 0 "ARC") (cons 8 "%s")%s (cons 10 %s) (cons 40 %.4f) (cons 50 %.6f) (cons 51 %.6f)))'
      % (lay, extra, P(c), r, math.radians(a1), math.radians(a2)))

def solid(lay, p1, p2, p3):
    w('(entmake (list (cons 0 "SOLID") (cons 8 "%s") (cons 10 %s) (cons 11 %s) (cons 12 %s) (cons 13 %s)))'
      % (lay, P(p1), P(p2), P(p3), P(p3)))

def text(lay, s, p, h, rot=0.0, center=False):
    if center:
        w('(entmake (list (cons 0 "TEXT") (cons 8 "%s") (cons 7 "GR") (cons 10 %s) (cons 11 %s) (cons 40 %.3f) (cons 50 %.6f) (cons 72 1) (cons 73 2) (cons 1 "%s")))'
          % (lay, P(p), P(p), h, math.radians(rot), esc(s)))
    else:
        w('(entmake (list (cons 0 "TEXT") (cons 8 "%s") (cons 7 "GR") (cons 10 %s) (cons 40 %.3f) (cons 50 %.6f) (cons 1 "%s")))'
          % (lay, P(p), h, math.radians(rot), esc(s)))

def arrowhead(lay, tip, frm, L=0.15, W=0.05):
    dx, dy = tip[0]-frm[0], tip[1]-frm[1]; d = math.hypot(dx, dy); ux, uy = dx/d, dy/d
    b = (tip[0]-ux*L, tip[1]-uy*L)
    solid(lay, tip, (b[0]-uy*W, b[1]+ux*W), (b[0]+uy*W, b[1]-ux*W))

def dim(kind, a, b, loc, txt=None):
    w('(setq e0 (entlast))')
    w('(command "_.%s" "_non" %s "_non" %s "_non" %s)' % (kind, P(a), P(b), P(loc)))
    if txt:
        w('(if (not (eq e0 (entlast))) (progn (setq ed (entget (entlast))) (entmod (subst (cons 1 "%s") (assoc 1 ed) ed))))' % txt)

add = lambda p, q, k=1.0: (p[0]+k*q[0], p[1]+k*q[1])

# ---------------- setup ----------------
w('(vl-load-com)')
w('(setq doc (vla-get-activedocument (vlax-get-acad-object)))')
w('(setq oldos (getvar "OSMODE")) (setvar "OSMODE" 0) (setvar "CMDECHO" 0)')
w('(foreach lt (list "DASHED" "CENTER" "HIDDEN") (if (not (tblsearch "LTYPE" lt)) (foreach f (list "default.lin" "iso.lin" "acad.lin" "acadiso.lin") (if (not (tblsearch "LTYPE" lt)) (vl-catch-all-apply (quote vla-load) (list (vla-get-linetypes doc) lt f))))))')
w('(setvar "LTSCALE" 0.25) (setvar "PSLTSCALE" 0)')
w('(if (not (tblsearch "STYLE" "GR")) (entmake (list (cons 0 "STYLE") (cons 100 "AcDbSymbolTableRecord") (cons 100 "AcDbTextStyleTableRecord") (cons 2 "GR") (cons 70 0) (cons 40 0.0) (cons 41 1.0) (cons 50 0.0) (cons 71 0) (cons 42 0.15) (cons 3 "arial.ttf") (cons 4 ""))))')
layers = [  # name, color, linetype, lineweight (1/100 mm)
    ('WALLS', 7, 'Continuous', 50), ('DOORS', 2, 'Continuous', 25), ('STAIRS', 4, 'Continuous', 25),
    ('HIDDEN', 6, 'DASHED', 25), ('EQUIP', 3, 'Continuous', 35), ('SECTION', 1, 'CENTER', 50),
    ('DIM', 8, 'Continuous', 18), ('TEXT', 7, 'Continuous', 25), ('LIFT', 30, 'Continuous', 35)]
for n, c, lt, lw in layers:
    w('(if (not (tblsearch "LAYER" "%s")) (entmake (list (cons 0 "LAYER") (cons 100 "AcDbSymbolTableRecord") (cons 100 "AcDbLayerTableRecord") (cons 2 "%s") (cons 70 0) (cons 62 %d) (cons 6 (if (tblsearch "LTYPE" "%s") "%s" "Continuous")) (cons 370 %d))))' % (n, n, c, lt, lt, lw))

# ---------------- geometry (metres) ----------------
k = 0.10                       # slope of the top (street) wall
yin = lambda x: 3.30 + k*x     # inner face of top wall
yout = lambda x: 3.50 + k*x    # outer face
XP0, XP1 = 5.20, 5.30          # DEH front (folding door line)
XR0, XR1 = XP1 + 2.77, XP1 + 2.97  # stair-side wall: hall depth 2.77 measured
XS = XR0 - 1.60                # stair 1.60 wide, passage XP1..XS (~1.17)
XN = XR0 + 0.12                # exit-door niche: door plane 0.12 beyond the wall face
YB = -0.90                     # where the walls below the DEH room are cut
YBK = yin(XS) - 5.95           # back wall face: hall 5.95 long from the street wall
XK = XN - 0.34                 # column 0.34 x 0.14 at the street-wall corner
YD1 = yin(XN) - 0.14; YD0 = YD1 - 2.70   # exit door 2.70 in the side wall, from the column face

# top (street) wall with the entrance opening
line('WALLS', (-1.40, yout(-1.40)), (XR1, yout(XR1)))
line('WALLS', (-1.40, yin(-1.40)), (-0.20, yin(-0.20)))
line('WALLS', (0, yin(0)), (XK, yin(XK)))
pline('WALLS', [(-1.40, yin(-1.40)-0.05), (-1.40, 3.22), (-1.46, 3.26), (-1.34, 3.31), (-1.40, 3.35), (-1.40, yout(-1.40)+0.05)])
# left + bottom wall of the room
pline('WALLS', [(-0.20, yin(-0.20)), (-0.20, -0.20), (XP0, -0.20)])
pline('WALLS', [(0, yin(0)), (0, 0), (XP0, 0)])
# DEH front: 4-leaf folding door 4 x 0.875, clear 3.55, overall 3.60 from the street wall
YT = yin(XP0); YF = YT - 3.60; J = 0.025
line('WALLS', (XP0, YBK), (XP0, YF)); line('WALLS', (XP1, YBK), (XP1, YF)); line('WALLS', (XP0, YF), (XP1, YF))
pline('WALLS', [(XP0, YF), (XP1, YF), (XP1, YF+J), (XP0, YF+J)], closed=True)
pline('WALLS', [(XP0, YT-J), (XP1, YT-J), (XP1, yin(XP1)), (XP0, YT)], closed=True)
line('DOORS', (XP1, YF+J), (XP1, YT-J))
y = YF + J + 0.025
for i in range(4):
    pline('DOORS', [(XP1, y), (XP1+0.40, y+0.4375), (XP1, y+0.875)], lt='DASHED')
    y += 0.875
# right (stair-side) wall down to the back wall
line('WALLS', (XR0, YBK), (XR0, YD0)); line('WALLS', (XR1, YBK-0.50), (XR1, YD0))
line('WALLS', (XR0, YD0), (XR1, YD0)); line('WALLS', (XN, YD1), (XR1, YD1)); line('WALLS', (XR1, YD1), (XR1, yout(XR1)))
YM = (YD0 + YD1)/2   # exit door: two leaves of 1.35
for ya, yb in ((YD0, YM), (YM, YD1)):
    pline('DOORS', [(XN, ya), (XN+0.04, ya), (XN+0.04, yb), (XN, yb)], closed=True)
# leaves open inwards (towards the landing), hinged at the jambs
line('DOORS', (XN, YD0), (XN-1.35, YD0)); arc('DOORS', (XN, YD0), 1.35, 90, 180)
line('DOORS', (XN, YD1), (XN-1.35, YD1)); arc('DOORS', (XN, YD1), 1.35, 180, 270)
text('TEXT', 'ΠΟΡΤΑ ΕΞΟΔΟΥ', (XR1+0.25, (YD0+YD1)/2 - 0.55), 0.12, 90)
# back wall 0.50 and corner column 0.31 x 0.52
line('HIDDEN', (XP1, YBK), (XR0, YBK), lt='DASHED'); line('HIDDEN', (XP0-0.20, YBK-0.50), (XR1, YBK-0.50), lt='DASHED')   # beam overhead (0.35 drop)
pline('WALLS', [(XR0-0.31, YBK), (XR0, YBK), (XR0, YBK+0.52), (XR0-0.31, YBK+0.52)], closed=True)
# cut wall stubs below the room
for x0 in (1.30, 2.75):
    line('WALLS', (x0, -0.20), (x0, YB)); line('WALLS', (x0+0.10, -0.20), (x0+0.10, YB))
for x0, x1 in ((1.30, 1.40), (2.75, 2.85)):
    m = (x0+x1)/2
    pline('WALLS', [(x0-0.05, YB), (m-0.02, YB), (m+0.02, YB-0.05), (m+0.02, YB+0.05), (m+0.06, YB), (x1+0.05, YB)])
# column at the entrance: 0.34 along the street wall, 0.14 proud of it
pline('WALLS', [(XK, yin(XK)), (XN, yin(XN)), (XN, YD1), (XK, yin(XK)-0.14)], closed=True)
pline('WALLS', [(XP0, YBK), (XP0-0.20, YBK), (XP0-0.20, YBK-0.50)])

# goods lift (cross = shaft), still in use
pline('LIFT', [(XP1, 2.80), (XS, 2.80), (XS, 3.80), (XP1, 3.80)], closed=True)
line('LIFT', (XP1, 2.80), (XS, 3.80)); line('LIFT', (XP1, 3.80), (XS, 2.80))
text('LIFT', 'ΑΝΑΒΑΤΟΡΙΟ', (XP1+0.10, 3.42), 0.08)
text('LIFT', 'ΕΜΠΟΡΕΥΜΑΤΩΝ', (XP1+0.10, 3.28), 0.08)

# stair 1.45 wide: landing 1.58 from the street wall, 10 risers ~0.16, treads 0.28
xm = (XS+XR0)/2
XC = (XK + XN)/2
YTOP = yin(XC) - 0.14 - 1.58   # landing 1.58 from the column face
line('STAIRS', (XS, YBK), (XS, yin(XS)))
for i in range(10):
    line('STAIRS', (XS, YTOP - i*0.28), (XR0, YTOP - i*0.28))
line('STAIRS', (xm, YTOP - 9*0.28 - 0.35), (xm, YTOP - 0.05))
solid('STAIRS', (xm, YTOP + 0.17), (xm-0.12, YTOP - 0.05), (xm+0.12, YTOP - 0.05))
text('TEXT', '10 x 0.16 / 0.28', (XS+0.12, YTOP - 9*0.28 - 0.30), 0.10)
XE = XN - 1.45; YE = yin(XK) - 2.864   # 2.864 from the wall face beside the column
pline('HIDDEN', [(XE, yin(XE)), (XE, YE), (XN, YE)], lt='DASHED')
text('TEXT', 'εσοχή οροφής h=1.90', (XE+0.08, YE+0.10), 0.10)

# 3 pipes D15 encased in concrete (hidden)
pline('HIDDEN', [(5.10, 3.32), (8.45, 3.32), (8.45, 3.52), (5.10, 3.52)], closed=True, lt='DASHED')

# grating opening 0.30 x 0.60, 0.10 from left wall, 0.20 from top wall
gy1 = yin(0.25) - 0.20; gy0 = gy1 - 0.60
pline('EQUIP', [(0.10, gy0), (0.40, gy0), (0.40, gy1), (0.10, gy1)], closed=True)
for i in range(1, 12):
    line('EQUIP', (0.10, gy0+i*0.05), (0.40, gy0+i*0.05))

# cable trench 2.90 x 0.60 parallel to the top wall, 1.00 from left wall, 0.50 from top wall
a = math.atan(k); u = (math.cos(a), math.sin(a)); n = (math.sin(a), -math.cos(a))
B = (0.0, 3.30 - 1.10/math.cos(a))        # left wall at trench bottom edge
P3 = add(B, u, 1.00); P2 = add(P3, u, 2.90)
P0 = add(P3, n, -0.60); P1 = add(P2, n, -0.60)
T = lambda s, t: add(add(P0, u, s), n, t)  # s along, t across (0 top .. 0.60 bottom)
pline('EQUIP', [P0, P1, P2, P3], closed=True)
cells = [0.0, 0.50, 1.15, 1.75, 2.50, 2.90]
for s in cells[1:-1]:
    line('EQUIP', T(s, 0), T(s, 0.60))
pline('HIDDEN', [T(-0.15, -0.10), T(3.20, -0.10), T(3.20, 0.70), T(-0.15, 0.70)], closed=True, lt='DASHED')
pline('EQUIP', [T(0.10, 0.52), T(2.78, 0.52), T(2.78, 0.06)], width=0.04)
labels = ['K1/Δ1', 'K2/Δ4', 'K1/Δ1', 'K3/Δ5', 'K1/Δ3']
for i, lab in enumerate(labels):
    text('TEXT', lab, T((cells[i]+cells[i+1])/2, 0.30), 0.09, math.degrees(a), center=True)

# floor opening with trap-door grating
pline('EQUIP', [(4.30, 0.20), (5.00, 0.20), (5.00, 0.90), (4.30, 0.90)], closed=True)
w('(entmake (list (cons 0 "CIRCLE") (cons 8 "TEXT") (cons 10 (list 4.65 0.55 0.0)) (cons 40 0.025)))')
# transformer / M/S position (hidden)
pline('HIDDEN', [(3.70, -0.50), (3.90, -0.50), (3.90, 0.15), (3.70, 0.15)], closed=True, lt='DASHED')
text('TEXT', 'Μ/Σ', (3.40, -0.85), 0.15, 15)

# section line A-A
YA = 2.76
line('SECTION', (-1.90, YA), (9.00, YA), lt='CENTER')
for x, side in ((-1.90, 1), (9.00, -1)):
    pline('SECTION', [(x, YA), (x, 3.20)], width=0.03)
    solid('SECTION', (x, 3.48), (x, 3.18), (x+side*0.14, 3.18))
    text('TEXT', 'A', (x-0.40 if side == 1 else x+0.15, 3.25), 0.28)

# ---------------- notes ----------------
text('TEXT', '%%uΚΑΤΟΨΙΣ', (2.70, 5.75), 0.30)
n1 = ['Άνοιγμα διαστάσεων 0.60x0.30 εκα-',
      'λυφθή καταλλήλως υπό του κατα-',
      'ναλωτού δι\' εσχάρας.']
for i, s in enumerate(n1):
    text('TEXT', s, (-2.60, 6.55 - i*0.25), 0.13)
line('TEXT', (-2.70, 5.95), (1.40, 5.95)); line('TEXT', (-2.70, 5.95), (0.22, 3.02)); arrowhead('TEXT', (0.22, 3.02), (-2.70, 5.95))

n2 = ['3 σιδηροσωλήνες Φ15εκ. ή (PVC)',
      'εγκιβωτισμένες στον μπετόν']
for i, s in enumerate(n2):
    text('TEXT', s, (5.45, 7.55 - i*0.25), 0.13)
line('TEXT', (5.40, 7.22), (8.25, 7.22)); line('TEXT', (8.25, 7.22), (7.00, 3.52)); arrowhead('TEXT', (7.00, 3.52), (8.25, 7.22))

n3 = ['Άνοιγμα επί της πλακός. Δι\' εσχά-',
      'ρα καταπακτής βλέπε σχ. 3-40609']
for i, s in enumerate(n3):
    text('TEXT', s, (0.60, -1.65 - i*0.25), 0.13)
line('TEXT', (0.55, -1.98), (3.95, -1.98)); line('TEXT', (3.95, -1.98), (4.65, 0.55))

# ---------------- dimensions ----------------
w('(setvar "CLAYER" "DIM")')
for var, val in [('DIMSCALE', '1.0'), ('DIMTXT', '0.13'), ('DIMASZ', '0.08'), ('DIMTSZ', '0.06'), ('DIMEXO', '0.05'),
                 ('DIMEXE', '0.08'), ('DIMGAP', '0.03'), ('DIMDEC', '2'), ('DIMZIN', '0'), ('DIMTAD', '1'),
                 ('DIMTIH', '0'), ('DIMTOH', '0'), ('DIMLUNIT', '2'), ('DIMDSEP', '"."'), ('DIMTXSTY', '"GR"'),
                 ('DIMATFIT', '3'), ('DIMTMOVE', '0')]:
    w('(vl-catch-all-apply (quote setvar) (list "%s" %s))' % (var, val))
dim('DIMLINEAR', (-0.20, yout(-0.20)), (XR1, yout(XR1)), (4.0, 5.05))

dim('DIMLINEAR', (0, 0), (XP0, 0), (2.6, -1.30))
dim('DIMLINEAR', (XP1, YBK), (XS, YBK), (5.9, YBK-0.75))
dim('DIMLINEAR', (XS, YBK), (XR0, YBK), (7.3, YBK-0.75))
dim('DIMLINEAR', (XP1, YBK), (XR0, YBK), (6.7, YBK-1.10))
dim('DIMLINEAR', (0, 0), (0, 3.30), (-0.75, 1.6))
dim('DIMLINEAR', (-0.20, 0.6), (0, 0.6), (-0.1, 0.75))
dim('DIMLINEAR', (0.6, -0.20), (0.6, 0), (0.75, -0.1))
dim('DIMLINEAR', (0, gy0), (0.10, gy0), (0.05, gy0-0.25))
dim('DIMLINEAR', (0.25, gy1), (0.25, yin(0.25)), (0.60, gy1+0.1))
dim('DIMALIGNED', B, P3, add(add(B, u, 0.5), n, 0.40))
dim('DIMALIGNED', P3, P2, add(add(P3, u, 1.4), n, 0.40))
W = add(P1, n, -0.50)
dim('DIMALIGNED', W, P1, add(add(W, u, 0.55), n, 0.25))
dim('DIMALIGNED', P1, P2, add(add(P1, u, 0.55), n, 0.30))
dim('DIMLINEAR', (XP1, YF), (XP1, YT), (XS-0.15, 1.9))
dim('DIMLINEAR', (XS-0.05, yin(XS-0.05)), (XS-0.05, YBK), (XS-0.40, -1.0))
dim('DIMLINEAR', (XC, yin(XC)-0.14), (XC, YTOP), (XC-0.25, 3.1))
dim('DIMLINEAR', (XK, yin(XK)-0.14), (XN, YD1), (XC, 3.62))
dim('DIMLINEAR', (XR1, YD0), (XR1, YD1), (XR1+0.55, 2.0))
dim('DIMLINEAR', (XR0, YD0), (XN, YD0), (XR0+0.06, YD0-0.25))
dim('DIMLINEAR', (XE, YE), (XN, YE), (7.4, YE-0.25))
dim('DIMLINEAR', (XK, yin(XK)), (XK, YE), (XK-0.30, 2.0))
dim('DIMLINEAR', (XN, yin(XN)), (XN, YD1), (XR1+0.55, yin(XN)-0.07))
dim('DIMLINEAR', (5.00, 0.90), (XP0, 0.90), (5.1, 1.10))
dim('DIMLINEAR', (4.30, 0), (4.30, 0.20), (4.10, 0.1))

w('(setvar "CLAYER" "0") (setvar "OSMODE" oldos) (setvar "CMDECHO" 1)')
w('(command "_.ZOOM" "_E")')
w('(princ "\\nKATOPSI OK") (princ)')

open(sys.argv[1], 'w', encoding='ascii').write('\n'.join(out) + '\n')
print(len(out), 'lines')
