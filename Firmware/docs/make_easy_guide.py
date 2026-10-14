#!/usr/bin/env python3
"""Build Firmware/docs/Attendance_Logger_Easy_Guide.pdf: a short, picture-led guide
for lecturers, in plain words. The device drawing uses the hole positions in
Enclosure/enclosure.py; the lights and buzzes follow App/Src/feedback.c.

    python3 make_easy_guide.py            (needs google-chrome or chromium)
"""
import base64
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "Attendance_Logger_Easy_Guide.pdf"
APP_SHOT = ROOT / "Slides" / "src" / "img" / "app_lectures.png"

GREEN = "#1fa855"
RED = "#d93434"
INK = "#1d1d1b"
MUTED = "#5b5a55"
CASE = "#e9e6df"
CASE_EDGE = "#a9a59b"
ACCENT = "#2a5bd7"

# ---------------------------------------------------------------- small icons

def led(colour, r=9):
    return (f'<svg width="{2*r+2}" height="{2*r+2}" viewBox="0 0 {2*r+2} {2*r+2}">'
            f'<circle cx="{r+1}" cy="{r+1}" r="{r}" fill="{colour}"/>'
            f'<circle cx="{r-2}" cy="{r-2}" r="{r/3:.1f}" fill="#fff" opacity=".45"/></svg>')


def buzz(n=1, long=False):
    """n buzz marks: little wavy lines."""
    w = 30 if long else 18
    parts, x = [], 2
    for _ in range(n):
        pts = " ".join(f"{x + i * w / 6:.1f},{9 + (4 if i % 2 else -4)}" for i in range(7))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{INK}" stroke-width="2.2" '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
        x += w + 7
    return f'<svg width="{x}" height="18" viewBox="0 0 {x} 18">{"".join(parts)}</svg>'


def blinks(colour, n):
    return "".join(led(colour, 6) for _ in range(n))


def signal(*parts):
    return f'<div class="sig">{"".join(parts)}</div>'

# ---------------------------------------------------------------- device drawing
# Board coordinates in mm from Enclosure/enclosure.py (x right, y up from the USB edge).
BOARD_W, BOARD_H, WALL = 60.0, 88.6, 3.0
S = 3.1  # px per mm


def X(x):
    return (x + WALL) * S


def Y(y):
    return (BOARD_H - y + WALL) * S


def power_symbol(cx, cy, r):
    return (f'<path d="M {cx - r*0.62:.1f} {cy - r*0.55:.1f} A {r*0.82:.1f} {r*0.82:.1f} 0 1 0 '
            f'{cx + r*0.62:.1f} {cy - r*0.55:.1f}" fill="none" stroke="{INK}" stroke-width="2" '
            f'stroke-linecap="round"/>'
            f'<line x1="{cx}" y1="{cy - r*0.95:.1f}" x2="{cx}" y2="{cy - r*0.15:.1f}" stroke="{INK}" '
            f'stroke-width="2" stroke-linecap="round"/>')


