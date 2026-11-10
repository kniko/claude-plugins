#!/usr/bin/env python3
"""Generates the README diagrams (docs/*.svg). Run: python3 docs/build_diagrams.py
Each SVG is a self-contained dark card, so it looks the same on light and dark GitHub themes."""
import os
from xml.sax.saxutils import escape

OUT = os.path.dirname(os.path.abspath(__file__))
FONT = "'Segoe UI', system-ui, -apple-system, 'Helvetica Neue', Arial, sans-serif"
BG, CARD, CARD2, LINE, TXT, MUTED = "#0d1117", "#161b22", "#1c2330", "#30363d", "#e6edf3", "#8b949e"
BLUE, PURPLE, GREEN, ORANGE, PINK, TEAL, GRAY = "#58a6ff", "#bc8cff", "#3fb950", "#e3a008", "#ff7eb6", "#39c5cf", "#6e7681"


def t(x, y, s, size=13, fill=TXT, weight=400, anchor="start", style=""):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}" {style}>{escape(s)}</text>')


def node(x, y, w, h, accent, title, sub=None, rets=(), title_size=15, fill=CARD):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{LINE}"/>',
           f'<rect x="{x}" y="{y}" width="5" height="{h}" rx="2.5" fill="{accent}"/>']
    cy = y + 30
    out.append(t(x + 18, cy, title, title_size, TXT, 600))
    if sub:
        cy += 23
        out.append(t(x + 18, cy, sub, 12.5, accent, 600))
    for r in rets:
        cy += 19
        out.append(t(x + 18, cy, r, 12, MUTED))
    return "\n".join(out)


def pill(cx, cy, lines, fill=CARD2, color=MUTED, size=11.5):
    lines = [lines] if isinstance(lines, str) else lines
    w = max(len(l) for l in lines) * size * 0.56 + 20
    h = 8 + len(lines) * (size + 4)
    out = [f'<rect x="{cx - w/2:.1f}" y="{cy - h/2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{h/2 if len(lines)==1 else 9:.1f}" fill="{fill}" stroke="{LINE}"/>']
    for i, l in enumerate(lines):
        ly = cy - h/2 + 4 + (i + 1) * (size + 4) - 3
        out.append(t(f"{cx:.1f}", f"{ly:.1f}", l, size, color, 500, "middle"))
    return "\n".join(out)


