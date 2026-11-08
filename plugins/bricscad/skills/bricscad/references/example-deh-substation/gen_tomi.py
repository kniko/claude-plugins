# Generates tomi.lsp: section A-A, drawn under the plan with the same x axis.
import math, sys

out = []
def w(s): out.append(s)
DY = -8.5   # vertical offset of the section (section level 0.00 -> drawing y = DY)

def esc(s):
    r = []
    for ch in s:
        if ord(ch) < 128:
            r.append('\\\\' if ch == '\\' else ('\\"' if ch == '"' else ch))
        else:
            r.append('\\\\U+%04X' % ord(ch))
    return ''.join(r)

def P(p): return '(list %.4f %.4f 0.0)' % (p[0], p[1] + DY)

def line(lay, a, b, lt=None):
    extra = ' (cons 6 "%s")' % lt if lt else ''
    w('(entmake (list (cons 0 "LINE") (cons 8 "%s")%s (cons 10 %s) (cons 11 %s)))' % (lay, extra, P(a), P(b)))

def pline(lay, pts, closed=False, width=0.0, lt=None):
    s = '(entmake (append (list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 "%s")' % lay
    if lt: s += ' (cons 6 "%s")' % lt
    s += ' (cons 100 "AcDbPolyline") (cons 90 %d) (cons 70 %d) (cons 43 %.3f))' % (len(pts), 1 if closed else 0, width)
    s += ' (list ' + ' '.join('(cons 10 (list %.4f %.4f))' % (p[0], p[1] + DY) for p in pts) + ')))'
    w(s)

def concrete(pts):
    pline('WALLS', pts, closed=True)
    w('(hatchlast)')

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

def level(x, y, txt):
    solid('TEXT', (x, y), (x-0.08, y+0.14), (x+0.08, y+0.14))
    line('TEXT', (x-0.08, y+0.14), (x+0.60, y+0.14))
    text('TEXT', txt, (x+0.02, y+0.20), 0.13)

def dim(kind, a, b, loc, txt=None):
    w('(setq e0 (entlast))')
    w('(command "_.%s" "_non" %s "_non" %s "_non" %s)' % (kind, P(a), P(b), P(loc)))
    if txt:
        w('(if (not (eq e0 (entlast))) (progn (setq ed (entget (entlast))) (entmod (subst (cons 1 "%s") (assoc 1 ed) ed))))' % txt)

# ---------------- setup ----------------
w('(vl-load-com)')
w('(setq ms (vla-get-modelspace (vla-get-activedocument (vlax-get-acad-object))))')
w('(setq oldos (getvar "OSMODE")) (setvar "OSMODE" 0) (setvar "CMDECHO" 0)')
w('(if (not (tblsearch "LAYER" "HATCH")) (entmake (list (cons 0 "LAYER") (cons 100 "AcDbSymbolTableRecord") (cons 100 "AcDbLayerTableRecord") (cons 2 "HATCH") (cons 70 0) (cons 62 8) (cons 6 "Continuous") (cons 370 13))))')
# concrete hatch for the last closed polyline (AR-CONC, falls back to ANSI31)
w('(defun hatchlast (/ pl h r) (setq pl (vlax-ename->vla-object (entlast)))'
  ' (foreach pat (list (list "AR-CONC" 0.004) (list "ANSI31" 0.02))'
  '  (if (not r) (progn (setq r (vl-catch-all-apply (function (lambda () (setq h (vla-AddHatch ms 1 (car pat) :vlax-true)) (vla-put-Layer h "HATCH") (vla-put-PatternScale h (cadr pat))'
  ' (vla-AppendOuterLoop h (vlax-make-variant (vlax-safearray-fill (vlax-make-safearray vlax-vbObject (quote (0 . 0))) (list pl)))) (vla-Evaluate h) T))))'
  ' (if (vl-catch-all-error-p r) (progn (if h (vl-catch-all-apply (quote vla-Delete) (list h))) (setq r nil h nil)))))) (princ))')

# ---------------- structure (section levels in metres) ----------------
# roof slab +1.00/+1.20, stepping up over the stair to +1.62/+1.77
concrete([(-1.60, 0.925), (6.74, 0.925), (6.74, 1.52), (8.27, 1.52), (8.27, 1.77), (6.54, 1.77), (6.54, 1.20), (-1.60, 1.20)])
# landing at -0.38
# landing slab + concrete retaining wall (0.20) under it, one piece
concrete([(6.47, -0.38), (8.27, -0.38), (8.27, -2.10), (8.07, -2.10), (8.07, -0.53), (6.47, -0.53)])
pline('DOORS', [(8.19, -0.38), (8.23, -0.38), (8.23, 1.506), (8.19, 1.506)], closed=True)   # exit door in the side wall
# basin under the DEH room: concrete bottom, closed walls flush with the room walls, slab 0.15 the cubicles stand on
concrete([(-0.20, -3.00), (5.60, -3.00), (5.60, -2.80), (-0.20, -2.80)])
concrete([(-0.20, -2.80), (0.00, -2.80), (0.00, -2.15), (-0.20, -2.15)])
concrete([(5.40, -2.80), (5.60, -2.80), (5.60, -2.15), (5.40, -2.15)])
for x0, x1 in ((-0.20, 0.10), (0.40, 1.10), (3.50, 5.60)):
    concrete([(x0, -2.15), (x1, -2.15), (x1, -2.00), (x0, -2.00)])