def device_top(labels=True, card=False):
    w, h = (BOARD_W + 2 * WALL) * S, (BOARD_H + 2 * WALL) * S
    pad_l, pad_r, pad_t, pad_b = (205, 215, 10, 60) if labels else (10, 10, 10, 10)
    W, H = w + pad_l + pad_r, h + pad_t + pad_b
    g = [f'<rect x="0" y="0" width="{w:.0f}" height="{h:.0f}" rx="22" fill="{CASE}" '
         f'stroke="{CASE_EDGE}" stroke-width="2"/>']
    # tap area
    ax, ay, aw, ah = 29.5, 68.5, 40.0, 30.0
    g.append(f'<rect x="{X(ax - aw/2):.0f}" y="{Y(ay + ah/2):.0f}" width="{aw*S:.0f}" height="{ah*S:.0f}" '
             f'rx="12" fill="#f6f4ef" stroke="{ACCENT}" stroke-width="2.5" stroke-dasharray="7 5"/>')
    cx, cy = X(ax), Y(ay)
    for k in (1, 2, 3):   # contactless waves
        g.append(f'<path d="M {cx - 6 + k*9:.0f} {cy - 8 - k*7:.0f} q {6 + k*3} {8 + k*7} 0 {16 + k*14}" '
                 f'fill="none" stroke="{ACCENT}" stroke-width="2.4" stroke-linecap="round" opacity="{1 - k*0.22:.2f}"/>')
    g.append(f'<text x="{cx - 12:.0f}" y="{cy + 5:.0f}" text-anchor="end" class="dl b" fill="{ACCENT}">TAP</text>')
    # holes: mounting screws
    for mx, my in [(4.25, 84.25), (55.75, 84.25), (4.25, 38.25), (55.75, 4.25)]:
        g.append(f'<circle cx="{X(mx):.0f}" cy="{Y(my):.0f}" r="{2.6*S:.0f}" fill="#d8d4cb" stroke="{CASE_EDGE}"/>')
    # status lights
    gx, gy = X(12.5), Y(15.74)
    rx_, ry = X(15.0), Y(15.74)
    g.append(f'<circle cx="{gx:.0f}" cy="{gy:.0f}" r="5" fill="{GREEN}"/>')
    g.append(f'<circle cx="{rx_:.0f}" cy="{ry:.0f}" r="5" fill="{RED}"/>')
    # power button
    px, py = X(4.5), Y(6.0)
    g.append(f'<circle cx="{px:.0f}" cy="{py:.0f}" r="{3.6*S:.0f}" fill="#fbfaf7" stroke="{INK}" stroke-width="2"/>')
    g.append(power_symbol(px, py + 2, 7))
    # service holes
    for sx in (12.0, 19.5):
        g.append(f'<circle cx="{X(sx):.0f}" cy="{Y(6.0):.0f}" r="3" fill="#8d897f"/>')
    # charge lights
    for i, cxl in enumerate((39.0, 41.5, 44.0)):
        g.append(f'<circle cx="{X(cxl):.0f}" cy="{Y(2.5):.0f}" r="3.2" fill="{RED if i == 0 else GREEN}" opacity=".85"/>')
    # USB-C opening on the bottom edge
    ux = X(30.04)
    g.append(f'<rect x="{ux - 15:.0f}" y="{h - 9:.0f}" width="30" height="12" rx="6" fill="#55524c"/>')
    if card:
        g.append(f'<g transform="translate({X(ax) - 70:.0f},{Y(ay) - 46:.0f}) rotate(-8 70 46)">'
                 f'<rect width="140" height="88" rx="9" fill="#fff" stroke="{INK}" stroke-width="2"/>'
                 f'<rect x="0" y="14" width="140" height="16" fill="{ACCENT}"/>'
                 f'<circle cx="28" cy="58" r="14" fill="#d9dde6"/>'
                 f'<rect x="52" y="46" width="70" height="7" rx="3" fill="#c8ccd6"/>'
                 f'<rect x="52" y="60" width="50" height="7" rx="3" fill="#c8ccd6"/></g>')
    body = "".join(g)
    out = [f'<svg viewBox="0 0 {W:.0f} {H:.0f}" class="fig {'dev' if labels else 'devs'}" xmlns="http://www.w3.org/2000/svg">'
           f'<g transform="translate({pad_l},{pad_t})">{body}']
    if labels:
        def lab(x0, y0, x1, y1, text, anchor):
            lines = text.split("|")
            ty = y1 - 8 * (len(lines) - 1)
            spans = "".join(f'<tspan x="{x1 + (-6 if anchor == "end" else 6):.0f}" dy="{0 if i == 0 else 17}">{t}</tspan>'
                            for i, t in enumerate(lines))
            return (f'<line x1="{x0:.0f}" y1="{y0:.0f}" x2="{x1:.0f}" y2="{y1:.0f}" stroke="{MUTED}" stroke-width="1.3"/>'
                    f'<circle cx="{x0:.0f}" cy="{y0:.0f}" r="3" fill="{MUTED}"/>'
                    f'<text y="{ty:.0f}" text-anchor="{anchor}" class="dl" dominant-baseline="middle">{spans}</text>')
        out.append(lab(X(ax + aw/2) - 4, Y(ay), w + 30, Y(ay), "<tspan class='b'>Tap card here</tspan>|(card area)", "start"))
        out.append(lab(gx, gy, -30, gy - 40, "<tspan class='b'>Lights</tspan>|green and red", "end"))
        out.append(lab(px - 3.6*S, py, -30, py, "<tspan class='b'>Power button</tspan>", "end"))
        out.append(lab(X(12.0), Y(6.0) + 3, -30, h + 30, "Small holes:|for service only.|Do not press.", "end"))
        out.append(lab(X(44.0) + 3, Y(2.5), w + 30, Y(2.5) - 30, "<tspan class='b'>Charging lights</tspan>|only when plugged in", "start"))
        out.append(lab(ux + 15, h - 3, w + 30, h + 30, "<tspan class='b'>USB-C port</tspan>|charger or computer", "start"))
    out.append("</g></svg>")
    return "".join(out)


