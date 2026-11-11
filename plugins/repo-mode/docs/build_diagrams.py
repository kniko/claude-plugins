#!/usr/bin/env python3
"""Generates the README diagrams (docs/*.svg): blueprint style, model names in their own colors.
Run: python3 docs/build_diagrams.py
Each SVG is a self-contained dark card, so it looks the same on light and dark GitHub themes."""
import os
from xml.sax.saxutils import escape

OUT = os.path.dirname(os.path.abspath(__file__))
MONO = "ui-monospace, 'Cascadia Mono', Consolas, 'DejaVu Sans Mono', Menlo, monospace"
INK, GRID, LINE, TX, MU = "#0b1f3f", "#16305c", "#7db3ff", "#eaf2ff", "#8fb0e0"
AMBER, GREEN = "#ffb347", "#5fd07a"
# one color per model family, used for the model name and the rank dots
MODEL = {"Haiku": ("#5fd07a", 1), "Sonnet": ("#39c5cf", 2), "Opus": ("#bc8cff", 3), "Fable": ("#ff7eb6", 4)}
DASH = ' stroke-dasharray="5 4"'


def t(x, y, s, size=12, fill=TX, weight=400, anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}">{escape(s)}</text>'


def dots(x, y, n, col):
    return "".join(f'<circle cx="{x + i * 13}" cy="{y}" r="4.2" fill="{col if i < n else "none"}" stroke="{col}" stroke-width="1.2"/>' for i in range(4))


def box(x, y, w, h, name, model=None, lines=(), col=LINE, title_size=15):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{INK}" stroke="{col}" stroke-width="1.4"/>'
    s += t(x + 14, y + 28, name, title_size, TX, 700)
    cy = y + 28
    if model:
        mc, rank = MODEL[model.split()[0]]
        cy += 21
        s += dots(x + 19, cy - 4, rank, mc) + t(x + 19 + 4 * 13 + 4, cy, model, 12, mc, 700)
    for l in lines:
        cy += 19 if (model or lines.index(l)) else 20
        s += t(x + 14, cy, l, 11.5, MU)
    return s


def pill(cx, ybottom, lines, col=LINE, fg=TX):
    lines = [lines] if isinstance(lines, str) else lines
    w = max(len(l) for l in lines) * 6.6 + 16
    h = 8 + 14 * len(lines)
    y = ybottom - h
    s = f'<rect x="{cx - w/2:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h}" fill="{INK}" stroke="{col}" stroke-width="1"/>'
    for i, l in enumerate(lines):
        s += t(f"{cx:.0f}", f"{y + 15 + i*14:.0f}", l, 10.5, fg, 400, "middle")
    return s


def arrow(d, dashed=False, col=LINE, both=False):
    m = ' marker-end="url(#a)"' + (' marker-start="url(#a)"' if both else "")
    return f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.4"{DASH if dashed else ""}{m}/>'


def svg(w, h, title, desc, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d" font-family="{MONO}">\n'
            f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>\n'
            f'<defs><pattern id="g" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="{GRID}" stroke-width="0.6"/></pattern>'
            f'<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M1 1 L9 5 L1 9" fill="none" stroke="{LINE}" stroke-width="1.5"/></marker>'
            +"".join(f'<marker id="m-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M1 1 L9 5 L1 9" fill="none" stroke="{v[0]}" stroke-width="1.5"/></marker>' for k, v in MODEL.items())+'</defs>\n'
            f'<rect width="{w}" height="{h}" rx="12" fill="{INK}"/><rect width="{w}" height="{h}" rx="12" fill="url(#g)"/>\n{body}\n</svg>\n')


