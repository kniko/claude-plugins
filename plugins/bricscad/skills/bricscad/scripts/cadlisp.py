"""Tiny LISP writer for BricsCAD (used through the bricscad MCP `command` tool).

Usage (in a generator script):

    import sys; sys.path.insert(0, r'<this folder>')
    from cadlisp import *
    begin(layers=[('WALLS', 7, 'Continuous', 50), ('DIM', 8, 'Continuous', 18)])
    line('WALLS', (0, 0), (5, 0))
    text('TEXT', 'ΚΑΤΟΨΗ', (0, -1), 0.30)
    dim('DIMLINEAR', (0, 0), (5, 0), (2.5, -0.6))
    ext3d('3D_WALLS', [(0, 0), (5, 0), (5, 0.2), (0, 0.2)], -2.0, 0.925)
    end('plan.lsp', log=r'C:/.../plan_log.txt')

Then in BricsCAD: (load "C:/.../plan.lsp") and read the log file back.

Everything is written as pure ASCII: non-ASCII characters (Greek) become \\U+XXXX,
which BricsCAD turns back into Unicode in TEXT/MTEXT/DIM strings.
Coordinates are in drawing units (metres in our drawings). OFFSET shifts every point
(set it to place a section/elevation/3D model next to the plan).
"""
import math

out = []
OFFSET = [0.0, 0.0]          # added to every 2D point (x, y)


def w(s):
    out.append(s)


def esc(s):
    """Python str -> LISP string body (ASCII, Greek as \\U+XXXX)."""
    r = []
    for ch in s:
        if ord(ch) < 128:
            r.append('\\\\' if ch == '\\' else ('\\"' if ch == '"' else ch))
        else:
            r.append('\\\\U+%04X' % ord(ch))
    return ''.join(r)


def P(p, z=0.0):
    return '(list %.4f %.4f %.4f)' % (p[0] + OFFSET[0], p[1] + OFFSET[1], z)


def P2(p):
    return '(list %.4f %.4f)' % (p[0] + OFFSET[0], p[1] + OFFSET[1])


# ---------------------------------------------------------------- setup / teardown
def begin(layers=(), ltscale=0.25, text_font='arial.ttf'):
    """Common header: COM, OSMODE off, linetypes, text style GR, layers, hatch + 3D + log helpers.
    layers: (name, color, linetype, lineweight_1/100mm); a negative color creates the layer OFF."""
    w('(vl-load-com)')
    w('(setq doc (vla-get-activedocument (vlax-get-acad-object)) ms (vla-get-modelspace doc) nok 0 nfail 0 logf nil)')
    w('(setq oldos (getvar "OSMODE")) (setvar "OSMODE" 0) (setvar "CMDECHO" 0)')
    w('(foreach lt (list "DASHED" "CENTER" "HIDDEN") (if (not (tblsearch "LTYPE" lt)) (foreach f (list "default.lin" "iso.lin" "acad.lin" "acadiso.lin")'
      ' (if (not (tblsearch "LTYPE" lt)) (vl-catch-all-apply (quote vla-load) (list (vla-get-linetypes doc) lt f))))))')
    w('(setvar "LTSCALE" %g) (setvar "PSLTSCALE" 0)' % ltscale)
    w('(if (not (tblsearch "STYLE" "GR")) (entmake (list (cons 0 "STYLE") (cons 100 "AcDbSymbolTableRecord") (cons 100 "AcDbTextStyleTableRecord")'
      ' (cons 2 "GR") (cons 70 0) (cons 40 0.0) (cons 41 1.0) (cons 50 0.0) (cons 71 0) (cons 42 0.15) (cons 3 "%s") (cons 4 ""))))' % text_font)
    for n, c, lt, lw in layers:
        w('(if (not (tblsearch "LAYER" "%s")) (entmake (list (cons 0 "LAYER") (cons 100 "AcDbSymbolTableRecord") (cons 100 "AcDbLayerTableRecord")'
          ' (cons 2 "%s") (cons 70 0) (cons 62 %d) (cons 6 (if (tblsearch "LTYPE" "%s") "%s" "Continuous")) (cons 370 %d))))' % (n, n, c, lt, lt, lw))
    # hatch the last closed polyline; tries the patterns in order (AR-CONC is often missing -> ANSI31)
    w('(defun hatchlast (pats lay / pl h r) (setq pl (vlax-ename->vla-object (entlast)))'
      ' (foreach pat pats (if (not r) (progn (setq r (vl-catch-all-apply (function (lambda ()'
      ' (setq h (vla-AddHatch ms 1 (car pat) :vlax-true)) (vla-put-Layer h lay) (vla-put-PatternScale h (cadr pat))'
      ' (vla-AppendOuterLoop h (vlax-make-variant (vlax-safearray-fill (vlax-make-safearray vlax-vbObject (quote (0 . 0))) (list pl)))) (vla-Evaluate h) T))))'
      ' (if (vl-catch-all-error-p r) (progn (if h (vl-catch-all-apply (quote vla-Delete) (list h))) (setq r nil h nil)))))) (princ))')
    # closed LWPOLYLINE at z0 -> region -> extruded 3D solid of height z1-z0 on layer lay
    w('(defun ext3d (lay pts z0 z1 / r)'
      ' (entmake (append (list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 "0") (cons 100 "AcDbPolyline") (cons 90 (length pts)) (cons 70 1) (cons 38 z0))'
      ' (mapcar (function (lambda (p) (cons 10 p))) pts)))'
      ' (setq r (vl-catch-all-apply (function (lambda (/ pl arr reg sol)'
      '  (setq pl (vlax-ename->vla-object (entlast)))'
      '  (setq arr (vlax-make-safearray vlax-vbObject (quote (0 . 0)))) (vlax-safearray-put-element arr 0 pl)'
      '  (setq reg (car (vlax-safearray->list (vlax-variant-value (vla-AddRegion ms arr)))))'
      '  (setq sol (vla-AddExtrudedSolid ms reg (- z1 z0) 0.0)) (vla-put-Layer sol lay)'
      '  (vla-Delete reg) (vla-Delete pl) T))))'
      ' (if (vl-catch-all-error-p r) (progn (setq nfail (1+ nfail)) (logw (strcat "FAIL " lay ": " (vl-catch-all-error-message r)))) (setq nok (1+ nok))))')
    w('(defun logw (s) (if logf (write-line s logf)) (princ (strcat "\\n" s)))')
    w('(defun lasth () (cdr (assoc 5 (entget (entlast)))))')