def laptop_figure():
    return f'''<svg viewBox="0 0 640 215" class="fig lap" xmlns="http://www.w3.org/2000/svg">
  <rect x="20" y="40" width="110" height="150" rx="16" fill="{CASE}" stroke="{CASE_EDGE}" stroke-width="2"/>
  <rect x="38" y="56" width="74" height="56" rx="8" fill="#f6f4ef" stroke="{ACCENT}" stroke-width="2" stroke-dasharray="6 4"/>
  <circle cx="45" cy="172" r="9" fill="#fbfaf7" stroke="{INK}" stroke-width="1.8"/>
  <circle cx="64" cy="148" r="4" fill="{GREEN}"/><circle cx="72" cy="148" r="4" fill="{RED}"/>
  <rect x="62" y="186" width="26" height="10" rx="5" fill="#55524c"/>
  <path d="M 75 196 C 75 230, 250 220, 290 175 S 340 150, 360 150" fill="none" stroke="#55524c" stroke-width="5" stroke-linecap="round"/>
  <text x="235" y="160" text-anchor="middle" class="dl">USB-C cable</text>
  <rect x="360" y="14" width="250" height="160" rx="10" fill="#2b2b2b"/>
  <rect x="372" y="26" width="226" height="136" rx="4" fill="#fff"/>
  <rect x="372" y="26" width="226" height="28" fill="#3646a8"/>
  <text x="384" y="45" class="dl b" fill="#fff">Attendance Logger</text>
  <rect x="384" y="64" width="90" height="12" rx="3" fill="#e5e8f5"/>
  <rect x="482" y="64" width="40" height="12" rx="3" fill="#43a047"/>
  <rect x="384" y="86" width="80" height="66" rx="4" fill="#f1f2f7"/>
  <rect x="472" y="86" width="114" height="66" rx="4" fill="#f1f2f7"/>
  <text x="529" y="126" text-anchor="middle" font-size="26" font-weight="700" fill="#2e7d32">17</text>
  <path d="M 340 174 L 630 174 L 612 194 L 358 194 Z" fill="#3d3d3d"/>
  <text x="75" y="28" text-anchor="middle" class="dl b">Device</text>
  <text x="485" y="206" text-anchor="middle" class="dl b">Computer with the app</text>
</svg>'''


