#!/usr/bin/env python3
"""Build Firmware/docs/Attendance_Logger_Easy_Guide.pdf: a short, picture-led guide for
lecturers, few words, many drawings. The device drawing uses the hole positions in
Enclosure/enclosure.py; the lights and buzzes follow App/Src/feedback.c. The app
pictures are guide_img/app_*.png, taken by app_screenshots.py from the demo data.

    python3 make_easy_guide.py            (needs google-chrome or chromium)
"""
import base64
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "Attendance_Logger_Easy_Guide.pdf"
IMG = HERE / "guide_img"

GREEN = "#1fa855"
RED = "#d93434"
INK = "#1d1d1b"
MUTED = "#5b5a55"
CASE = "#e9e6df"
CASE_EDGE = "#a9a59b"
ACCENT = "#2a5bd7"
SKIN = "#f0c8a4"
SKIN_EDGE = "#c4946c"

# ---------------------------------------------------------------- small icons

def buzz(n=1, long=False):
    """n buzz marks (little zig-zags)."""
    w = 30 if long else 18
    parts, x = [], 2
    for _ in range(n):
        pts = " ".join(f"{x + i * w / 6:.1f},{9 + (4 if i % 2 else -4)}" for i in range(7))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{INK}" stroke-width="2.2" '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
        x += w + 7
    return f'<svg width="{x}" height="18" viewBox="0 0 {x} 18">{"".join(parts)}</svg>'


def dot(colour, r=7):
    return (f'<svg width="{2*r+2}" height="{2*r+2}" viewBox="0 0 {2*r+2} {2*r+2}">'
            f'<circle cx="{r+1}" cy="{r+1}" r="{r}" fill="{colour}"/></svg>')

# ---------------------------------------------------------------- device drawings
# Board coordinates in mm from Enclosure/enclosure.py (x right, y up from the USB edge).
BOARD_W, BOARD_H, WALL = 60.0, 88.6, 3.0
S = 3.1  # px per mm
CW, CH = (BOARD_W + 2 * WALL) * S, (BOARD_H + 2 * WALL) * S
TAP = (29.5, 68.5, 40.0, 30.0)      # tap area centre and size
LED_G, LED_R = (12.5, 15.74), (15.0, 15.74)
BTN = (4.5, 6.0)
CHG = [(39.0, 2.5), (41.5, 2.5), (44.0, 2.5)]
USB_X = 30.04


def X(x):
    return (x + WALL) * S


def Y(y):
    return (BOARD_H - y + WALL) * S


def power_symbol(cx, cy, r, colour=INK):
    return (f'<path d="M {cx - r*0.62:.1f} {cy - r*0.55:.1f} A {r*0.82:.1f} {r*0.82:.1f} 0 1 0 '
            f'{cx + r*0.62:.1f} {cy - r*0.55:.1f}" fill="none" stroke="{colour}" stroke-width="2" '
            f'stroke-linecap="round"/>'
            f'<line x1="{cx}" y1="{cy - r*0.95:.1f}" x2="{cx}" y2="{cy - r*0.15:.1f}" stroke="{colour}" '
            f'stroke-width="2" stroke-linecap="round"/>')


def glow(cx, cy, colour, r=7):
    return (f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r*3.2:.0f}" fill="{colour}" opacity=".18"/>'
            f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r*2:.0f}" fill="{colour}" opacity=".3"/>'
            f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r}" fill="{colour}"/>')