def log_open(path):
    """Open a log file; the MCP `command` tool returns no output, so results go to a file you read back."""
    w('(setq logf (open "%s" "w"))' % path.replace('\\', '/'))


def log(lisp_string_expr):
    """log('"text"') or log('(strcat "made " (lasth))')."""
    w('(logw %s)' % lisp_string_expr)


def end(path, log=None):
    w('(logw (strcat "solids ok " (itoa nok) " failed " (itoa nfail)))')
    w('(setvar "CLAYER" "0") (setvar "OSMODE" oldos) (setvar "CMDECHO" 1)')
    w('(if logf (progn (close logf) (setq logf nil))) (princ)')
    body = out[:]
    if log:
        hdr = [l for l in body if l.startswith(('(vl-load-com)', '(setq doc', '(setq oldos', '(foreach lt', '(setvar "LTSCALE"', '(if (not (tblsearch "STYLE"', '(defun'))]
        rest = [l for l in body if l not in hdr]
        body = hdr + ['(setq logf (open "%s" "w"))' % log.replace('\\', '/')] + rest
    src = '\n'.join(body) + '\n'
    assert src.count('(') == src.count(')'), 'unbalanced parentheses'
    open(path, 'w', encoding='ascii').write(src)
    return len(body)


# ---------------------------------------------------------------- 2D entities
def line(lay, a, b, lt=None):
    extra = ' (cons 6 "%s")' % lt if lt else ''
    w('(entmake (list (cons 0 "LINE") (cons 8 "%s")%s (cons 10 %s) (cons 11 %s)))' % (lay, extra, P(a), P(b)))


def pline(lay, pts, closed=False, width=0.0, lt=None):
    s = '(entmake (append (list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 "%s")' % lay
    if lt:
        s += ' (cons 6 "%s")' % lt
    s += ' (cons 100 "AcDbPolyline") (cons 90 %d) (cons 70 %d) (cons 43 %.3f))' % (len(pts), 1 if closed else 0, width)
    s += ' (list ' + ' '.join('(cons 10 %s)' % P2(p) for p in pts) + ')))'
    w(s)