def timeline_figure():
    x0, x5 = 70, 600
    def xs(s):
        return x0 + (x5 - x0) * s / 5
    return f'''<svg viewBox="0 0 660 180" class="fig tl" xmlns="http://www.w3.org/2000/svg">
  <rect x="{x0}" y="70" width="{x5 - x0}" height="22" rx="11" fill="#eceae4"/>
  <rect x="{x0}" y="70" width="{xs(0.6) - x0:.0f}" height="22" rx="11" fill="{GREEN}" opacity=".75"/>
  <rect x="{xs(2):.0f}" y="70" width="{xs(5) - xs(2):.0f}" height="22" fill="{ACCENT}" opacity=".18"/>
  <rect x="{xs(5) - 6:.0f}" y="70" width="12" height="22" rx="6" fill="{RED}"/>
  {"".join(f'<line x1="{xs(s):.0f}" y1="96" x2="{xs(s):.0f}" y2="104" stroke="{MUTED}" stroke-width="1.5"/><text x="{xs(s):.0f}" y="120" text-anchor="middle" class="dl">{s} s</text>' for s in range(6))}
  <text x="{x0 - 12}" y="86" text-anchor="end" class="dl b">Press</text>
  <text x="{xs(0.3):.0f}" y="40" text-anchor="middle" class="dl b">Quick press</text>
  <text x="{xs(0.3):.0f}" y="58" text-anchor="middle" class="dl">battery check</text>
  <line x1="{xs(2):.0f}" y1="60" x2="{xs(2):.0f}" y2="104" stroke="{ACCENT}" stroke-width="2.5"/>
  <text x="{xs(2) + 8:.0f}" y="40" class="dl b" fill="{ACCENT}">At 2 s it buzzes once</text>
  <text x="{xs(2) + 8:.0f}" y="58" class="dl">let go now = new lecture</text>
  <text x="{xs(5):.0f}" y="150" text-anchor="end" class="dl b" fill="{RED}">Keep holding to 5 s</text>
  <text x="{xs(5):.0f}" y="168" text-anchor="end" class="dl">= switch off</text>
</svg>'''


def app_figure():
    if not APP_SHOT.exists():
        return ""
    data = base64.b64encode(APP_SHOT.read_bytes()).decode()
    # markers sit beside what they point at, never on top of it
    marks = [(1, 925, 291, "Type the lecture name, press Start lecture"),
             (2, 262, 452, "All lectures"),
             (3, 723, 455, "Who came, with the time"),
             (4, 1353, 912, "Save the list as PDF"),
             (5, 376, 103, "Eject")]
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="26" fill="{RED}" stroke="#fff" stroke-width="5"/>'
                   f'<text x="{x}" y="{y + 11}" text-anchor="middle" font-size="32" font-weight="700" '
                   f'fill="#fff">{n}</text>' for n, x, y, _ in marks)
    keys = "".join(f'<li><b class="num">{n}</b> {t}</li>' for n, _, _, t in marks)
    return (f'<div class="shot"><svg viewBox="0 0 1475 950" xmlns="http://www.w3.org/2000/svg">'
            f'<image href="data:image/png;base64,{data}" width="1475" height="950"/>{dots}</svg></div>'
            f'<ol class="keys">{keys}</ol>')

# ---------------------------------------------------------------- pages