def case_body(lit=None, charge=None, dim=False, waves=True):
    """The case, seen from the top. lit: 'green' / 'red' / None; charge: 'red' / 'green' / None."""
    g = [f'<rect x="0" y="0" width="{CW:.0f}" height="{CH:.0f}" rx="22" fill="{CASE}" '
         f'stroke="{CASE_EDGE}" stroke-width="2"/>']
    ax, ay, aw, ah = TAP
    g.append(f'<rect x="{X(ax - aw/2):.0f}" y="{Y(ay + ah/2):.0f}" width="{aw*S:.0f}" height="{ah*S:.0f}" '
             f'rx="12" fill="#f6f4ef" stroke="{ACCENT}" stroke-width="2.5" stroke-dasharray="7 5"/>')
    if waves:
        cx, cy = X(ax), Y(ay)
        for k in (1, 2, 3):
            g.append(f'<path d="M {cx - 6 + k*9:.0f} {cy - 8 - k*7:.0f} q {6 + k*3} {8 + k*7} 0 {16 + k*14}" '
                     f'fill="none" stroke="{ACCENT}" stroke-width="2.4" stroke-linecap="round" '
                     f'opacity="{1 - k*0.22:.2f}"/>')
        g.append(f'<text x="{cx - 12:.0f}" y="{cy + 6:.0f}" text-anchor="end" font-size="17" '
                 f'font-weight="700" fill="{ACCENT}">TAP</text>')
    for mx, my in [(4.25, 84.25), (55.75, 84.25), (4.25, 38.25), (55.75, 4.25)]:
        g.append(f'<circle cx="{X(mx):.0f}" cy="{Y(my):.0f}" r="{2.6*S:.0f}" fill="#d8d4cb" stroke="{CASE_EDGE}"/>')
    off = "#c9c5bc"
    plain = lit is None and not dim
    g.append(f'<circle cx="{X(LED_G[0]):.0f}" cy="{Y(LED_G[1]):.0f}" r="5" fill="{GREEN if plain else off}"/>')
    g.append(f'<circle cx="{X(LED_R[0]):.0f}" cy="{Y(LED_R[1]):.0f}" r="5" fill="{RED if plain else off}"/>')
    if lit == "green":
        g.append(glow(X(LED_G[0]), Y(LED_G[1]), GREEN))
    elif lit == "red":
        g.append(glow(X(LED_R[0]), Y(LED_R[1]), RED))
    px, py = X(BTN[0]), Y(BTN[1])
    g.append(f'<circle cx="{px:.0f}" cy="{py:.0f}" r="{3.6*S:.0f}" fill="#fbfaf7" stroke="{INK}" stroke-width="2"/>')
    g.append(power_symbol(px, py + 2, 7))
    for sx in (12.0, 19.5):
        g.append(f'<circle cx="{X(sx):.0f}" cy="{Y(6.0):.0f}" r="3" fill="#8d897f"/>')
    for i, (cx_, cy_) in enumerate(CHG):
        if charge == "red" and i == 0:
            g.append(glow(X(cx_), Y(cy_), RED, 3.5))
        elif charge == "green" and i == 1:
            g.append(glow(X(cx_), Y(cy_), GREEN, 3.5))
        else:
            g.append(f'<circle cx="{X(cx_):.0f}" cy="{Y(cy_):.0f}" r="3.2" fill="{off}"/>')
    g.append(f'<rect x="{X(USB_X) - 15:.0f}" y="{CH - 9:.0f}" width="30" height="12" rx="6" fill="#55524c"/>')
    return "".join(g)


def id_card(cx, cy, angle=-8):
    return (f'<g transform="translate({cx - 70:.0f},{cy - 44:.0f}) rotate({angle} 70 44)">'
            f'<rect width="140" height="88" rx="9" fill="#fff" stroke="{INK}" stroke-width="2"/>'
            f'<rect x="0" y="14" width="140" height="16" fill="{ACCENT}"/>'
            f'<circle cx="28" cy="58" r="14" fill="#d9dde6"/>'
            f'<rect x="52" y="46" width="70" height="7" rx="3" fill="#c8ccd6"/>'
            f'<rect x="52" y="60" width="50" height="7" rx="3" fill="#c8ccd6"/></g>')


def finger(px, py):
    """A fingertip pressing at (px, py), coming from below left."""
    return (f'<circle cx="{px:.0f}" cy="{py:.0f}" r="22" fill="none" stroke="{ACCENT}" stroke-width="2.5" opacity=".7"/>'
            f'<circle cx="{px:.0f}" cy="{py:.0f}" r="31" fill="none" stroke="{ACCENT}" stroke-width="2" opacity=".35"/>'
            f'<g transform="translate({px:.0f},{py:.0f}) rotate(35)">'
            f'<rect x="-15" y="-6" width="30" height="110" rx="15" fill="{SKIN}" stroke="{SKIN_EDGE}" stroke-width="2"/>'
            f'<rect x="-9" y="0" width="18" height="20" rx="8" fill="#f8e3d2" stroke="{SKIN_EDGE}" stroke-width="1.2"/>'
            f'</g>')


