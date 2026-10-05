"""Build presentation/Jev_Team_Overview.pptx (4 slides, 16:9, dark theme).

Run from the repo root:  .venv\\Scripts\\python.exe presentation\\build_presentation.py
Images: YouTube thumbnails (credited + linked), a terminal screenshot rendered from a real
run of samples/06_agent_harness.py, everything else is native, editable PowerPoint shapes.
"""
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = Path(__file__).parent
ASSETS = HERE / "assets"
OUT = HERE / "Jev_Team_Overview.pptx"

VIDEO_1 = "https://www.youtube.com/watch?v=vj7hysh0mOI"
VIDEO_2 = "https://www.youtube.com/watch?v=I34qxJjyms0"
VIDEO_3 = "https://www.youtube.com/watch?v=VE5dsWll06M"

BG = RGBColor(0x0F, 0x11, 0x17)
PANEL = RGBColor(0x1A, 0x1D, 0x27)
PANEL_2 = RGBColor(0x24, 0x28, 0x36)
LINE = RGBColor(0x33, 0x38, 0x4A)
TEXT = RGBColor(0xF5, 0xF6, 0xFA)
MUTED = RGBColor(0xA3, 0xA9, 0xBC)
CHOICE = RGBColor(0xE0, 0x40, 0xFB)
SCORE = RGBColor(0x22, 0xD3, 0xEE)
NOUL = RGBColor(0xFB, 0xBF, 0x24)
GREEN = RGBColor(0x34, 0xD3, 0x99)
RED = RGBColor(0xF8, 0x71, 0x71)

FONT = "Segoe UI"
FONT_BOLD = "Segoe UI Semibold"
MONO = "Consolas"


# ------------------------------------------------------------------ helpers
def set_bg(slide):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = BG


def box(slide, x, y, w, h, fill=PANEL, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06):
    shp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        shp.adjustments[0] = radius
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1.25)
    shp.shadow.inherit = False
    shp.text_frame.text = ""
    return shp


def run(paragraph, text, size=14, color=TEXT, bold=False, font=None, italic=False):
    r = paragraph.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.font.bold = False
    r.font.italic = italic
    r.font.name = font or (FONT_BOLD if bold else FONT)
    return r


def text(slide, x, y, w, h, lines, size=14, color=TEXT, bold=False, font=None,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.0, space_after=0, shape=None):
    """lines: list of str or list of [(text, {overrides})] runs."""
    if shape is None:
        shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, Inches(0.04))
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        p.space_after = Pt(space_after)
        parts = [(line, {})] if isinstance(line, str) else line
        for t, o in parts:
            run(p, t, size=o.get("size", size), color=o.get("color", color),
                bold=o.get("bold", bold), font=o.get("font", font), italic=o.get("italic", False))
    return shape


def bullets(slide, x, y, w, h, items, size=14, gap=7, marker_color=SCORE):
    """items: list of (lead, rest) - lead is bold."""
    lines = []
    for lead, rest in items:
        lines.append([("▸  ", {"color": marker_color, "bold": True}),
                      (lead, {"bold": True}), (rest, {"color": MUTED})])
    return text(slide, x, y, w, h, lines, size=size, space_after=gap, spacing=1.05)


def header(slide, kicker, title, subtitle=None):
    text(slide, 0.5, 0.32, 9, 0.3, [kicker], size=11, color=SCORE, bold=True)
    text(slide, 0.5, 0.58, 12.3, 0.7, [title], size=30, bold=True)
    if subtitle:
        text(slide, 0.5, 1.22, 12.3, 0.4, [subtitle], size=14, color=MUTED)


def picture(slide, path, x, y, w, link=None):
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(w))
    pic.line.color.rgb = LINE
    pic.line.width = Pt(1)
    if link:
        pic.click_action.hyperlink.address = link
    return pic


def caption(slide, x, y, w, parts, link=None):
    shp = text(slide, x, y, w, 0.3, [parts], size=10, color=MUTED)
    if link:
        # Shape-level link keeps the text colour readable (run links use the theme's dark blue).
        shp.click_action.hyperlink.address = link
        shp.text_frame.paragraphs[0].runs[-1].font.underline = True
    return shp