CSS = f"""
@page {{ size: A4; margin: 13mm 14mm 12mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: Inter, 'DejaVu Sans', Arial, sans-serif; color: {INK}; font-size: 11.8pt;
        line-height: 1.42; margin: 0; }}
.page {{ page-break-after: always; }}
.page:last-child {{ page-break-after: auto; }}
h1 {{ font-size: 27pt; margin: 0 0 2mm; letter-spacing: -.3px; }}
.sub {{ color: {MUTED}; font-size: 13pt; margin: 0 0 6mm; }}
h2 {{ font-size: 16pt; margin: 5mm 0 2.5mm; padding-bottom: 1.5mm; border-bottom: 2.5px solid {ACCENT}; }}
h2 .n {{ display: inline-block; background: {ACCENT}; color: #fff; border-radius: 50%; width: 1.5em;
         height: 1.5em; text-align: center; line-height: 1.5em; font-size: .8em; margin-right: 2mm;
         vertical-align: .1em; }}
p {{ margin: 0 0 2.5mm; }}
.fig {{ display: block; width: 100%; height: auto; margin: 2mm auto 3mm; }}
.dev {{ width: 100%; height: auto; }}
.dev .dl {{ font-size: 17px; }}
.devs {{ height: 72mm; width: auto; }}
.lap {{ height: 46mm; width: auto; }}
.tl {{ height: 48mm; width: auto; }}
.dl {{ font-family: Inter, Arial, sans-serif; font-size: 15px; fill: {INK}; }}
.b {{ font-weight: 700; }}
.steps {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm; margin: 3mm 0; }}
.step {{ background: #f5f4f0; border-radius: 10px; padding: 4mm; }}
.step .big {{ font-size: 22pt; font-weight: 800; color: {ACCENT}; line-height: 1; }}
.step h3 {{ margin: 2mm 0 1mm; font-size: 13pt; }}
.step p {{ font-size: 11.2pt; margin: 0; }}
table {{ width: 100%; border-collapse: collapse; margin: 2mm 0 3mm; }}
td, th {{ padding: 1.7mm 2.2mm; vertical-align: middle; border-bottom: 1px solid #e3e1da; text-align: left; }}
th {{ font-size: 10.5pt; color: {MUTED}; text-transform: uppercase; letter-spacing: .5px; font-weight: 600; }}
td.s {{ width: 36%; }}
.sig {{ display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }}
.sig .t {{ font-size: 11pt; color: {MUTED}; margin-left: 4px; }}
.note {{ background: #fff6e0; border-left: 5px solid #f0a500; padding: 3mm 4mm; border-radius: 6px; margin: 3mm 0; }}
.tip {{ background: #eaf1ff; border-left: 5px solid {ACCENT}; padding: 3mm 4mm; border-radius: 6px; margin: 3mm 0; }}
ol.list {{ padding-left: 6mm; margin: 1mm 0 3mm; }}
ol.list li {{ margin-bottom: 1.8mm; }}
.shot {{ width: 150mm; margin: 0 auto; }}
.shot svg {{ width: 100%; height: auto; border: 1px solid #d6d4cc; border-radius: 6px; }}
ol.keys {{ list-style: none; padding: 0; margin: 2mm 0 0; columns: 2; font-size: 11.2pt; }}
ol.keys li {{ margin-bottom: 1.5mm; }}
.num {{ display: inline-block; background: {RED}; color: #fff; border-radius: 50%; width: 1.55em; height: 1.55em;
        text-align: center; line-height: 1.55em; font-size: .85em; margin-right: 1.5mm; }}
.two {{ display: grid; grid-template-columns: 62mm 1fr; gap: 7mm; align-items: center; }}
.foot {{ color: {MUTED}; font-size: 9.5pt; margin-top: 5mm; }}
"""


def page1():
    return f'''<div class="page">
<h1>Attendance Logger</h1>
<p class="sub">An easy guide for lecturers. Students tap their ID card, and the device keeps the record.</p>
{device_top()}
<h2><span class="n">1</span>Taking attendance: 3 easy steps</h2>
<div class="steps">
 <div class="step"><div class="big">1</div><h3>Switch on</h3>
  <p>Press the power button once. You will see a <b>green light</b> and feel a short buzz.</p></div>
 <div class="step"><div class="big">2</div><h3>Start the lecture</h3>
  <p>In the app, press <b>Start lecture</b>. No computer? <b>Hold the button for 2 seconds</b> until it buzzes, then let go.</p></div>
 <div class="step"><div class="big">3</div><h3>Students tap</h3>
  <p>Each student holds the ID card flat on the card area until the device buzzes.</p></div>
</div>
<div class="tip"><b>Before your first lecture:</b> charge the device fully (section 6), install the app
on your computer (section 9) and add your students (section 8). You only need to do this once.</div>
</div>'''