def shake():
    """Vibration marks on both sides of the case."""
    y = CH * 0.45
    out = []
    for side, x in ((-1, -8), (1, CW + 8)):
        for k in (0, 1):
            dx = side * (k * 9)
            out.append(f'<path d="M {x + dx:.0f} {y - 22:.0f} q {side*7} 11 0 22 q {-side*7} 11 0 22" fill="none" '
                       f'stroke="{INK}" stroke-width="2.4" stroke-linecap="round" opacity="{0.9 - k*0.35:.2f}"/>')
    return "".join(out)


def mini(lit=None, card=False, press=False, cable=False, charge=None, buzzing=False, dim=False,
         badge=None, sleep=False):
    """A small drawing of the device in one state."""
    pad_l, pad_r, pad_t = 40, 40, 14
    pad_b = 70 if (press or cable) else 14
    W, H = CW + pad_l + pad_r, CH + pad_t + pad_b
    g = [case_body(lit, charge, dim, waves=not card)]
    if card:
        g.append(id_card(X(TAP[0]), Y(TAP[1]) + 4))
    if cable:
        ux = X(USB_X)
        g.append(f'<rect x="{ux - 13:.0f}" y="{CH - 4:.0f}" width="26" height="26" rx="5" fill="#3d3b37"/>'
                 f'<path d="M {ux:.0f} {CH + 22:.0f} L {ux:.0f} {CH + pad_b:.0f}" stroke="#3d3b37" stroke-width="8"/>')
    if press:
        g.append(finger(X(BTN[0]), Y(BTN[1])))
    if buzzing:
        g.append(shake())
    if sleep:
        g.append(f'<text x="{CW - 30:.0f}" y="{CH*0.6:.0f}" font-size="44" font-weight="800" fill="{MUTED}" '
                 f'text-anchor="end">z<tspan font-size="34" dy="-16">z</tspan><tspan font-size="24" dy="-14">z</tspan></text>')
    if badge:
        g.append(f'<g transform="translate({CW - 4:.0f},4)"><rect x="-84" y="0" width="88" height="44" rx="22" '
                 f'fill="{ACCENT}"/><text x="-40" y="31" text-anchor="middle" font-size="25" font-weight="800" '
                 f'fill="#fff">{badge}</text></g>')
    return (f'<svg viewBox="0 0 {W:.0f} {H:.0f}" class="mini" xmlns="http://www.w3.org/2000/svg">'
            f'<g transform="translate({pad_l},{pad_t})">{"".join(g)}</g></svg>')


def device_labelled():
    pad_l, pad_r, pad_t, pad_b = 205, 215, 10, 60
    W, H = CW + pad_l + pad_r, CH + pad_t + pad_b
    ax, ay, aw, ah = TAP
    gx, gy = X(LED_G[0]), Y(LED_G[1])
    px, py = X(BTN[0]), Y(BTN[1])
    ux = X(USB_X)

    def lab(x0, y0, x1, y1, text, anchor):
        lines = text.split("|")
        ty = y1 - 9 * (len(lines) - 1)
        spans = "".join(f'<tspan x="{x1 + (-6 if anchor == "end" else 6):.0f}" dy="{0 if i == 0 else 19}">{t}</tspan>'
                        for i, t in enumerate(lines))
        return (f'<line x1="{x0:.0f}" y1="{y0:.0f}" x2="{x1:.0f}" y2="{y1:.0f}" stroke="{MUTED}" stroke-width="1.3"/>'
                f'<circle cx="{x0:.0f}" cy="{y0:.0f}" r="3" fill="{MUTED}"/>'
                f'<text y="{ty:.0f}" text-anchor="{anchor}" class="dl" dominant-baseline="middle">{spans}</text>')
    labels = "".join([
        lab(X(ax + aw/2) - 4, Y(ay), CW + 30, Y(ay), "<tspan class='b'>Tap card here</tspan>", "start"),
        lab(gx, gy, -30, gy - 40, "<tspan class='b'>Lights</tspan>|green / red", "end"),
        lab(px - 3.6*S, py, -30, py, "<tspan class='b'>Power button</tspan>", "end"),
        lab(X(12.0), Y(6.0) + 3, -30, CH + 32, "Small holes:|do not press", "end"),
        lab(X(44.0) + 3, Y(2.5), CW + 30, Y(2.5) - 30, "<tspan class='b'>Charging lights</tspan>", "start"),
        lab(ux + 15, CH - 3, CW + 30, CH + 30, "<tspan class='b'>USB-C port</tspan>", "start"),
    ])
    return (f'<svg viewBox="0 0 {W:.0f} {H:.0f}" class="dev" xmlns="http://www.w3.org/2000/svg">'
            f'<g transform="translate({pad_l},{pad_t})">{case_body()}{labels}</g></svg>')