def concrete(pts, lay='WALLS', hatch_lay='HATCH', pats=(('AR-CONC', 0.004), ('ANSI31', 0.02))):
    """Closed outline + concrete hatch (earth: ANSI31 0.08)."""
    pline(lay, pts, closed=True)
    w('(hatchlast (list %s) "%s")' % (' '.join('(list "%s" %g)' % p for p in pats), hatch_lay))


def arc(lay, c, r, a1, a2, lt=None):
    """Counter-clockwise from a1 to a2 (degrees)."""
    extra = ' (cons 6 "%s")' % lt if lt else ''
    w('(entmake (list (cons 0 "ARC") (cons 8 "%s")%s (cons 10 %s) (cons 40 %.4f) (cons 50 %.6f) (cons 51 %.6f)))'
      % (lay, extra, P(c), r, math.radians(a1), math.radians(a2)))


def solid(lay, p1, p2, p3, p4=None):
    """2D filled SOLID (arrowheads, level markers). Note the vertex order 1-2-4-3."""
    w('(entmake (list (cons 0 "SOLID") (cons 8 "%s") (cons 10 %s) (cons 11 %s) (cons 12 %s) (cons 13 %s)))'
      % (lay, P(p1), P(p2), P(p3), P(p4 or p3)))


def text(lay, s, p, h, rot=0.0, center=False, style='GR'):
    if center:
        w('(entmake (list (cons 0 "TEXT") (cons 8 "%s") (cons 7 "%s") (cons 10 %s) (cons 11 %s) (cons 40 %.3f) (cons 50 %.6f) (cons 72 1) (cons 73 2) (cons 1 "%s")))'
          % (lay, style, P(p), P(p), h, math.radians(rot), esc(s)))
    else:
        w('(entmake (list (cons 0 "TEXT") (cons 8 "%s") (cons 7 "%s") (cons 10 %s) (cons 40 %.3f) (cons 50 %.6f) (cons 1 "%s")))'
          % (lay, style, P(p), h, math.radians(rot), esc(s)))


def arrowhead(lay, tip, frm, L=0.15, W=0.05):
    dx, dy = tip[0] - frm[0], tip[1] - frm[1]
    d = math.hypot(dx, dy); ux, uy = dx / d, dy / d
    b = (tip[0] - ux * L, tip[1] - uy * L)
    solid(lay, tip, (b[0] - uy * W, b[1] + ux * W), (b[0] + uy * W, b[1] - ux * W))


def level(x, y, txt, lay='TEXT', h=0.13):
    """Section level marker: triangle + line + text (e.g. '+1.20')."""
    solid(lay, (x, y), (x - 0.08, y + 0.14), (x + 0.08, y + 0.14))
    line(lay, (x - 0.08, y + 0.14), (x + 0.60, y + 0.14))
    text(lay, txt, (x + 0.02, y + 0.20), h)


def dim(kind, a, b, loc, txt=None, lay='DIM'):
    """Real associative dimension via the command line, so it shows the MEASURED value.
    kind: 'DIMLINEAR' or 'DIMALIGNED'. For a vertical DIMLINEAR put loc's y between a and b
    (otherwise it may come out horizontal = 0.00). txt only for prefixes like '~<>' - never
    to fake a number."""
    w('(setvar "CLAYER" "%s") (setq e0 (entlast))' % lay)
    w('(command "_.%s" "_non" %s "_non" %s "_non" %s)' % (kind, P(a), P(b), P(loc)))
    if txt:
        w('(if (not (eq e0 (entlast))) (progn (setq ed (entget (entlast))) (entmod (subst (cons 1 "%s") (assoc 1 ed) ed))))' % esc(txt))
    w('(setvar "CLAYER" "0")')


# ---------------------------------------------------------------- 3D
def ext3d(lay, pts, z0, z1):
    """Prism: plan outline pts (2D, OFFSET applied) extruded from z0 to z1."""
    w('(ext3d "%s" (list %s) %.4f %.4f)' % (lay, ' '.join(P2(p) for p in pts), z0, z1))


def box(lay, x0, y0, x1, y1, z0, z1):
    ext3d(lay, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1)


def subtract_last_from(handle_var):
    """(setq <handle_var> obj) must exist; subtracts the last-made solid from it (vla-Boolean 2 = subtract)."""
    w('(setq r (vl-catch-all-apply (quote vla-Boolean) (list %s 2 (vlax-ename->vla-object (entlast)))))'
      ' (logw (if (vl-catch-all-error-p r) (strcat "CUT FAIL " (vl-catch-all-error-message r)) "cut ok"))' % handle_var)