def page2():
    return f'''<div class="page">
<h2><span class="n">2</span>How to tap a card</h2>
<div class="two">
 <div>{device_top(labels=False, card=True)}</div>
 <div>
  <ol class="list">
   <li>Hold the card <b>flat</b> on top of the card area.</li>
   <li>Keep it there for about <b>one second</b>, until you feel the buzz.</li>
   <li>Green light with one buzz means the student is <b>marked present</b>.</li>
  </ol>
  <div class="tip">Only one card at a time, please. Do not put two cards on the device together.</div>
  <div class="tip">Tapping again does no harm. The student is counted only <b>once</b> for each lecture.</div>
 </div>
</div>

<h2><span class="n">3</span>What the lights and buzzes mean</h2>
<table>
 <tr><th>You see / feel</th><th>Meaning</th><th>What to do</th></tr>
 <tr><td class="s">{signal(led(GREEN), buzz(1))}</td><td><b>Marked present.</b></td><td>Nothing. Next student.</td></tr>
 <tr><td class="s">{signal(buzz(2), '<span class="t">two short buzzes</span>')}</td><td>Already marked in this lecture.</td><td>Nothing. It is not counted twice.</td></tr>
 <tr><td class="s">{signal(led(GREEN), buzz(3))}</td><td>A <b>new lecture</b> has started.</td><td>Students can tap now.</td></tr>
 <tr><td class="s">{signal(blinks(RED, 5), '<span class="t">5 red blinks</span>')}</td><td><b>Battery is low.</b></td><td>Charge it with a USB-C charger.</td></tr>
 <tr><td class="s">{signal(led(RED), buzz(4))}</td><td><b>Memory is full.</b> The tap was not saved.</td><td>Connect to the computer and start a lecture from the app. This empties the memory.</td></tr>
 <tr><td class="s">{signal(led(GREEN), buzz(2), '<span class="t">after the computer</span>')}</td><td>Settings saved. Taking attendance again.</td><td>Nothing.</td></tr>
 <tr><td class="s">{signal(led(RED), buzz(3), '<span class="t">after the computer</span>')}</td><td>Settings not accepted. Nothing changed.</td><td>Start the lecture again from the app.</td></tr>
 <tr><td class="s">{signal(blinks(RED, 3), '<span class="t">fast red, non-stop</span>')}</td><td>The device has a fault.</td><td>Unplug, wait 10 seconds, try again. If it repeats, give it to the technical staff.</td></tr>
</table>
</div>'''


def page3():
    return f'''<div class="page">
<h2><span class="n">4</span>The power button</h2>
{timeline_figure()}
<table>
 <tr><th>Do this</th><th>What happens</th></tr>
 <tr><td class="s"><b>Press once</b> (device is off)</td><td>Switches on. Green light and a short buzz.</td></tr>
 <tr><td class="s"><b>Quick press</b> (device is on)</td><td>Shows the battery: 2 green blinks = OK, 5 red blinks = low.</td></tr>
 <tr><td class="s"><b>Hold 2 seconds</b> until it buzzes, then let go</td><td>Starts the <b>next lecture</b> (green and three quick buzzes). Everyone can tap again.</td></tr>
 <tr><td class="s"><b>Hold 5 seconds</b></td><td>Switches off. Red light and a long buzz. No new lecture.</td></tr>
 <tr><td class="s"><b>Press twice quickly</b> (cable in, after Eject)</td><td>Brings the device back on the computer.</td></tr>
</table>
<div class="tip">If nobody taps for <b>3 minutes</b>, the device switches itself off to save the battery.
Just press the button to switch it on again. <b>All records are safe</b>, even when it is off.</div>

<h2><span class="n">5</span>Two lectures back to back</h2>
<p>When one lecture finishes and the next one starts, <b>hold the power button for 2 seconds</b>
until you feel a buzz, then let go. You will see green with three quick buzzes. Now the next
lecture has started and every student can tap again.</p>
<p>The device names it for you: <i>Circuits Lecture 4</i> becomes <i>Circuits Lecture 5</i>.
You can change the name later in the app.</p>
<div class="note">If you do not start a new lecture, a student who already tapped in the last
6 hours will only get two buzzes and will not be counted again.</div>

<h2><span class="n">6</span>Charging</h2>
<p>Use any <b>USB-C</b> phone charger, power bank or computer. The small lights near the USB port
show the charging: <b>red</b> while charging, <b>green</b> when full. The device keeps taking
attendance while it charges. A full charge lasts <b>many months</b> of normal use.</p>
</div>'''