def laptop():
    return f'''<svg viewBox="0 0 300 200" class="mini" xmlns="http://www.w3.org/2000/svg">
  <rect x="25" y="10" width="250" height="160" rx="10" fill="#2b2b2b"/>
  <rect x="37" y="22" width="226" height="136" rx="4" fill="#fff"/>
  <rect x="37" y="22" width="226" height="28" fill="#3646a8"/>
  <text x="49" y="41" font-size="14" font-weight="700" fill="#fff">Attendance Logger</text>
  <rect x="49" y="60" width="90" height="12" rx="3" fill="#e5e8f5"/>
  <rect x="147" y="60" width="40" height="12" rx="3" fill="#43a047"/>
  <rect x="49" y="82" width="80" height="66" rx="4" fill="#f1f2f7"/>
  <rect x="137" y="82" width="114" height="66" rx="4" fill="#f1f2f7"/>
  <text x="194" y="124" text-anchor="middle" font-size="28" font-weight="700" fill="#2e7d32">17</text>
  <path d="M 5 170 L 295 170 L 277 190 L 23 190 Z" fill="#3d3d3d"/>
</svg>'''

# ---------------------------------------------------------------- app screenshots

def shot(name, crop=None, marks=(), boxes=()):
    """An app screenshot (guide_img/<name>), cropped by the viewBox, with numbered markers and red boxes."""
    raw = (IMG / name).read_bytes()
    w, h = struct.unpack(">II", raw[16:24])
    x0, y0, x1, y1 = crop or (0, 0, w, h)
    over = "".join(f'<rect x="{a - 5}" y="{b - 5}" width="{c - a + 10}" height="{d - b + 10}" rx="10" fill="none" '
                   f'stroke="{RED}" stroke-width="5"/>' for a, b, c, d in boxes)
    over += "".join(f'<circle cx="{x}" cy="{y}" r="24" fill="{RED}" stroke="#fff" stroke-width="5"/>'
                    f'<text x="{x}" y="{y + 10}" text-anchor="middle" font-size="28" font-weight="800" '
                    f'fill="#fff">{n}</text>' for n, x, y in marks)
    data = base64.b64encode(raw).decode()
    return (f'<svg viewBox="{x0} {y0} {x1 - x0} {y1 - y0}" class="shot" xmlns="http://www.w3.org/2000/svg">'
            f'<image href="data:image/png;base64,{data}" width="{w}" height="{h}"/>{over}</svg>')

# ---------------------------------------------------------------- page parts

def card(pic, title, line="", signal=""):
    sig = f'<div class="sig">{signal}</div>' if signal else ""
    ln = f'<p>{line}</p>' if line else ""
    return f'<div class="card"><div class="pic">{pic}</div>{sig}<h3>{title}</h3>{ln}</div>'


def step(n, pic, text):
    return f'<div class="step"><div class="pic">{pic}</div><p><b class="num">{n}</b>{text}</p></div>'


ARROW = (f'<div class="arrow"><svg viewBox="0 0 40 40"><path d="M 6 20 H 30 M 22 11 L 32 20 L 22 29" fill="none" '
         f'stroke="{ACCENT}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/></svg></div>')


def icon(body, vb="0 0 100 100"):
    return f'<svg viewBox="{vb}" class="mini" xmlns="http://www.w3.org/2000/svg">{body}</svg>'


NO = f'<line x1="14" y1="88" x2="86" y2="12" stroke="{RED}" stroke-width="8" stroke-linecap="round"/>'

