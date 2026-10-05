"""Build presentation/Jev_Team_Overview.pptx (4 slides, 16:9, dark theme).

Run from the repo root:  .venv\\Scripts\\python.exe presentation\\build_presentation.py
Images: YouTube thumbnails (credited + linked), a terminal screenshot rendered from a real
run of samples/06_agent_harness.py and MP4 clips recorded from samples/07_ui_demos.py;
everything else is native, editable PowerPoint shapes. Speaker notes live in speaker_notes.py.
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

from speaker_notes import NOTES

HERE = Path(__file__).parent
ASSETS = HERE / "assets"
OUT = HERE / "Jev_Team_Overview.pptx"

VIDEO_1 = "https://www.youtube.com/watch?v=vj7hysh0mOI"
VIDEO_2 = "https://www.youtube.com/watch?v=I34qxJjyms0"
VIDEO_3 = "https://www.youtube.com/watch?v=VE5dsWll06M"
REPO = "https://github.com/stvonolf/jev-samples"
LAYA = "https://huggingface.co/convaiinnovations/laya"
FOUNDRY_ARTICLE = ("https://techcommunity.microsoft.com/blog/azuredevcommunityblog/"
                   "using-jev-with-agents-in-microsoft-foundry-for-model-evaluation/4559851")
TYPESAFE_DOCS = "https://docs.typesafe.ai"
SLIDES = 6

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


def link(slide, x, y, w, label, url, size=12, color=SCORE, prefix=None):
    parts = ([(prefix, {"color": MUTED})] if prefix else []) + [(label, {"color": color, "bold": True})]
    shp = text(slide, x, y, w, 0.32, [parts], size=size)
    shp.click_action.hyperlink.address = url
    shp.text_frame.paragraphs[0].runs[-1].font.underline = True
    return shp


def crop_banner(src, dst, top_px):
    """Drop the clickbait title banner from a thumbnail, keep the demo collage."""
    with Image.open(src) as im:
        im.crop((0, top_px, im.width, im.height)).save(dst, quality=92)
    return dst


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
def card(slide, x, y, w, h, color, title, items, url, url_label, size=14):
    box(slide, x, y, w, h, fill=PANEL)
    box(slide, x, y, w, 0.07, fill=color, shape=MSO_SHAPE.RECTANGLE)
    text(slide, x + 0.2, y + 0.18, w - 0.35, 0.45, [title], size=17, bold=True, color=color)
    text(slide, x + 0.2, y + 0.75, w - 0.35, h - 1.2,
         [[("•  ", {"color": color}), (item, {})] for item in items], size=size, color=TEXT, space_after=6)
    link(slide, x + 0.2, y + h - 0.45, w - 0.35, url_label, url, size=11, color=color)


def flow(slide, x, y, step_w, h, steps, gap=0.12):
    """Chevron flow: steps = [(title, subtitle, fill)]."""
    for i, (title, sub, color) in enumerate(steps):
        shape = MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON
        chev = box(slide, x + i * (step_w - 0.12 + gap), y, step_w, h, fill=color, shape=shape)
        dark = color in (CHOICE, SCORE, NOUL, GREEN)
        lines = [[(title, {"bold": True, "size": 13})]] + ([[(sub, {"size": 10})]] if sub else [])
        text(slide, 0, 0, 0, 0, lines, color=BG if dark else TEXT, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE, shape=chev)


def slide_1(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(s)
    text(s, 0.5, 0.32, 7, 0.3, [f"JEV · TEAM BRIEFING  ·  1 / {SLIDES}"], size=11, color=SCORE, bold=True)
    text(s, 0.5, 0.62, 7.0, 1.3, [[("Jev: AI that ", {}), ("decides", {"color": CHOICE}),
                                  (",\nnot chats", {})]], size=40, bold=True, spacing=0.95)
    text(s, 0.5, 2.15, 6.8, 0.5, ["TypeSafe AI's first “System One” model"], size=17, color=MUTED)
    bullets(s, 0.5, 3.0, 6.7, 2.9, [
        ("Text in → ", "typed decisions + probabilities out"),
        ("One parallel pass: ", "~0.1 s, ~200× faster and ~400× cheaper than an LLM*"),
        ("Fast “System 1” ", "next to the LLM's slow “System 2” - not a replacement"),
    ], size=19, gap=18)
    text(s, 0.5, 5.75, 6.8, 0.3, ["* TypeSafe's own benchmark on System One workflows"], size=10, color=MUTED)

    picture(s, ASSETS / "yt_vj7hysh0mOI.jpg", 7.55, 0.55, 5.3, link=VIDEO_1)
    caption(s, 7.55, 3.58, 5.3, [("▶  “Jev explained in 7min..” – Caleb Writes Code", {})], link=VIDEO_1)
    for i, (label, value, sub, color) in enumerate([("LLM", "≈ 5 s", "text, then parse", RED),
                                                    ("Jev", "≈ 0.1 s", "noul = 0.98", GREEN)]):
        x = 7.55 + i * 2.72
        box(s, x, 4.15, 2.58, 1.75, fill=PANEL, line=color)
        text(s, x + 0.18, 4.25, 2.3, 0.3, [label], size=13, bold=True, color=color)
        text(s, x + 0.18, 4.6, 2.3, 0.7, [value], size=32, bold=True)
        text(s, x + 0.18, 5.35, 2.3, 0.45, [sub], size=11, color=MUTED)
    caption(s, 7.55, 6.0, 5.3, [("“Is there PII in this text?” – LangChain demo", {})], link=VIDEO_3)
    link(s, 0.5, 6.9, 7.3, "github.com/stvonolf/jev-samples", REPO, size=12, prefix="Slides, samples & UI demos:  ")
    notes(s, NOTES["what"])


def slide_2(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(s)
    header(s, f"HOW IT WORKS  ·  2 / {SLIDES}", "Three primitives, one parallel call",
           "Your code owns the flow - Jev answers narrow, typed questions.")
    cards = [("Choice", CHOICE, "Which team should handle this ticket?", "billing  (p 0.84)"),
             ("Score", SCORE, "How frustrated is the customer?", "1.04 → frustrated"),
             ("Noul", NOUL, "Does the message convey urgency?", "0.999 → yes")]
    for i, (name, color, q, a) in enumerate(cards):
        x = 0.5 + i * 4.17
        box(s, x, 1.85, 4.0, 1.95, fill=PANEL)
        box(s, x, 1.85, 4.0, 0.07, fill=color, shape=MSO_SHAPE.RECTANGLE)
        text(s, x + 0.22, 2.02, 3.6, 0.5, [name], size=26, bold=True, color=color)
        text(s, x + 0.22, 2.68, 3.6, 0.5, [q], size=14.5)
        text(s, x + 0.22, 3.2, 3.6, 0.45, [a], size=15, color=color, font=MONO)

    flow(s, 0.5, 4.3, 1.92, 0.9, [("State", "text or JSON", PANEL_2), ("Questions", "Choice · Score · Noul", PANEL_2),
                                  ("Answers", "+ confidence", SCORE), ("Your code", "act · review · escalate", PANEL_2)])
    bullets(s, 0.5, 5.5, 7.2, 1.4, [
        ("All questions answered together ", "in ~0.1 s"),
        ("Text only; ", "calibrated over many decisions, not each one"),
    ], size=15, gap=8)

    picture(s, ASSETS / "yt_VE5dsWll06M.jpg", 8.3, 3.95, 4.55, link=VIDEO_3)
    caption(s, 8.3, 6.56, 4.55, [("▶  LangChain: Jev in the agent harness - routing · auto mode · judge", {})],
            link=VIDEO_3)
    notes(s, NOTES["how"])


def slide_3(prs, demos_png):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(s)
    header(s, f"FOR MARKETING SOFTWARE  ·  3 / {SLIDES}", "Thousands of tiny marketing decisions")
    items = [("Lead scoring & routing", "Score + Choice"), ("Reply & intent triage", "Choice + Noul"),
             ("Ad, SEO & content tagging at scale", "Choice · Noul"),
             ("Social listening & AI guardrails", "Noul + Score")]
    lines = [[("▸  ", {"color": SCORE, "bold": True}), (use, {"bold": True}),
              (f"    {prim}", {"color": primitive_color(prim), "bold": True, "size": 14})] for use, prim in items]
    text(s, 0.5, 1.65, 7.1, 3.4, lines, size=19, space_after=18)

    with Image.open(demos_png) as im:
        img_h = 5.0 * im.height / im.width
    picture(s, demos_png, 7.85, 1.5, 5.0, link=VIDEO_2)
    caption(s, 7.85, 1.5 + img_h + 0.05, 5.0, [("▶  “Jev Is WAY More Powerful Than We Thought” – Pursuing AI", {})],
            link=VIDEO_2)
    text(s, 7.85, 1.5 + img_h + 0.5, 5.0, 0.5, [[("586 pages · 45 s · $0.21", {"bold": True})]], size=22)
    text(s, 7.85, 1.5 + img_h + 1.0, 5.0, 0.4, ["SEO internal links placed by Jev (Claude Opus 5: 21 pages, $1.43)"],
         size=11, color=MUTED)

    flow(s, 0.5, 5.45, 3.08, 0.85, [("Collect", "rows via code", PANEL_2), ("Ask Jev", "Choice · Score · Noul", CHOICE),
                                   ("Threshold", "auto · review · drop", SCORE), ("LLM writes", "only what passed", PANEL_2)])
    text(s, 0.5, 6.6, 12.3, 0.4, [[("Limits: ", {"bold": True, "color": RED}),
                                   ("no explanations · closed answer sets · triage-grade accuracy → keep a human "
                                    "for the middle band", {})]], size=12.5, color=MUTED)
    notes(s, NOTES["marketing"])


def slide_access(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(s)
    header(s, f"GETTING ACCESS  ·  4 / {SLIDES}", "Jev isn't public yet - not even in Microsoft Foundry",
           "Early access since 15 Sep 2026, sign-up required. Three ways in:")
    cards = [
        (NOUL, "①  TypeSafe API", ["Sign up for early access", "$0.042 per 1M input tokens"],
         TYPESAFE_DOCS, "docs.typesafe.ai"),
        (SCORE, "②  Microsoft Foundry", ["Not in the model catalog", "Call it via an agent OpenAPI tool"],
         FOUNDRY_ARTICLE, "Microsoft Tech Community article"),
        (GREEN, "③  Open-source Laya", ["No sign-up, runs on a laptop", "Powers all our demos"],
         LAYA, "huggingface.co/convaiinnovations/laya"),
    ]
    for i, (color, title, items, url, label) in enumerate(cards):
        card(s, 0.5 + i * 4.19, 1.85, 3.95, 2.45, color, title, items, url, label)

    box(s, 0.5, 4.6, 12.33, 1.95, fill=PANEL, line=GREEN)
    link(s, 0.72, 4.72, 11.9, "github.com/stvonolf/jev-samples", REPO, size=15, color=GREEN, prefix="Try it:  ")
    text(s, 0.72, 5.25, 11.9, 1.6, [
        "git clone https://github.com/stvonolf/jev-samples; cd jev-samples",
        r"python -m venv .venv; .venv\Scripts\pip install -r samples\requirements.txt",
        r"cd samples; ..\.venv\Scripts\python 07_ui_demos.py      # → http://localhost:8765",
    ], size=14, font=MONO, color=TEXT, spacing=1.25)
    notes(s, NOTES["access"])


def slide_4(prs, terminal_png, terminal_size):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(s)
    header(s, f"HANDS-ON  ·  5 / {SLIDES}", "We built it: 6 samples + 3 UI demos")
    link(s, 0.5, 1.25, 7.0, "github.com/stvonolf/jev-samples", REPO, size=14, prefix="Code:  ")
    bullets(s, 0.5, 1.9, 7.0, 2.4, [
        ("6 marketing samples: ", "leads, replies, SEO, social, commands, agents"),
        ("3 UI demos, ", "one per primitive (next slide)"),
        ("Local Laya or the Jev API: ", "one env variable"),
    ], size=16, gap=12)
    text(s, 0.5, 4.45, 7.0, 0.4, ["What we learned"], size=16, bold=True, color=GREEN)
    bullets(s, 0.5, 4.9, 7.0, 1.7, [
        ("Ask small, atomic questions", ""),
        ("Keep numbers and business rules in code", ""),
        ("Test wording on labelled examples, gate on confidence", ""),
    ], size=15, gap=8, marker_color=GREEN)

    w = 4.95
    h = w * terminal_size[1] / terminal_size[0]
    picture(s, terminal_png, 7.9, 1.9, w)
    caption(s, 7.9, 1.9 + h + 0.04, w, [("Real output of samples/06_agent_harness.py (excerpt)", {})])
    text(s, 0.5, 6.75, 12.3, 0.4, [[("Next: ", {"bold": True, "color": SCORE}),
                                    ("pick one pilot · label 300–500 real examples · compare Laya vs the Jev API", {})]],
         size=14, color=TEXT)
    notes(s, NOTES["handson"])


def slide_demos(prs, demos):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(s)
    header(s, f"LIVE DEMOS  ·  6 / {SLIDES}", "Live demos: one per primitive")
    link(s, 0.5, 1.22, 12.3, r"python samples\07_ui_demos.py  →  http://localhost:8765", REPO, size=13,
         color=SCORE, prefix="Run:  ")
    w = 3.95
    h = w * 800 / 1280
    for i, (clip, poster, title, prim, color, line) in enumerate(demos):
        x = 0.5 + i * (w + 0.24)
        if clip.exists():
            movie = s.shapes.add_movie(str(clip), Inches(x), Inches(1.8), Inches(w), Inches(h),
                                       poster_frame_image=str(poster), mime_type="video/mp4")
            movie.line.color.rgb = LINE
        else:
            picture(s, poster, x, 1.8, w)
        y = 1.8 + h + 0.2
        text(s, x, y, w, 0.4, [[(title, {"bold": True}), (f"   {prim}", {"color": color, "bold": True})]], size=15)
        text(s, x, y + 0.5, w, 1.4, [line], size=13, color=MUTED)
    text(s, 0.5, 6.85, 12.3, 0.3, ["Click a video to play it · recorded from samples/07_ui_demos.py on a laptop CPU"],
         size=10.5, color=MUTED)
    notes(s, NOTES["demos"])


def main():
    terminal_png = ASSETS / "terminal_06_agent_harness.png"
    size = render_terminal(terminal_png)
    demos_png = crop_banner(ASSETS / "yt_I34qxJjyms0.jpg", ASSETS / "yt_I34qxJjyms0_demos.jpg", top_px=144)
    demos = [
        (ASSETS / "demo_trolley.mp4", ASSETS / "demo_trolley.png", "Trolley ×100", "Choice", CHOICE,
         "100 / 100 pulls, like the video - but it also pulls when 5 are on the side track."),
        (ASSETS / "demo_creative.mp4", ASSETS / "demo_creative.png", "Emoji pile", "Noul", NOUL,
         "~235 yes/no decisions per prompt; matches fly up as they stream in."),
        (ASSETS / "demo_score.mp4", ASSETS / "demo_score.png", "Message heat", "Score", SCORE,
         "Gauges move between levels as the complaint escalates → retention."),
    ]

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    slide_1(prs)
    slide_2(prs)
    slide_3(prs, demos_png)
    slide_access(prs)
    slide_4(prs, terminal_png, size)
    slide_demos(prs, demos)
    prs.core_properties.title = "Jev - AI that decides, not chats"
    prs.core_properties.subject = "Team briefing: Jev, System One models and marketing software"
    prs.save(OUT)
    print(f"saved {OUT} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