STR = {
    "en": dict(
        you="YOU", main="main session", main_l=["effort medium", "keeps only the results"], adv="advisor", adv_l=["reads the whole chat"],
        ask="consults", advice="advice", inside="stays inside:", cards=[
            ("Explore", "Haiku", "reads many files", ["path:line"], "10+ files"),
            ("test-runner", "Haiku", "runs the full suite", ["failures only"], "tests · logs"),
            ("audit", "Sonnet", "reads the diff", ["findings +", "evidence"], "before «done»"),
            ("general-purpose", "Sonnet", "any task · also Plan", ["summary"], "everything else"),
            ("escalate", "Fable", "reads, reproduces", ["diagnosis +", "next step"], ["advisor + 2 tries", "failed"])],
        caption="each subagent has its own context: the long output stays inside, only the result comes back up", rank="model rank",
        legend="dashed = only after the advisor and two of its own tries failed",
        wt="How the work is split", wd="The main session delegates to subagents with their own context, consults the advisor at decision points, and calls escalate only after the advisor and two tries failed.",
        setup=dict(cmd="/repo-mode:setup", wizard="wizard · questions and reads only",
                   steps=[("Check repo", ["version", "settings"]), ("Round 1", ["model · advisor", "agents · scope"]),
                          ("Round 2", ["model per agent", "+ the rest"]), ("Rounds 3–4", ["effort · workflows", "rules · deny", "secrets · escalate", "test filter · LSP"]),
                          ("Plan", ["before / after", "of every file"])],
                   approve="Approve?", yes="yes", no="no", nothing="Nothing is written", writes="Writes",
                   writes_l=["settings.local.json · agents/*.md", "CLAUDE.local.md · hooks/ · .git/info/exclude", "repo-mode.json (state, for /off)"],
                   back="or change your answers → back to Round 1",
                   title="How the setup is created", desc="The wizard asks and reads only, shows a before/after plan, and writes files only after you approve.")),
    "el": dict(
        you="ΕΣΥ", main="κύριο session", main_l=["effort medium", "κρατά μόνο τα αποτελέσματα"], adv="advisor", adv_l=["βλέπει όλη τη συζήτηση"],
        ask="ρωτά", advice="συμβουλή", inside="μένει μέσα:", cards=[
            ("Explore", "Haiku", "σαρώνει αρχεία", ["path:line"], "10+ αρχεία"),
            ("test-runner", "Haiku", "τρέχει όλο το suite", ["μόνο failures"], "tests · logs"),
            ("audit", "Sonnet", "διαβάζει το diff", ["ευρήματα +", "αποδείξεις"], "πριν το «τέλος»"),
            ("general-purpose", "Sonnet", "κάθε δουλειά · Plan", ["περίληψη"], "υπόλοιπα"),
            ("escalate", "Fable", "αναπαράγει το σφάλμα", ["διάγνωση +", "επόμενο βήμα"], ["advisor + 2 προσπάθειες", "απέτυχαν"])],
        caption="κάθε subagent έχει δικό του context: το μεγάλο output μένει μέσα, επιστρέφει μόνο το αποτέλεσμα", rank="βαθμίδα μοντέλου",
        legend="διακεκομμένο = μόνο αν απέτυχαν ο advisor και δύο δικές του προσπάθειες",
        wt="Πώς μοιράζεται η δουλειά", wd="Το κύριο session αναθέτει σε subagents με δικό τους context, ρωτά τον advisor στα σημεία απόφασης και καλεί τον escalate μόνο αν απέτυχαν ο advisor και δύο προσπάθειες.",
        setup=dict(cmd="/repo-mode:setup", wizard="wizard · μόνο ερωτήσεις και ανάγνωση",
                   steps=[("Έλεγχος repo", ["έκδοση", "ρυθμίσεις"]), ("Γύρος 1", ["model · advisor", "agents · scope"]),
                          ("Γύρος 2", ["model κάθε agent", "+ υπόλοιποι"]), ("Γύρος 3–4", ["effort · workflows", "κανόνες · deny", "secrets · escalate", "φίλτρο · LSP"]),
                          ("Σχέδιο", ["before / after", "κάθε αρχείου"])],
                   approve="Έγκριση;", yes="ναι", no="όχι", nothing="Δεν γράφεται τίποτα", writes="Γράφει",
                   writes_l=["settings.local.json · agents/*.md", "CLAUDE.local.md · hooks/ · .git/info/exclude", "repo-mode.json (κατάσταση, για το /off)"],
                   back="ή άλλαξε απαντήσεις → πίσω στον Γύρο 1",
                   title="Πώς δημιουργείται το setup", desc="Ο wizard μόνο ρωτά και διαβάζει, δείχνει σχέδιο before/after και γράφει αρχεία μόνο μετά την έγκρισή σου.")),
}