CSS = f"""
@page {{ size: A4; margin: 12mm 13mm 11mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: Inter, 'DejaVu Sans', Arial, sans-serif; color: {INK}; font-size: 12pt; line-height: 1.35; margin: 0; }}
.page {{ page-break-after: always; }}
.page:last-child {{ page-break-after: auto; }}
h1 {{ font-size: 30pt; margin: 0 0 1mm; letter-spacing: -.4px; }}
.sub {{ color: {MUTED}; font-size: 14pt; margin: 0 0 3mm; }}
h2 {{ font-size: 18pt; margin: 6mm 0 3mm; padding-bottom: 1.5mm; border-bottom: 3px solid {ACCENT}; }}
.page > h2:first-child {{ margin-top: 0; }}
h3 {{ font-size: 13pt; margin: 1.5mm 0 0; }}
p {{ margin: .5mm 0 0; }}
.dl {{ font-family: Inter, Arial, sans-serif; font-size: 18px; fill: {INK}; }}
.b {{ font-weight: 700; }}
svg.dev {{ display: block; width: 100%; height: auto; margin: 0 auto; }}
svg.mini {{ display: block; height: 100%; width: auto; max-width: 100%; margin: 0 auto; }}
svg.shot {{ display: block; width: 100%; height: auto; border: 1px solid #d6d4cc; border-radius: 6px; background: #fff; }}
.grid {{ display: grid; gap: 4mm; }}
.g3 {{ grid-template-columns: repeat(3, 1fr); }}
.g4 {{ grid-template-columns: repeat(4, 1fr); }}
.card {{ background: #f5f4f0; border-radius: 12px; padding: 3mm 3mm 3.5mm; text-align: center; }}
.card .pic {{ height: 48mm; }}
.g4 .card .pic {{ height: 40mm; }}
.short .card .pic {{ height: 34mm; }}
.card p {{ color: {MUTED}; font-size: 11pt; }}
.sig {{ display: flex; justify-content: center; align-items: center; gap: 5px; margin-top: 2mm; min-height: 18px; font-size: 10pt; color: {MUTED}; }}
.flow {{ display: flex; align-items: stretch; gap: 1.5mm; }}
.flow .step {{ flex: 1; }}
.flow .arrow {{ display: flex; align-items: center; }}
.step {{ background: #f5f4f0; border-radius: 12px; padding: 3mm; text-align: center; }}
.step .pic {{ height: 46mm; display: flex; align-items: center; justify-content: center; }}
.step .pic svg.shot {{ width: 100%; height: auto; max-height: 46mm; }}
.big .step .pic {{ height: 62mm; }}
.step p {{ font-size: 11.5pt; margin-top: 2mm; }}
.arrow svg {{ width: 8mm; height: 8mm; }}
.num {{ display: inline-block; background: {RED}; color: #fff; border-radius: 50%; width: 1.6em; height: 1.6em;
        text-align: center; line-height: 1.6em; font-size: .85em; margin-right: 1.5mm; }}
.keys {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5mm 4mm; margin: 2.5mm 0 0; font-size: 12pt; }}
.note {{ background: #fff6e0; border-left: 5px solid #f0a500; padding: 2.5mm 4mm; border-radius: 6px; margin: 3mm 0 0; font-size: 12pt; }}
.row {{ display: grid; grid-template-columns: 1.2fr 1fr; gap: 6mm; align-items: center; margin-top: 4mm; }}
table {{ width: 100%; border-collapse: collapse; }}
td {{ padding: 2mm; border-bottom: 1px solid #e3e1da; vertical-align: middle; font-size: 11.5pt; }}
td:first-child {{ font-weight: 700; width: 40%; }}
.foot {{ color: {MUTED}; font-size: 9.5pt; margin-top: 4mm; }}
"""


def page1():
    return f'''<div class="page">
<h1>Attendance Logger</h1>
<p class="sub">Easy guide for lecturers</p>
{device_labelled()}
<h2>Taking attendance</h2>
<div class="flow big">
 {step(1, mini(lit="green", press=True, buzzing=True), "Press the button.<br>Green light = ON")}
 {ARROW}
 {step(2, mini(lit="green", press=True, badge="2 s"), "Hold 2 s, let go.<br>New lecture starts")}
 {ARROW}
 {step(3, mini(lit="green", card=True, buzzing=True), "Students tap<br>their ID card")}
</div>
</div>'''


def page2():
    return f'''<div class="page">
<h2>Lights and buzzes</h2>
<div class="grid g3">
 {card(mini(lit="green", card=True, buzzing=True), "Marked present", "OK. Next student.", dot(GREEN) + buzz(1))}
 {card(mini(card=True, buzzing=True), "Already marked", "Not counted again.", buzz(2))}
 {card(mini(lit="green", buzzing=True), "New lecture", "Students can tap now.", dot(GREEN) + buzz(3))}
 {card(mini(lit="red"), "Battery low", "Please charge it.", "".join(dot(RED, 5) for _ in range(5)) + "&nbsp;5 blinks")}
 {card(mini(lit="red", buzzing=True), "Memory full", "Connect to the computer.", dot(RED) + buzz(4))}
 {card(mini(lit="red"), "Not working", "Unplug. Try again.", dot(RED, 5) * 3 + "&nbsp;fast, non-stop")}
</div>
<h2>Power button</h2>
<div class="grid g4">
 {card(mini(lit="green", press=True), "Press", "Switch ON")}
 {card(mini(lit="green", press=True, badge="tap"), "Quick press", "Battery check")}
 {card(mini(lit="green", press=True, badge="2 s"), "Hold 2 s", "Next lecture")}
 {card(mini(lit="red", press=True, badge="5 s"), "Hold 5 s", "Switch OFF")}
</div>
</div>'''