NO_STYLE_NO_GRID = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"


def cell_borders(cell, color="33384A", width=9525):
    tc_pr = cell._tc.get_or_add_tcPr()
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        for old in tc_pr.findall(qn(tag)):
            tc_pr.remove(old)
    # Border elements must be the first children of tcPr, in L, R, T, B order.
    for i, tag in enumerate(("a:lnL", "a:lnR", "a:lnT", "a:lnB")):
        ln = etree.SubElement(tc_pr, qn(tag), w=str(width), cap="flat", cmpd="sng", algn="ctr")
        fill = etree.SubElement(ln, qn("a:solidFill"))
        etree.SubElement(fill, qn("a:srgbClr"), val=color)
        etree.SubElement(ln, qn("a:prstDash"), val="solid")
        tc_pr.remove(ln)
        tc_pr.insert(i, ln)


def table(slide, x, y, w, col_widths, rows, row_h=0.4, size=11, header_fill=PANEL_2,
          first_col_color=TEXT, col_colors=None):
    shape = slide.shapes.add_table(len(rows), len(col_widths), Inches(x), Inches(y),
                                   Inches(w), Inches(row_h * len(rows)))
    tbl = shape.table
    tbl.first_row = True
    tbl.horz_banding = False
    shape._element.xpath(".//a:tableStyleId")[0].text = NO_STYLE_NO_GRID
    for c, cw in enumerate(col_widths):
        tbl.columns[c].width = Inches(cw)
    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(row_h)
        for c, value in enumerate(row):
            cell = tbl.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = header_fill if r == 0 else (PANEL if r % 2 else BG)
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell_borders(cell)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            if r == 0:
                color, bold = MUTED, True
            elif col_colors and c in col_colors:
                color, bold = col_colors[c](value), True
            elif c == 0:
                color, bold = first_col_color, True
            else:
                color, bold = MUTED, False
            run(p, value, size=size - (1 if r == 0 else 0), color=color, bold=bold)
    return tbl


def primitive_color(value):
    for name, color in (("Choice", CHOICE), ("Score", SCORE), ("Noul", NOUL)):
        if value.startswith(name):
            return color
    return TEXT


def notes(slide, body):
    slide.notes_slide.notes_text_frame.text = body.strip()


# ------------------------------------------------------------------ terminal screenshot
TERMINAL_LINES = [  # excerpt of a real run of samples/06_agent_harness.py (laptop CPU)
    ("1) MODEL ROUTING - cheapest LLM that can do the job", "head"),
    ("   fast      (p=0.67)  Fix the typo in this subject line", ""),
    ("   powerful  (p=0.87)  Write a 3-month go-to-market plan", ""),
    ("   fast      (p=0.60)  Translate this CTA to German", ""),
    ("   -> cost 63 units vs 120 always-powerful (48% saved)", "ok"),
    ("", ""),
    ("2) AUTO MODE - classify every tool call before it runs", "head"),
    ("   ✅ ALLOW     read       read open/click statistics", ""),
    ("   ✅ ALLOW     draft_edit send test email to marketing-team@", ""),
    ("   ✋ ASK HUMAN mass_send  send draft_v3 to 1,200,000 contacts", "warn"),
    ("   ✋ ASK HUMAN delete     delete segment, 48,000 contacts", "warn"),
    ("   ⛔ BLOCK     export     export VIP list to a private gmail", "bad"),
    ("", ""),
    ("3) JEV-AS-A-JUDGE - check LLM-written emails", "head"),
    ("   draft A: PASS  (cta=0.92, hype=0.13)", "ok"),
    ("   draft B: FAIL  hype; unsupported: \"#1 CDP worldwide,", "bad"),
    ("            trusted by 10,000 brands\", \"300% ROI in 30 days\"", "bad"),
    ("   draft C: FAIL  no call to action", "bad"),
]