def svg(w, h, title, desc, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d" font-family="{FONT}">
<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 1 L9 5 L0 9 z" fill="{MUTED}"/></marker>
</defs>
<rect width="{w}" height="{h}" rx="14" fill="{BG}" stroke="{LINE}"/>
{body}
</svg>
'''


def line(d, dashed=False, arrow=True, both=False):
    a = ' marker-end="url(#a)"' if arrow else ""
    if both:
        a += ' marker-start="url(#a)"'
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    return f'<path d="{d}" fill="none" stroke="{MUTED}" stroke-width="1.6"{dash}{a}/>'


STR = {
    "en": dict(
        you="You", main="Main session", main_sub="Sonnet 5.5 · effort medium",
        main_ret="talks · edits code", adv="Advisor", adv_sub="Opus 5.5", adv_ret="→ plan / correction",
        decision="decision points", group="Subagents · own context, return only a summary",
        cards=[("Explore", "Haiku · low", ["→ path:line"], "10+ files", BLUE if False else GREEN),
               ("test-runner", "Haiku · low", ["→ failures only"], "tests · logs", GREEN),
               ("audit", "Sonnet · high", ["→ findings + evidence"], "before «done»", TEAL),
               ("general-purpose", "Sonnet · also Plan", ["→ summary"], "everything else", TEAL),
               ("escalate", "Fable · high", ["→ diagnosis +", "   next step"], ["advisor + 2 tries", "failed"], PINK)],
        wt="How the work is split",
        wd="The main session delegates to subagents with their own context; the advisor is consulted at decision points; escalate is called only when the advisor and two tries failed.",
        setup=dict(cmd="/repo-mode:setup", wizard="Wizard · questions and reads only",
                   steps=[("Check repo", ["version", "settings"]), ("Round 1", ["model · advisor", "agents · scope"]),
                          ("Round 2", ["model per agent", "+ the rest"]), ("Rounds 3–4", ["effort · workflows", "rules · deny", "secrets · escalate", "test filter · LSP"]),
                          ("Plan", ["before / after", "of every file"])],
                   approve="Approve?", yes="Yes", no="No", nothing="Nothing is written",
                   writes="Writes", writes_l=["settings.local.json · agents/*.md", "CLAUDE.local.md · hooks/ · .git/info/exclude", "repo-mode.json (state, for /off)"],
                   back="or change your answers → back to Round 1",
                   title="How the setup is created", desc="The wizard asks and reads only, shows a before/after plan, and writes files only after you approve."),
    ),
    "el": dict(
        you="Εσύ", main="Κύριο session", main_sub="Sonnet 5.5 · effort medium",
        main_ret="μιλάει · γράφει κώδικα", adv="Advisor", adv_sub="Opus 5.5", adv_ret="→ σχέδιο / διόρθωση",
        decision="σημεία απόφασης", group="Subagents · δικό τους context, επιστρέφουν μόνο περίληψη",
        cards=[("Explore", "Haiku · low", ["→ path:line"], "10+ αρχεία", GREEN),
               ("test-runner", "Haiku · low", ["→ μόνο failures"], "tests · logs", GREEN),
               ("audit", "Sonnet · high", ["→ ευρήματα +", "   αποδείξεις"], "πριν το «τέλος»", TEAL),
               ("general-purpose", "Sonnet · και Plan", ["→ περίληψη"], "υπόλοιπα", TEAL),
               ("escalate", "Fable · high", ["→ διάγνωση +", "   επόμενο βήμα"], ["advisor + 2 προσπάθειες", "απέτυχαν"], PINK)],
        wt="Πώς μοιράζεται η δουλειά",
        wd="Το κύριο session αναθέτει σε subagents με δικό τους context· ο advisor ρωτιέται στα σημεία απόφασης· ο escalate καλείται μόνο αν απέτυχαν ο advisor και δύο προσπάθειες.",
        setup=dict(cmd="/repo-mode:setup", wizard="Wizard · μόνο ερωτήσεις και ανάγνωση",
                   steps=[("Έλεγχος repo", ["έκδοση", "ρυθμίσεις"]), ("Γύρος 1", ["model · advisor", "agents · scope"]),
                          ("Γύρος 2", ["model κάθε agent", "+ υπόλοιποι"]), ("Γύρος 3–4", ["effort · workflows", "κανόνες · deny", "secrets · escalate", "φίλτρο · LSP"]),
                          ("Σχέδιο", ["before / after", "κάθε αρχείου"])],
                   approve="Έγκριση;", yes="Ναι", no="Όχι", nothing="Δεν γράφεται τίποτα",
                   writes="Γράφει", writes_l=["settings.local.json · agents/*.md", "CLAUDE.local.md · hooks/ · .git/info/exclude", "repo-mode.json (κατάσταση, για το /off)"],
                   back="ή άλλαξε απαντήσεις → πίσω στον Γύρο 1",
                   title="Πώς δημιουργείται το setup", desc="Ο wizard μόνο ρωτά και διαβάζει, δείχνει σχέδιο before/after και γράφει αρχεία μόνο μετά την έγκρισή σου."),
    ),
}


def work_split(lang):
    s = STR[lang]
    W, H = 1000, 500
    b = []
    b.append(f'<rect x="440" y="22" width="120" height="34" rx="17" fill="{CARD2}" stroke="{LINE}"/>' + t(500, 44, s["you"], 14, TXT, 600, "middle"))
    b.append(line("M500 56 V84"))
    b.append(node(350, 84, 300, 92, BLUE, s["main"], s["main_sub"], [s["main_ret"]], 16))
    b.append(node(770, 84, 200, 92, PURPLE, s["adv"], s["adv_sub"], [s["adv_ret"]], 16))
    b.append(line("M650 130 H770", dashed=True, both=True))
    b.append(pill(710, 114, s["decision"]))
    # bus + drops
    cw, gap, x0, cy0 = 172, 15, 40, 300
    centers = [x0 + i * (cw + gap) + cw / 2 for i in range(5)]
    b.append(line("M500 176 V212", arrow=False))
    b.append(line(f"M{centers[0]} 212 H{centers[-1]}", arrow=False))
    # group box (drawn before cards, after lines so lines stay visible on top of it)
    b.insert(0, "")
    group = (f'<rect x="20" y="276" width="960" height="204" rx="14" fill="{CARD}" fill-opacity="0.55" stroke="{LINE}" stroke-dasharray="6 5"/>'
             + t(500, 466, s["group"], 12, MUTED, 500, "middle"))
    b.append(group)
    for i, (name, model, rets, trig, color) in enumerate(s["cards"]):
        cx = centers[i]
        dashed = (i == 4)
        b.append(line(f"M{cx} 212 V{cy0}", dashed=dashed))
        b.append(pill(cx, 248, trig, fill=BG))
        b.append(node(x0 + i * (cw + gap), cy0, cw, 104, color, name, model, rets, 15))
    return svg(W, H, s["wt"], s["wd"], "\n".join(b))


def setup_flow(lang):
    s = STR[lang]["setup"]
    W, H = 1000, 440
    b = []
    b.append(f'<rect x="395" y="20" width="210" height="36" rx="18" fill="{CARD2}" stroke="{BLUE}"/>' + t(500, 43, s["cmd"], 14, TXT, 600, "middle", 'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"'))
    b.append(line("M500 56 V84"))
    b.append(f'<rect x="20" y="84" width="960" height="176" rx="14" fill="{CARD}" fill-opacity="0.55" stroke="{LINE}" stroke-dasharray="6 5"/>')
    b.append(t(40, 108, s["wizard"], 12, MUTED, 500))
    cw, gap, x0, y0 = 168, 20, 40, 122
    accents = [GRAY, BLUE, BLUE, BLUE, GREEN]
    for i, (name, rets) in enumerate(s["steps"]):
        x = x0 + i * (cw + gap)
        b.append(node(x, y0, cw, 120, accents[i], name, None, rets, 15))
        if i < 4:
            b.append(line(f"M{x + cw + 2} {y0 + 60} H{x + cw + gap - 2}"))
    b.append(line("M500 260 V290"))
    # diamond
    dcx, dcy, dw, dh = 500, 336, 80, 46
    b.append(f'<path d="M{dcx} {dcy-dh} L{dcx+dw} {dcy} L{dcx} {dcy+dh} L{dcx-dw} {dcy} z" fill="{CARD2}" stroke="{ORANGE}" stroke-width="1.5"/>')
    b.append(t(dcx, dcy + 5, s["approve"], 14, TXT, 600, "middle"))
    # yes -> writes
    b.append(line(f"M{dcx+dw+2} {dcy} H640"))
    b.append(pill(dcx + dw + 28, dcy - 14, s["yes"], fill=BG, color=GREEN))
    b.append(node(640, 282, 340, 116, GREEN, s["writes"], None, s["writes_l"], 15))
    # no -> nothing
    b.append(line(f"M{dcx-dw-2} {dcy} H360"))
    b.append(pill(dcx - dw - 28, dcy - 14, s["no"], fill=BG, color=ORANGE))
    b.append(f'<rect x="20" y="318" width="340" height="36" rx="18" fill="{CARD2}" stroke="{LINE}"/>' + t(190, 341, s["nothing"], 13.5, MUTED, 600, "middle"))
    b.append(t(500, 410, s["back"], 12, MUTED, 400, "middle", 'font-style="italic"'))
    return svg(W, H, s["title"], s["desc"], "\n".join(b))


if __name__ == "__main__":
    for lang in ("en", "el"):
        open(os.path.join(OUT, f"work-split.{lang}.svg"), "w", encoding="utf-8").write(work_split(lang))
        open(os.path.join(OUT, f"setup-flow.{lang}.svg"), "w", encoding="utf-8").write(setup_flow(lang))
    print("ok")