def page3():
    return f'''<div class="page">
<h2>Charging</h2>
<div class="grid g3">
 {card(mini(cable=True, charge="red"), "Red = charging", "Any USB-C phone charger")}
 {card(mini(cable=True, charge="green"), "Green = full", "Lasts many months")}
 {card(mini(dim=True, sleep=True, badge="3 min"), "Sleeps by itself", "Press to wake. Records are safe.")}
</div>
<h2>See who came</h2>
<div class="flow">
 {step(1, mini(cable=True, lit="green"), "Connect the<br>USB-C cable")}
 {ARROW}
 {step(2, laptop(), "Open the<br><b>Attendance Logger</b>")}
 {ARROW}
 {step(3, shot("app_lectures.png", (664, 332, 1258, 762), boxes=[(1157, 348, 1238, 427)]), "Pick a lecture.<br>See who came")}
</div>
<h2>Cable still in? Press Eject first</h2>
<div class="flow">
 {step(1, shot("app_lectures.png", (255, 100, 520, 156), boxes=[(271, 112, 353, 144)]), "Press <b>Eject</b><br>in the app")}
 {ARROW}
 {step(2, mini(cable=True, lit="green", buzzing=True), "Green +<br>2 buzzes")}
 {ARROW}
 {step(3, mini(cable=True, lit="green", card=True), "Now students<br>can tap")}
</div>
<div class="note">While the device shows in the app, a tap is <b>not</b> attendance. It is only for adding cards.</div>
</div>'''


def page4():
    return f'''<div class="page">
<h2>The app</h2>
<div>{shot("app_lectures.png", marks=[(1, 745, 237), (2, 206, 366), (3, 646, 368), (4, 1180, 768), (5, 312, 88)])}</div>
<div class="keys">
 <div><b class="num">1</b>Start a lecture</div>
 <div><b class="num">2</b>All lectures</div>
 <div><b class="num">3</b>Who came</div>
 <div><b class="num">4</b>Save as PDF</div>
 <div><b class="num">5</b>Eject</div>
</div>
<h2>Add a new student</h2>
<div class="flow">
 {step(1, shot("app_students.png", (1000, 426, 1252, 484), boxes=[(1131, 439, 1239, 471)]), "Students page:<br><b>Tap a card…</b>")}
 {ARROW}
 {step(2, mini(cable=True, lit="green", card=True), "Tap the card<br>on the device")}
 {ARROW}
 {step(3, shot("app_register.png"), "Type index no.<br>and name. <b>Save</b>")}
</div>
<div class="row">
 <div>{shot("app_students.png", (222, 172, 1258, 408), boxes=[(1147, 244, 1241, 276)])}</div>
 <div><h3>Forgot to add a card?</h3><p>No problem. The device saves every card.
 It shows here, in <b>New cards</b>. Press <b>Register…</b></p></div>
</div>
</div>'''