line('WALLS', (0.00, -2.00), (5.60, -2.00)); line('WALLS', (0.00, -2.15), (5.60, -2.15))
# walls cut / seen (from floor -2.00 to slab underside +1.00)
for x in (-1.60, -1.40, -0.20, 0.00, 5.20, 5.30):
    line('WALLS', (x, -2.00), (x, 0.925))
line('WALLS', (-1.60, -2.00), (0.00, -2.00))
line('WALLS', (5.60, -2.00), (8.07, -2.00))
# right wall below the landing (0.20) and building line
line('HIDDEN', (8.27, 1.77), (8.27, 2.10), lt='DASHED')
text('TEXT', 'ΟΙΚΟΔ. ΓΡΑΜΜΗ', (8.62, 0.10), 0.13, 90)

# switchgear cubicles over the trench (same x as in the plan)
cx = [0.965 + 0.995*s for s in (0.0, 0.50, 1.15, 1.75, 2.50, 2.90)]
pline('EQUIP', [(cx[0], -2.00), (cx[-1], -2.00), (cx[-1], 0.10), (cx[0], 0.10)], closed=True, lt='DASHED')
for x in cx[1:-1]:
    line('EQUIP', (x, -2.00), (x, 0.10), lt='DASHED')

# 3 pipes D15 rising from the trench (-2.50) to the building line (-2.08)
pb0, pb1 = (5.30, -2.50), (8.45, -2.23)
line('HIDDEN', pb0, pb1, lt='DASHED')
line('HIDDEN', (pb0[0], pb0[1]+0.15), (pb1[0], pb1[1]+0.15), lt='DASHED')
line('HIDDEN', pb0, (pb0[0], pb0[1]+0.15)); line('HIDDEN', pb1, (pb1[0], pb1[1]+0.15))

# ---------------- levels, notes ----------------
level(5.60, 1.20, '+1.20')
level(6.80, 1.77, '+1.77')
level(7.00, -0.38, '-0.38')
level(6.40, -2.00, '-2.00')
text('TEXT', '%%uΤΟΜΗ Α-Α', (0.90, 2.40), 0.30)
px = 6.31; py = pb0[1] + (px-pb0[0])/(pb1[0]-pb0[0])*(pb1[1]-pb0[1])
n2 = ['3 σιδηροσωλήνες Φ15εκ. ή (PVC)',
      'εγκιβωτισμένες στον μπετόν']
for i, s in enumerate(n2):
    text('TEXT', s, (5.95, -4.15 - i*0.25), 0.13)
line('TEXT', (5.85, -4.45), (8.75, -4.45)); line('TEXT', (5.85, -4.45), (px, py)); arrowhead('TEXT', (px, py), (5.85, -4.45))

# ---------------- dimensions ----------------
w('(setvar "CLAYER" "DIM")')
dim('DIMLINEAR', (-1.60, -2.00), (-1.60, 0.925), (-2.20, -0.5))
dim('DIMLINEAR', (0.00, -2.00), (0.00, -3.00), (-0.60, -2.5))
dim('DIMLINEAR', (5.40, -2.80), (5.40, -2.50), (5.15, -2.65))
dim('DIMLINEAR', (6.62, -0.38), (6.62, 0.925), (6.70, 0.3))
dim('DIMLINEAR', (6.74, 0.925), (6.74, 1.52), (6.92, 1.2))
dim('DIMLINEAR', (7.70, -0.38), (7.70, 1.52), (7.95, 0.6))
dim('DIMLINEAR', (8.27, -0.38), (8.45, -2.08), (8.95, -1.2), txt='~<>')
dim('DIMLINEAR', (8.07, -1.75), (8.27, -1.75), (8.2, -1.60))

w('(setvar "CLAYER" "0") (setvar "OSMODE" oldos) (setvar "CMDECHO" 1)')
w('(princ "\\nTOMI OK") (princ)')

open(sys.argv[1], 'w', encoding='ascii').write('\n'.join(out) + '\n')
print(len(out), 'lines')