def page4():
    return f'''<div class="page">
<h2><span class="n">7</span>After the lecture: see who came</h2>
{laptop_figure()}
<ol class="list">
 <li>Connect the device to the computer with the <b>USB-C cable</b>.</li>
 <li>Open the <b>Attendance Logger</b> app. It reads the device by itself.
     The top of the window says <i>Device connected</i> and shows the battery.</li>
 <li>Click a lecture to see who came, with the time each student tapped.</li>
 <li>Press <b>Save as PDF</b> or <b>Save list (CSV)</b> to keep or print the list.</li>
</ol>
{app_figure()}
<div class="note"><b>While the device is connected to the computer, taps are not attendance.</b>
They are only for registering cards. To take attendance with the cable still in, press
<b>Eject</b> in the app (or press the device's button once). Green with two buzzes means it is ready.</div>
</div>'''


def page5():
    return f'''<div class="page">
<h2><span class="n">8</span>Adding a new student</h2>
<ol class="list">
 <li>Connect the device to the computer and open the app.</li>
 <li>Go to the <b>Students</b> page and press <b>Tap a card…</b></li>
 <li>Tap the student's card on the device. The card number comes into the app by itself.</li>
 <li>Type the <b>index number</b> and <b>name</b>, then press <b>Save</b>.</li>
</ol>
<div class="tip">Forgot to register a card before the lecture? No problem. The device saves every card.
Register it later: the app shows it in the orange <b>New cards</b> box with a <b>Register…</b> button.</div>

<h2><span class="n">9</span>Installing the app (Windows)</h2>
<ol class="list">
 <li>Get the file <b>AttendanceLogger-Setup-1.0.0.exe</b> (from the project's GitHub page, folder
     <i>Companion/dist</i>) and double-click it.</li>
 <li>If a blue window says <i>Windows protected your PC</i>, click <b>More info</b>, then <b>Run anyway</b>.</li>
 <li>Click <b>Next</b> and <b>Install</b>. Then open <b>Attendance Logger</b> from the Start menu. No internet is needed.</li>
</ol>

<h2><span class="n">10</span>Problems and quick fixes</h2>
<table>
 <tr><th>Problem</th><th>What to do</th></tr>
 <tr><td class="s">No light when a card is tapped</td><td>The device may be off. Press the power button once. Hold the card flat, over the card area.</td></tr>
 <tr><td class="s">Device does not switch on</td><td>Battery may be empty. Charge it for some time, then try again.</td></tr>
 <tr><td class="s">App says <i>Device not connected</i></td><td>Check the cable. If you pressed Eject before, press the device's button <b>twice quickly</b>, or unplug and plug in again.</td></tr>
 <tr><td class="s">A student is not on the list</td><td>The card may not be registered. Register it (section 8); the old taps then show under that student.</td></tr>
 <tr><td class="s">Wrong times in the list</td><td>In the app, press <b>Set device time</b>.</td></tr>
</table>

<h2><span class="n">11</span>Please take care</h2>
<p>Keep the device dry and away from heat. Do not drop it. Do not open the case. Do not press the
small service holes. Keep it charged, and connect it to the computer at least once a week so the
records are saved in the app.</p>
<p class="foot">Attendance Logger · Easy Guide · October 2026</p>
</div>'''


def main():
    html = (f"<!doctype html><html><head><meta charset='utf-8'><title>Attendance Logger: Easy Guide</title>"
            f"<style>{CSS}</style></head><body>{page1()}{page2()}{page3()}{page4()}{page5()}</body></html>")
    chrome = next((shutil.which(c) for c in ("google-chrome", "chromium", "chromium-browser",
                                              "microsoft-edge") if shutil.which(c)), None)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "guide.html"
        src.write_text(html, encoding="utf-8")
        if "--html" in sys.argv:
            shutil.copy(src, HERE / "easy_guide.html")
            print("wrote", HERE / "easy_guide.html")
        if chrome is None:
            sys.exit("needs google-chrome or chromium to print the PDF")
        subprocess.run([chrome, "--headless=new", "--no-pdf-header-footer", "--disable-gpu",
                        f"--print-to-pdf={OUT}", src.as_uri()], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