def page5():
    exe = icon(f'<rect x="22" y="10" width="56" height="80" rx="8" fill="#fff" stroke="{INK}" stroke-width="3"/>'
               f'<path d="M 50 28 V 62 M 36 50 L 50 64 L 64 50" fill="none" stroke="{ACCENT}" stroke-width="6" '
               f'stroke-linecap="round" stroke-linejoin="round"/><rect x="34" y="72" width="32" height="6" rx="3" fill="{ACCENT}"/>')
    smart = icon('<rect x="6" y="14" width="148" height="92" rx="6" fill="#1f5fbf"/>'
                 '<text x="16" y="42" font-size="13" font-weight="700" fill="#fff">Windows protected your PC</text>'
                 '<text x="16" y="64" font-size="11" fill="#dfe8ff" text-decoration="underline">More info</text>'
                 '<rect x="84" y="78" width="62" height="20" fill="#fff"/>'
                 '<text x="115" y="92" text-anchor="middle" font-size="10" fill="#1f5fbf">Run anyway</text>', "0 0 160 120")
    app = icon('<rect x="10" y="10" width="80" height="80" rx="18" fill="#3646a8"/>'
               '<path d="M 28 52 L 44 68 L 74 34" fill="none" stroke="#fff" stroke-width="10" '
               'stroke-linecap="round" stroke-linejoin="round"/>')
    drop = icon(f'<path d="M 50 12 C 50 12 24 44 24 62 A 26 26 0 0 0 76 62 C 76 44 50 12 50 12 Z" fill="#7fb2f0"/>{NO}')
    sun = icon(f'<circle cx="50" cy="48" r="18" fill="#f0a500"/><g stroke="#f0a500" stroke-width="6" stroke-linecap="round">'
               f'<line x1="50" y1="12" x2="50" y2="20"/><line x1="50" y1="76" x2="50" y2="84"/><line x1="14" y1="48" x2="22" y2="48"/>'
               f'<line x1="78" y1="48" x2="86" y2="48"/></g>{NO}')
    fall = icon(f'<rect x="30" y="10" width="40" height="52" rx="8" fill="{CASE}" stroke="{CASE_EDGE}" stroke-width="3"/>'
                f'<path d="M 50 68 V 90 M 40 80 L 50 90 L 60 80" fill="none" stroke="{INK}" stroke-width="5" '
                f'stroke-linecap="round" stroke-linejoin="round"/>{NO}')
    week = icon('<rect x="10" y="22" width="80" height="54" rx="6" fill="#2b2b2b"/><rect x="17" y="29" width="66" height="40" fill="#fff"/>'
                f'<text x="50" y="57" text-anchor="middle" font-size="18" font-weight="800" fill="{ACCENT}">weekly</text>'
                '<path d="M 4 80 H 96 L 90 88 H 10 Z" fill="#3d3d3d"/>')
    return f'''<div class="page">
<h2>Install the app (Windows)</h2>
<div class="grid g3">
 {card(exe, "1. Double-click", "AttendanceLogger-Setup-1.0.0.exe")}
 {card(smart, "2. Blue window?", "More info, then Run anyway")}
 {card(app, "3. Start menu", "Open Attendance Logger")}
</div>

<h2>Quick fixes</h2>
<table>
 <tr><td>No light when a card is tapped</td><td>Press the power button. Hold the card flat on TAP.</td></tr>
 <tr><td>Device does not switch on</td><td>Charge it for some time. Try again.</td></tr>
 <tr><td>App says <i>Device not connected</i></td><td>Press the device button <b>twice quickly</b>, or unplug and plug in.</td></tr>
 <tr><td>Student not on the list</td><td>Card not added yet. Add it (page 4).</td></tr>
 <tr><td>Wrong time in the list</td><td>Press <b>Set device time</b> in the app.</td></tr>
</table>

<h2>Please take care</h2>
<div class="grid g4">
 {card(drop, "Keep dry")}
 {card(sun, "No heat or sun")}
 {card(fall, "Do not drop")}
 {card(week, "Connect weekly", "Saves the records")}
</div>
<p class="foot">Attendance Logger · Easy Guide · October 2026</p>
</div>'''


def main():
    missing = [n for n in ("app_lectures.png", "app_students.png", "app_register.png") if not (IMG / n).exists()]
    if missing:
        sys.exit("missing %s: run app_screenshots.py first" % ", ".join(missing))
    html = (f"<!doctype html><html><head><meta charset='utf-8'><title>Attendance Logger: Easy Guide</title>"
            f"<style>{CSS}</style></head><body>{page1()}{page2()}{page3()}{page4()}{page5()}</body></html>")
    chrome = next((shutil.which(c) for c in ("google-chrome", "chromium", "chromium-browser",
                                              "microsoft-edge") if shutil.which(c)), None)
    if chrome is None:
        sys.exit("needs google-chrome or chromium to print the PDF")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "guide.html"
        src.write_text(html, encoding="utf-8")
        if "--html" in sys.argv:
            shutil.copy(src, HERE / "easy_guide.html")
        subprocess.run([chrome, "--headless=new", "--no-pdf-header-footer", "--disable-gpu",
                        f"--print-to-pdf={OUT}", src.as_uri()], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