def render_terminal(path):
    scale = 2
    mono = ImageFont.truetype("consola.ttf", 15 * scale)
    mono_b = ImageFont.truetype("consolab.ttf", 15 * scale)
    emoji = ImageFont.truetype("seguiemj.ttf", 14 * scale)
    char_w = mono.getlength("M")
    line_h = int(21 * scale)
    pad = 18 * scale
    bar_h = 30 * scale
    cols = max(len(t) for t, _ in TERMINAL_LINES) + 2
    width = int(pad * 2 + char_w * cols)
    height = bar_h + pad + line_h * len(TERMINAL_LINES) + pad
    img = Image.new("RGB", (width, height), (13, 15, 20))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, bar_h], fill=(36, 40, 54))
    for i, color in enumerate([(248, 113, 113), (251, 191, 36), (52, 211, 153)]):
        cx = pad + i * 22 * scale
        draw.ellipse([cx, bar_h // 2 - 6 * scale, cx + 12 * scale, bar_h // 2 + 6 * scale], fill=color)
    draw.text((pad + 80 * scale, bar_h // 2), "python 06_agent_harness.py   (Laya, laptop CPU)",
              font=ImageFont.truetype("consola.ttf", 12 * scale), fill=(163, 169, 188), anchor="lm")
    colors = {"": (222, 226, 236), "head": (34, 211, 238), "ok": (52, 211, 153),
              "warn": (251, 191, 36), "bad": (248, 113, 113)}
    y = bar_h + pad
    for line, kind in TERMINAL_LINES:
        x = pad
        for ch in line:
            if ord(ch) > 0x2000 and ch not in "─→":
                draw.text((x, y + 2 * scale), ch, font=emoji, embedded_color=True)
                x += char_w * 2
            else:
                draw.text((x, y), ch, font=mono_b if kind == "head" else mono, fill=colors[kind])
                x += char_w
        y += line_h
    img.save(path)
    return img.size


# ------------------------------------------------------------------ slides
def slide_1(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(s)
    text(s, 0.5, 0.32, 7, 0.3, ["JEV · TEAM BRIEFING  ·  1 / 4"], size=11, color=SCORE, bold=True)
    text(s, 0.5, 0.62, 7.6, 1.3, [[("Jev: AI that ", {}), ("decides", {"color": CHOICE}),
                                  (",\nnot chats", {})]], size=36, bold=True, spacing=0.95)
    text(s, 0.5, 2.0, 7.4, 0.6, ["TypeSafe AI's first “System One” model: fast, typed, calibrated "
                                 "decisions that software can use directly."], size=14, color=MUTED)
    bullets(s, 0.5, 2.75, 7.35, 4.4, [
        ("What it is.  ", "Input = a state (text or JSON) + typed questions. Output = typed answers "
                          "with calibrated probabilities. It never generates text, so there is nothing "
                          "to parse and no broken schema."),
        ("Why it exists.  ", "LLMs were optimised for chat (RLHF) and coding agents (RLVR). Workflow "
                             "automation needs thousands of quick decisions under uncertainty: the "
                             "neglected use case."),
        ("How it is trained.  ", "RLCD = reinforcement learning for calibrated decisions. Rewards come "
                                 "from proper scoring rules, so honest probabilities score best."),
        ("Speed and cost.  ", "All questions in one parallel pass: 70–500 ms, 20–200× faster and "
                              "40–400× cheaper than LLMs on classification-style tasks. "
                              "$0.042 per 1M input tokens, output is free."),
        ("Not an LLM replacement.  ", "It cannot write, explain or plan. Jev is System 1 (fast "
                                      "intuition); LLMs stay System 2 (slow reasoning). Use both."),
    ], size=14, gap=11)

    picture(s, ASSETS / "yt_vj7hysh0mOI.jpg", 8.3, 0.45, 4.55, link=VIDEO_1)
    caption(s, 8.3, 3.04, 4.6, [("Video: ", {}), ("“Jev explained in 7min..” – Caleb Writes Code", {})],
            link=VIDEO_1)

    # Same question, two ways (LangChain demo: "Is there PII in this text?")
    box(s, 8.3, 3.5, 4.55, 3.55, fill=PANEL)
    text(s, 8.45, 3.6, 4.3, 0.35, [[("Same question, two models: ", {"bold": True}),
                                    ("“Is there PII in this text?”", {"color": MUTED})]], size=11.5)
    rows = [("LLM", RED, ["prompt", "token · token · token …", "text → parse"], "≈ 5 s"),
            ("Jev", GREEN, ["state + question", "1 parallel pass", "noul = 0.98"], "≈ 0.1 s")]
    for i, (label, color, steps, t) in enumerate(rows):
        y = 4.1 + i * 1.3
        text(s, 8.45, y, 1.0, 0.3, [label], size=13, bold=True, color=color)
        text(s, 11.85, y, 0.9, 0.3, [t], size=13, bold=True, color=color, align=PP_ALIGN.RIGHT)
        for j, step in enumerate(steps):
            bx = box(s, 8.45 + j * 1.45, y + 0.38, 1.3, 0.58, fill=PANEL_2, line=color if j == 2 else None)
            text(s, 0, 0, 0, 0, [step], size=10, color=TEXT, align=PP_ALIGN.CENTER,
                 anchor=MSO_ANCHOR.MIDDLE, shape=bx)
            if j < 2:
                text(s, 8.45 + j * 1.45 + 1.27, y + 0.47, 0.22, 0.4, ["›"], size=16, color=MUTED,
                     align=PP_ALIGN.CENTER)
    caption(s, 8.45, 6.68, 4.3, [("Demo from “Building a Harness with Jev” – LangChain", {})], link=VIDEO_3)

    notes(s, """
WHAT: Jev (TypeSafe AI, early access since Sept 2026) is the first "System One" model. You send a state and typed questions (choice / score / noul) to POST /v1/systemone and get typed answers with probabilities back. No text generation.

WHY (Caleb Writes Code, "Jev explained in 7min"): the AI stack's application layer pushed models toward chat (RLHF) and coding agents (RLVR). Workflow automation never crossed the cost/speed threshold, even with very capable models. TypeSafe argues that forcing chat/agent-optimised models into automation is the wrong approach and trains for calibrated decisions instead (RLCD). Most community demos show off speed (sorting email, RAG, games, model routing) rather than depth - LLMs can do these functionally, but not at 70-500 ms, because they generate tokens one after another.

HOW FAST/CHEAP: vendor-reported 40-200x faster; LangChain quotes 20-200x faster and 40-400x cheaper on classification-style tasks. Price $0.042 per 1M input tokens, output free (~$0.0004 per decision).

NAME: System 1 / System 2 from Kahneman, "Thinking, Fast and Slow".

LANGCHAIN DEMO: "Is there PII in this text?" - LLM writes an answer + structured output in ~5 s; Jev returns 0.98 almost instantly.

Takeaway from video 1: this is less about Jev's novelty and more about the use-case space growing horizontally - narrow, specialised models next to general LLMs.
""")


def slide_2(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(s)
    header(s, "HOW IT WORKS  ·  2 / 4", "Three primitives, one parallel call",
           "Like logic gates and registers: your code owns the control flow, Jev answers narrow typed questions.")

    cards = [
        ("Choice", CHOICE, "Pick one option from a set you define (up to 255).",
         "Which team should handle this ticket?", "choice: \"billing\"\np = .84 · confidence = .60"),
        ("Score", SCORE, "Rate on ordered levels you describe (2–10).",
         "How frustrated is the customer?\ncalm · frustrated · very angry", "score: 1.04\n(frustrated, not very angry)"),
        ("Noul", NOUL, "Yes/no question → probability of “yes”.",
         "Does the message convey urgency?", "noul: 0.999"),
    ]
    for i, (name, color, desc, q, a) in enumerate(cards):
        x = 0.5 + i * 4.17
        box(s, x, 1.8, 4.0, 2.3, fill=PANEL)
        box(s, x, 1.8, 4.0, 0.07, fill=color, shape=MSO_SHAPE.RECTANGLE)
        text(s, x + 0.2, 1.95, 3.6, 0.45, [name], size=22, bold=True, color=color)
        text(s, x + 0.2, 2.45, 3.6, 0.4, [desc], size=11.5, color=MUTED)
        text(s, x + 0.2, 2.85, 3.6, 0.6, [q], size=12.5, color=TEXT)
        text(s, x + 0.2, 3.42, 3.6, 0.6, [a], size=12, color=color, font=MONO)

    # request / response
    box(s, 0.5, 4.3, 6.15, 2.75, fill=PANEL)
    text(s, 0.68, 4.38, 5.9, 0.3, ["One request, three answers (support-ticket example from the docs)"],
         size=11, color=MUTED, bold=True)
    code = [
        [("POST", {"color": SCORE}), (" /v1/systemone", {})],
        [("{ ", {}), ("\"state\"", {"color": NOUL}),
         (": \"My Stripe connection has failed for 3 days.", {})],
        [("            I'm losing sales. Please help ASAP.\",", {})],
        [("  ", {}), ("\"questions\"", {"color": NOUL}), (": {", {})],
        [("    \"team\":   {", {}), ("\"type\": \"choice\"", {"color": CHOICE}),
         (", \"criteria\": {\"billing\": …}},", {})],
        [("    \"mood\":   {", {}), ("\"type\": \"score\"", {"color": SCORE}),
         (", \"criteria\": [\"calm\", …]},", {})],
        [("    \"urgent\": {", {}), ("\"type\": \"noul\"", {"color": NOUL}),
         (", \"instructions\": \"Urgent?\"} } }", {})],
        [("→ team = billing (.84) · mood = 1.04 · urgent = 0.999", {"color": GREEN})],
    ]
    text(s, 0.68, 4.75, 5.9, 2.3, code, size=11.5, font=MONO, color=TEXT, spacing=1.1)

    # harness use cases (LangChain video)
    box(s, 6.85, 4.3, 5.98, 2.75, fill=PANEL)
    text(s, 7.03, 4.38, 5.7, 0.3, [[("Where it fits: around the LLM in the agent loop", {"bold": True}),
                                    ("  (LangChain)", {"color": MUTED})]], size=11.5)
    bullets(s, 7.03, 4.78, 5.65, 2.2, [
        ("Model routing.  ", "Pick the cheapest LLM that can handle each request, almost instantly."),
        ("Auto mode.  ", "Classify every tool call (delete DB, mass send) and block risky ones "
                         "before they run - fast enough to keep it switched on."),
        ("Jev-as-a-judge.  ", "Score agent answers against a rubric (correct? grounded? cited?) "
                              "for online evals: cheaper, faster and more consistent than LLM-as-judge."),
    ], size=11.5, gap=6, marker_color=GREEN)
    caption(s, 7.03, 6.7, 5.7, [("Video: “Building a Harness with Jev” – LangChain  ·  "
                                 "pip install langchain-typesafe", {})], link=VIDEO_3)

    notes(s, """
PRIMITIVES (all three videos + docs.typesafe.ai/api):
- Choice: map of option -> rubric (or null). Returns choice, probabilities per option, confidence. Max 255 options.
- Score: ordered array of level descriptions (2-10). Returns a probability-weighted score that can land between levels (1.04 = frustrated, not very angry), plus legend/probabilities/confidence.
- Noul: yes/no; returns P(yes). Optional criteria for what true/false mean.
- Many questions about one state are answered in ONE parallel pass - adding questions barely changes latency (unlike LLMs, which reason sequentially).
- Instructions and criteria can be structured JSON; refer to state fields in backticks.

Caleb's framing: "It almost feels like we're back to logic gates and registers" - you build abstractions on top. On the Pareto frontier Jev competes with Flash/Nano-class models, but only on workflow-specific tasks.

DOCS PATTERNS: confidence-gated routing (the answer tells you WHAT, confidence tells you WHETHER to act), composite scoring (atomic scores, weights in code), speculative fan-out (ask everything in one call, code decides what is relevant), intent routing.

LANGCHAIN ("Building a Harness with Jev"): langchain-typesafe exposes TypeSafeClassifier plus experimental middleware: ModelRouterMiddleware (fast vs powerful model per request) and AutoModeMiddleware (tool-risk gating). Jev-as-a-judge for LangSmith online evals: rubric criteria scored by Jev - reported as cheaper, faster and more consistent than LLM judges. Sample 06 in our repo implements all three ideas.
""")


def slide_3(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(s)
    header(s, "FOR MARKETING SOFTWARE  ·  3 / 4", "Thousands of tiny marketing decisions, in milliseconds")

    rows = [
        ["Use case", "Question Jev answers", "Primitive"],
        ["Lead scoring & routing", "How well does the lead fit our ICP? How ready to buy? Who owns it?", "Score + Choice"],
        ["Campaign reply triage", "Meeting, not now, unsubscribe, out of office, wrong person?", "Choice + Noul"],
        ["Search terms & negatives", "Buyer, researcher, job seeker, competitor or junk?", "Choice"],
        ["Ad creative tagging", "Hook, format, offer, awareness stage? (724 ads in 40 s ≈ $0.09)", "Choice ×4"],
        ["SEO internal linking", "Is there an honest reason to link page A to page B?", "Noul"],
        ["Social listening", "Engagement bait? Sentiment? Complaint, question or churn?", "Noul + Score"],
        ["Content QA gate", "Does this draft meet each of the 20 checklist points?", "Noul ×20"],
        ["AI assistant harness", "Fast or powerful LLM? Is this tool call risky? Is the claim grounded?", "Choice + Noul"],
    ]
    table(s, 0.5, 1.4, 7.75, [2.05, 4.35, 1.35], rows, row_h=0.43, size=11.5,
          col_colors={2: primitive_color})

    picture(s, ASSETS / "yt_I34qxJjyms0.jpg", 8.5, 1.4, 4.33, link=VIDEO_2)
    caption(s, 8.5, 3.86, 4.35, [("Video: “Jev Is WAY More Powerful Than We Thought” – Pursuing AI", {})],
            link=VIDEO_2)
    text(s, 8.5, 4.2, 4.35, 1.1, [
        [("SEO: ", {"bold": True, "color": TEXT}), ("586 pages in 45 s, 584 links placed, 139 rejected, "
                                                    "$0.21 (Claude Opus 5: 21 pages, $1.43)", {})],
        [("Also: ", {"bold": True, "color": TEXT}), ("driving sim, trolley problem 100/100, "
                                                     "voice-controlled drawing app, live slop detector, "
                                                     "Laya playing Snake at ~60 decisions/s", {})],
    ], size=10.5, color=MUTED, space_after=3)

    # decide-then-act loop
    text(s, 0.5, 5.4, 8, 0.3, [[("The decide-then-act loop", {"bold": True}),
                                ("  ·  same architecture for every row above", {"color": MUTED})]], size=12)
    steps = [("Collect", "rows via API / code", PANEL_2), ("Shortlist", "rules or embeddings", PANEL_2),
             ("Ask Jev", "Choice · Score · Noul", CHOICE), ("Threshold", "auto · review · drop", SCORE),
             ("LLM writes", "only what passed", PANEL_2), ("Verify", "Jev checks the output", NOUL)]
    for i, (title, sub, color) in enumerate(steps):
        shape = MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON
        chev = box(s, 0.5 + i * 2.06, 5.78, 2.2, 0.82, fill=color, shape=shape)
        dark = color in (CHOICE, SCORE, NOUL)
        text(s, 0, 0, 0, 0, [[(title, {"bold": True, "size": 12.5})], [(sub, {"size": 9.5})]],
             color=BG if dark else TEXT, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape=chev)
    text(s, 0.5, 6.72, 12.4, 0.5, [[
        ("Limits: ", {"bold": True, "color": RED}),
        ("no rationale (a number, not a reason) · closed answer sets only · triage-grade accuracy "
         "(vendor benchmark ~68% vs ~73% for frontier LLMs) · early access, price may change. "
         "If the answer must be written, it belongs to an LLM.", {})]], size=11, color=MUTED)

    notes(s, """
MARKETING USE CASES (TypeSafe use-case map: lead generation, advertising, customer support, moderation; Ryze AI "Jev for Marketing: 8 use cases and the limits"):
- Lead scoring and routing: score each lead against the ICP and pick the owner - two questions, one call. Sales gets the top band, the rest goes to nurture. (A 700-lead demo on X did exactly this.)
- Search terms & negatives (paid search): buyer / researcher / job seeker / competitor / junk -> auto-negative, queue or drop by confidence.
- Ad creative tagging: Matthew Berman ran Jev on 724 live ads from 37 brands in 40 s (~9 cents) - hook, format, offer, CTA, awareness stage, landing-page mismatch.
- SEO internal links: the 586-page Distribb demo from video 2.
- AI citation / GEO checks: "Is our brand recommended in this AI answer?" (Noul).
- Review & survey themes: classify every response instead of sampling 200.
- Content QA gate: 20 Nouls per draft; only passing drafts reach an editor.
- Model routing: frontier vs small vs no model.
Cost at list price is cents per job -> jobs that ran monthly on a frontier LLM can run nightly.

DECIDE-THEN-ACT LOOP (Ryze): collect with code -> shortlist to 10-15 candidates -> one bounded question per row -> threshold (high confidence auto, middle band to approval queue, low dropped) -> LLM writes only where text is needed -> verify the LLM output with Jev before it ships.

VIDEO 2 (Pursuing AI): AI that watches, decides and acts. Driving simulator (real-time control), trolley problem 100 trials (99% pull, consistent), designer visual exploration (hundreds of tiny decisions what to show), voice + gesture control of a drawing app, live slop detector on X, SEO 586 pages, Laya (local, M3 Max) playing Snake at ~60 decisions/s with 10-18 ms latency and ~1 GB memory.

LIMITS: no explanation; bounded answers only; vendor-reported benchmarks measure agreement with frontier models (Jev 67.8% vs Claude Opus 5 73.1%, GPT-5.6 Sol 74.1% on TypeSafe's 4-workflow benchmark); "cannot hallucinate" means it cannot break the schema - it can still pick the wrong option. Label 500 rows of your own data before trusting a threshold. Waitlist access, price may move.
""")


def slide_4(prs, terminal_png, terminal_size):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(s)
    header(s, "HANDS-ON  ·  4 / 4", "We built it: 6 samples running locally on Laya",
           "Laya: open-source (Apache-2.0), Jev-compatible, 421M params, same /v1/systemone shape. "
           "Runs on a laptop CPU.")

    rows = [
        ["#", "Sample", "Primitives", "What happened on our laptop"],
        ["01", "Lead scoring", "Choice + Score + Noul", "VP with budget → 86/100, enterprise AE; student & agency dropped; possible competitor → human check"],
        ["02", "Reply triage (EN/DE/CZ)", "Choice + Noul", "10/10 correct labels; 7 automated, 1 review, 2 escalated; opt-outs always suppressed"],
        ["03", "SEO internal linking", "Noul + Choice", "36 page pairs → 18 links + anchor texts; party page gets none"],
        ["04", "Social feed monitor", "Noul + Score + Choice", "3/3 slop posts hidden; complaint → support, cancellation → retention"],
        ["05", "Command bar", "Choice", "“cut meta prospecting in half” → change_budget(…, 50%); vague → “did you mean…?”"],
        ["06", "Agent harness", "Choice + Noul", "48% LLM cost saved by routing; 6/6 tool calls gated; fake claims caught"],
    ]
    table(s, 0.5, 1.8, 7.7, [0.42, 1.85, 1.7, 3.73], rows, row_h=0.5, size=10.5,
          first_col_color=MUTED, col_colors={1: lambda v: TEXT, 2: lambda v: primitive_color(v)})

    w = 4.38
    h = w * terminal_size[1] / terminal_size[0]
    picture(s, terminal_png, 8.45, 1.8, w)
    caption(s, 8.45, 1.8 + h + 0.03, w, [("Real output of samples/06_agent_harness.py (excerpt)", {})])

    box(s, 0.5, 5.45, 7.7, 1.65, fill=PANEL)
    text(s, 0.68, 5.52, 7.4, 0.3, ["What we learned (zero-shot, no fine-tuning)"], size=12, bold=True, color=GREEN)
    bullets(s, 0.68, 5.85, 7.45, 1.25, [
        ("Atomic questions win: ", "one persona Choice beat four disqualifier Nouls."),
        ("Data and business rules stay in code; ", "the model only judges language."),
        ("Wording matters: ", "test 3–5 phrasings on a small labelled set before you trust a threshold."),
        ("Gate on confidence, fail safe: ", "uncertain → human or “did you mean…?”. "
                                           "CPU ≈ 0.3 s/question, GPU ≈ 33 ms."),
    ], size=10.5, gap=1.5, marker_color=GREEN)

    ny = max(1.8 + h + 0.4, 5.45)
    box(s, 8.45, ny, 4.38, 7.1 - ny, fill=PANEL, line=SCORE)
    text(s, 8.62, ny + 0.07, 4.1, 0.3, ["Next steps"], size=12, bold=True, color=SCORE)
    text(s, 8.62, ny + 0.4, 4.1, 7.1 - ny - 0.45, [
        "1. Pick one pilot: reply triage or lead scoring",
        "2. Label 300–500 real examples, set thresholds",
        "3. Compare Laya (fine-tuned) vs Jev API on it",
        "4. Ship behind a confidence gate + human review",
    ], size=10.5, color=TEXT, space_after=2)

    notes(s, """
REPO: samples/ - six runnable Python samples + jev_client.py (local Laya backend or any Jev-compatible HTTP endpoint via JEV_BASE_URL / JEV_API_KEY). Run: python -m venv .venv; .venv\\Scripts\\pip install -r samples\\requirements.txt; cd samples; ..\\.venv\\Scripts\\python 01_lead_scoring.py

LAYA (huggingface.co/convaiinnovations/laya): ModernBERT-large backbone (395M) + a decision head trained from scratch, 421M total; multilingual checkpoint on mmBERT-base for 100+ languages; trained with RLCD-style proper scoring rules. laya-serve exposes the same POST /v1/systemone request/response shape as TypeSafe Jev. Author-reported vs Jev (third-party numbers, different setups): 7.8x faster on a T4 GPU (32.8 ms vs 236-276 ms p50), better calibration after temperature fitting, but Jev is better with >20 options (Banking77: 0.87 vs 0.43). The base checkpoint scores 0.36 on the typed-decisions benchmark; the fine-tuned typed-decisions checkpoint 0.77 - fine-tuning matters.

OUR MEASUREMENTS (Intel Core Ultra 7 268V, CPU only): ~250-350 ms for one short question, ~1-2 s for 4-5 questions about one item, model load ~10 s from cache. Fine for batch/demo; use a GPU or the Jev API for real-time.

LESSONS: we tested 3-5 phrasings per question on small labelled sets. Examples: "Do both pages cover the same marketing topic?" (AUC 1.0) beat "Are the pages closely related?"; short option labels beat long descriptions for the command bar; plain-text tool-call descriptions + a "kind of action" Choice beat risk Nouls on JSON. Giving the model fewer CRM fields improved persona detection.

NEXT STEPS: one pilot use case, label data, measure Laya vs Jev, ship behind confidence gating with human review for the middle band.
""")


def main():
    terminal_png = ASSETS / "terminal_06_agent_harness.png"
    size = render_terminal(terminal_png)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    slide_1(prs)
    slide_2(prs)
    slide_3(prs)
    slide_4(prs, terminal_png, size)
    prs.core_properties.title = "Jev - AI that decides, not chats"
    prs.core_properties.subject = "Team briefing: Jev, System One models and marketing software"
    prs.save(OUT)
    print(f"saved {OUT} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