def work_split(lang):
    s = STR[lang]; W, H = 1000, 520; b = []
    b.append(f'<rect x="440" y="24" width="120" height="30" fill="{INK}" stroke="{LINE}" stroke-width="1.4"/>' + t(500, 44, s["you"], 13, TX, 700, "middle"))
    b.append(arrow("M500 54 V84"))
    b.append(box(340, 84, 320, 106, s["main"], "Sonnet 5.5", s["main_l"], title_size=16))
    b.append(box(770, 84, 200, 106, s["adv"], "Opus 5.5", s["adv_l"], title_size=16))
    b.append(arrow("M660 118 H770")); b.append(t(715, 110, s["ask"], 10.5, MU, 400, "middle"))
    b.append(arrow("M770 156 H660", dashed=True)); b.append(t(715, 172, s["advice"], 10.5, MU, 400, "middle"))
    cw, gap, x0 = 172, 15, 40
    cx = [x0 + i * (cw + gap) + cw / 2 for i in range(5)]
    dn = [c + 22 for c in cx]   # delegate arrows go down on the right of each column
    up = [c - 22 for c in cx]   # results come back up on the left
    b.append(f'<path d="M500 190 V222 M{dn[0]} 222 H{dn[4]}" stroke="{LINE}" stroke-width="1.4" fill="none"/>')
    b.append(f'<rect x="20" y="268" width="960" height="242" fill="none" stroke="{LINE}" stroke-width="1" stroke-dasharray="3 5"/>')
    for i, (name, model, inside, result, trig) in enumerate(s["cards"]):
        x = x0 + i * (cw + gap); esc = (i == 4)
        fam = model.split()[0]; mc = MODEL[fam][0]
        col = MODEL["Fable"][0] if esc else LINE
        b.append(f'<path d="M{dn[i]} 222 V318" fill="none" stroke="{col}" stroke-width="1.4"{DASH if esc else ""} marker-end="url(#{"m-Fable" if esc else "a"})"/>')
        b.append(pill(dn[i], 262, trig, col, col if esc else TX))
        # result coming back up, in the model's color, label to the left of the arrow
        b.append(f'<path d="M{up[i]} 318 V286" fill="none" stroke="{mc}" stroke-width="1.6" marker-end="url(#m-{fam})"/>')
        for k, line in enumerate(result):
            b.append(t(up[i] - 8, 296 + k * 14 - (len(result) - 1) * 7, line, 11, mc, 700, "end"))
        # card: name, model, what stays inside
        b.append(box(x, 318, cw, 104, name, model, [], col=col))
        b.append(t(x + 14, 318 + 78, s["inside"], 10.5, MU) + t(x + 14, 318 + 94, inside, 11.5, TX))
    b.append(t(34, 448, s["caption"], 11, MU))
    b.append(t(34, 474, s["rank"], 11, MU))
    lx = 34 + len(s["rank"]) * 6.7 + 14
    for nm in ("Haiku", "Sonnet", "Opus", "Fable"):
        c, r_ = MODEL[nm]
        b.append(dots(lx + 5, 471, r_, c) + t(lx + 60, 474, nm, 11, c, 700))
        lx += 60 + len(nm) * 7 + 18
    b.append(t(34, 498, s["legend"], 11, MODEL["Fable"][0]))
    return svg(W, H, s["wt"], s["wd"], "\n".join(b))


def setup_flow(lang):
    s = STR[lang]["setup"]; W, H = 1000, 460; b = []
    b.append(f'<rect x="395" y="20" width="210" height="36" fill="{INK}" stroke="{LINE}" stroke-width="1.4"/>' + t(500, 43, s["cmd"], 14, TX, 700, "middle"))
    b.append(arrow("M500 56 V84"))
    b.append(f'<rect x="20" y="84" width="960" height="184" fill="none" stroke="{LINE}" stroke-width="1" stroke-dasharray="3 5"/>')
    b.append(t(34, 106, s["wizard"], 11, MU))
    cw, gap, x0, y0 = 168, 20, 40, 122
    for i, (name, lines) in enumerate(s["steps"]):
        x = x0 + i * (cw + gap)
        b.append(box(x, y0, cw, 130, name, None, lines, col=GREEN if i == 4 else LINE))
        if i < 4:
            b.append(arrow(f"M{x + cw + 2} {y0 + 65} H{x + cw + gap - 2}"))
    b.append(arrow("M500 268 V300"))
    dcx, dcy, dw, dh = 500, 346, 82, 46
    b.append(f'<path d="M{dcx} {dcy-dh} L{dcx+dw} {dcy} L{dcx} {dcy+dh} L{dcx-dw} {dcy} z" fill="{INK}" stroke="{AMBER}" stroke-width="1.4"/>')
    b.append(t(dcx, dcy + 5, s["approve"], 13, TX, 700, "middle"))
    b.append(arrow(f"M{dcx+dw+2} {dcy} H640")); b.append(t(dcx + dw + 28, dcy - 8, s["yes"], 10.5, GREEN, 700, "middle"))
    b.append(box(640, 290, 340, 112, s["writes"], None, s["writes_l"], col=GREEN))
    b.append(arrow(f"M{dcx-dw-2} {dcy} H360")); b.append(t(dcx - dw - 28, dcy - 8, s["no"], 10.5, MU, 700, "middle"))
    b.append(f'<rect x="20" y="328" width="340" height="36" fill="{INK}" stroke="{MU}" stroke-width="1.2" stroke-dasharray="3 3"/>' + t(190, 351, s["nothing"], 13, MU, 700, "middle"))
    b.append(t(500, 428, s["back"], 11, MU, 400, "middle"))
    return svg(W, H, s["title"], s["desc"], "\n".join(b))


if __name__ == "__main__":
    for lang in ("en", "el"):
        open(os.path.join(OUT, f"work-split.{lang}.svg"), "w", encoding="utf-8").write(work_split(lang))
        open(os.path.join(OUT, f"setup-flow.{lang}.svg"), "w", encoding="utf-8").write(setup_flow(lang))
    print("ok")
