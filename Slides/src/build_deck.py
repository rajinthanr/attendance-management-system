"""Build the Group 05 slide deck as HTML (1280 x 720 px slides), then print it to PDF with headless Chrome."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = "img/"
GREEN, DARK, INK = "#119437", "#0b6b46", "#1d1d1f"

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@700;800&family=Poppins:wght@400;500;600;700&display=swap');
@page { size: 1280px 720px; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #ebebeb; }
body { font-family: 'Poppins', 'Segoe UI', Arial, sans-serif; color: #1d1d1f; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.s { width: 1280px; height: 720px; position: relative; overflow: hidden; background: #ebebeb; padding: 54px 70px; page-break-after: always; break-after: page; }
h1 { font: 800 62px/1 'Inter Tight', 'Segoe UI', Arial, sans-serif; letter-spacing: -0.045em; color: #119437; margin: 0 0 26px; }
h1.big { font-size: 96px; line-height: .93; }
.rule { height: 4px; width: 540px; background: #0b6b46; margin: 22px 0 0; }
ul.b { list-style: none; margin: 0; padding: 0; font-weight: 600; font-size: 25px; line-height: 1.32; }
ul.b li { position: relative; padding-left: 26px; margin: 0 0 12px; }
ul.b li::before { content: ''; position: absolute; left: 0; top: .55em; width: 9px; height: 9px; border-radius: 50%; background: #1d1d1f; }
ul.b.sm { font-size: 21px; }
.mut { color: #4d4d4d; font-weight: 500; }
.g { color: #119437; } .dk { color: #0b6b46; }
.card { background: #fff; border: 1.5px solid #119437; border-radius: 4px; }
.num { position: absolute; width: 74px; height: 74px; border-radius: 50%; background: #119437; color: #fff; font: 700 30px/74px 'Poppins', sans-serif; text-align: center; }
table { border-collapse: collapse; width: 100%; background: #fff; }
th { background: #119437; color: #fff; font-weight: 600; text-align: left; padding: 10px 16px; font-size: 19px; }
td { padding: 9px 16px; font-size: 19px; font-weight: 500; border-bottom: 1px solid #d9d9d9; }
td.r, th.r { text-align: right; }
tr.hl td { background: #e3f3e8; font-weight: 700; }
.tile { background: #fff; border: 1.5px solid #119437; border-radius: 4px; padding: 16px 20px; }
.tile .v { font: 800 50px/1 'Inter Tight', sans-serif; color: #119437; letter-spacing: -0.03em; }
.tile .v small { font-size: 24px; font-weight: 700; color: #0b6b46; letter-spacing: 0; }
.big td, .big th { font-size: 17px; padding: 10px 12px; }
.tile .l { font-weight: 600; font-size: 17px; margin-top: 6px; color: #333; }
.bar { height: 34px; background: #119437; border-radius: 3px; }
.barrow { display: grid; grid-template-columns: 330px 1fr 100px; align-items: center; gap: 14px; margin: 9px 0; font-weight: 600; font-size: 18px; }
.barrow .val { font-weight: 700; color: #0b6b46; }
.note { font-size: 15px; color: #555; font-weight: 500; }
.pill { display: inline-block; padding: 3px 14px; border-radius: 20px; font-weight: 600; font-size: 17px; }
.sw { display: inline-block; width: 16px; height: 16px; border-radius: 50%; vertical-align: -2px; margin-right: 6px; }
"""


def slide(inner, extra=""):
    return '<section class="s" %s>%s</section>' % (extra, inner)


def icon_reader():
    return ('<svg width="190" height="150" viewBox="0 0 190 150"><g fill="none" stroke="#2e4a4c" stroke-width="3" stroke-linecap="round">'
            '<g transform="rotate(-38 95 80)"><rect x="42" y="64" width="112" height="30" rx="14" fill="#7bb0b4"/></g>'
            '<path d="M138 26c10 6 16 16 17 28M150 14c14 8 22 22 24 40M118 30c5 3 8 8 9 14"/></g></svg>')


def icon_card():
    return ('<svg width="190" height="170" viewBox="0 0 190 170"><rect x="22" y="20" width="118" height="130" rx="16" fill="#7bb0b4" stroke="#2e4a4c" stroke-width="3"/>'
            '<rect x="42" y="38" width="48" height="8" rx="4" fill="#9ed19a" stroke="#2e4a4c" stroke-width="2"/>'
            '<g transform="rotate(-24 110 95)"><rect x="70" y="70" width="104" height="66" rx="10" fill="#8bbcf2" stroke="#2e4a4c" stroke-width="3"/>'
            '<rect x="82" y="86" width="22" height="16" rx="3" fill="#e9d6a8" stroke="#2e4a4c" stroke-width="2"/></g></svg>')


def icon_feedback():
    return ('<svg width="180" height="190" viewBox="0 0 180 190"><rect x="52" y="14" width="76" height="164" rx="12" fill="#7bb0b4" stroke="#2e4a4c" stroke-width="3"/>'
            '<circle cx="90" cy="80" r="17" fill="#fff" stroke="#2e4a4c" stroke-width="3"/><path d="M80 82l7 7 14-15" fill="none" stroke="#119437" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
            '<g fill="none" stroke="#7bb0b4" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"><path d="M30 60l-10 15 10 15-10 15 10 15"/><path d="M150 60l10 15-10 15 10 15-10 15"/></g></svg>')


def icon_usb():
    return ('<svg width="230" height="160" viewBox="0 0 230 160"><rect x="60" y="14" width="150" height="96" rx="8" fill="#7bb0b4" stroke="#2e4a4c" stroke-width="3"/>'
            '<rect x="72" y="26" width="126" height="70" rx="3" fill="#2e4a4c"/><path d="M40 124h190l-14 20H54z" fill="#7bb0b4" stroke="#2e4a4c" stroke-width="3" stroke-linejoin="round"/>'
            '<path d="M6 140h34" stroke="#2e4a4c" stroke-width="5" stroke-linecap="round"/><rect x="0" y="130" width="14" height="20" rx="3" fill="#2e4a4c"/></svg>')


# --------------------------------------------------------------------------------------------- slides
S = []

S.append(slide(f"""
<div style="position:absolute;left:70px;top:68px;width:780px">
  <h1 class="big">Attendance<br>Management System</h1>
  <div class="rule"></div>
  <div style="margin-top:96px;font-size:26px;font-weight:500;text-decoration:underline;color:{DARK}">Group 05</div>
  <div style="margin-top:26px;font-size:23px;font-weight:700;color:{DARK};line-height:1.35">
    Rajinthan R. &nbsp;&nbsp;&nbsp;: 220502M<br>Praveen V.V.J. : 220491B<br>Sulojan R. &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: 220626V</div>
</div>
<img src="{IMG}case_hero.png" style="position:absolute;right:20px;bottom:10px;width:560px">
"""))

def step(n, title, icon, x, y, icon_style):
    return (f'<div class="card" style="position:absolute;left:{x}px;top:{y}px;width:490px;height:138px;display:flex;align-items:center;justify-content:center;'
            f'text-align:center;padding:0 130px 0 60px"><div style="font-weight:700;font-size:25px;line-height:1.25">{title}</div></div>'
            f'<div class="num" style="left:{x-24}px;top:{y-34}px">{n}</div>'
            f'<div style="position:absolute;{icon_style}">{icon}</div>')

S.append(slide(f"""
<h1>How System Works</h1>
<ul class="b" style="font-size:26px"><li>Automate the process of taking attendance in live physical classes.</li>
<li>A handheld NFC reader records each student card and the time.</li></ul>
{step('01', 'Pass the reader<div class="mut" style="font-size:19px;font-weight:500">hold it near the cards</div>', '', 100, 300, '')}
<div style="position:absolute;left:490px;top:278px">{icon_reader()}</div>
{step('02', 'Tap the student ID', '', 700, 300, '')}
<div style="position:absolute;left:1030px;top:268px">{icon_card()}</div>
{step('03', 'Instant feedback<div class="mut" style="font-size:19px;font-weight:500">light and buzz</div>', '', 100, 520, '')}
<div style="position:absolute;left:500px;top:480px">{icon_feedback()}</div>
{step('04', 'Plug in over USB<div class="mut" style="font-size:19px;font-weight:500">to retrieve the records</div>', '', 700, 520, '')}
<div style="position:absolute;left:1030px;top:528px">{icon_usb().replace('width="230"', 'width="190"')}</div>
"""))

S.append(slide(f"""
<h1>Justification of NFC</h1>
<div style="display:grid;grid-template-columns:600px 1fr;gap:46px">
<ul class="b" style="font-size:23px">
<li>Student ID cards and NFC tags are usually <b>13.56 MHz ISO 14443-A</b> (MIFARE, NTAG). One reader IC, the <b>ST25R3916</b>, reads them over SPI.</li>
<li>Every card has its own number (4, 7 or 10 bytes). That number is all the device stores.</li>
<li>The reader can <b>look for a card by itself</b> every 100 ms while the MCU sleeps.</li>
<li>The antenna is a <b>3-turn loop etched on the PCB</b>: no extra part.</li>
</ul>
<div>
<table>
<tr><th></th><th>First design<br><span style="font-weight:500">125 kHz EM4100</span></th><th>Final<br><span style="font-weight:500">13.56 MHz NFC</span></th></tr>
<tr><td>Cards</td><td>EM4100 tags</td><td>ISO 14443-A cards</td></tr>
<tr><td>Reader</td><td>discrete circuit</td><td>one chip</td></tr>
<tr><td>Card detect</td><td>separate touch IC</td><td>reader's own wake-up</td></tr>
</table>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:22px">
<div class="tile"><div class="v">18.2<small> mA</small></div><div class="l">polling the reader all the time</div></div>
<div class="tile"><div class="v">194<small> µA</small></div><div class="l">with the reader's wake-up mode</div></div>
</div>
<div class="note" style="margin-top:10px">Measured on the board, 8 October 2026 (polling figure from the model).</div>
</div></div>
"""))

idle = [("Reader wake-up mode (every 100 ms)", 184.7), ("Heartbeat LED (10 ms every 5 s)", 5.54), ("MCU in Stop 2, board static", 3.3),
        ("MCU wake-ups (0.4 per second)", 0.2), ("Battery sample (every 10 s)", 0.18)]
rows = "".join(f'<div class="barrow"><div>{n}</div><div><div class="bar" style="width:{max(v/184.7*100, 1.2):.1f}%"></div></div><div class="val">{v:g} µA</div></div>' for n, v in idle)
S.append(slide(f"""
<h1>Power Analysis</h1>
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:18px">
<div class="tile"><div class="v">1.8<small> µA</small></div><div class="l">switched off (Standby)</div></div>
<div class="tile"><div class="v">194<small> µA</small></div><div class="l">idle, waiting for a card</div></div>
<div class="tile"><div class="v">2.5<small> µAh</small></div><div class="l">one card tap (8.9 mC)</div></div>
<div class="tile"><div class="v">18<small> months</small></div><div class="l">on a 1000 mAh cell (13 worst case)</div></div>
</div>
<div style="margin-top:30px;font-weight:700;font-size:22px">Where the 194 µA goes</div>
<div style="margin-top:6px">{rows}</div>
<div class="note" style="margin-top:14px">Measured with a meter in series with the cell (power-test build). Battery life assumes 4 lectures a day of 100 students, with self-discharge.
The RF field (203 mA) and the motor (56.5 mA) only run for milliseconds per tap.</div>
"""))

clk = [("MCU at 4 MHz (chosen)", 15.2), ("MCU at 24 MHz", 42.0), ("MCU at 80 MHz (PLL)", 135.0), ("RF field for the same read", 2030.0)]
rows = "".join(f'<div class="barrow" style="grid-template-columns:150px 1fr 70px;font-size:16px;gap:10px"><div>{n}</div><div><div class="bar" style="width:{max(v/2030*100,1.5):.1f}%;background:{GREEN if i==0 else ("#9cc9a8" if i<3 else "#0b6b46")}"></div></div><div class="val">{v:g} µC</div></div>' for i, (n, v) in enumerate(clk))
S.append(slide(f"""
<h1>Clock Speed Calculation</h1>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:34px;zoom:1.2;margin-top:6px" class="big">
<div>
<table>
<tr><th>Clock</th><th>Speed</th><th>Why</th></tr>
<tr class="hl"><td>Scanning</td><td>4 MHz (MSI)</td><td>no PLL to relock on each wake-up</td></tr>
<tr><td>USB session</td><td>24 MHz (MSI)</td><td>USB needs above 14.2 MHz; power comes from the cable</td></tr>
<tr><td>USB clock</td><td>HSI48 + CRS</td><td>locks to the host, no crystal</td></tr>
<tr><td>RTC, timers</td><td>32.768 kHz</td><td>runs through sleep for under 1 µA</td></tr>
<tr><td>Reader SPI</td><td>500 kHz</td><td>chip allows 10 MHz</td></tr>
</table></div>
<div>
<div style="font-weight:700;font-size:21px;margin-bottom:6px">Charge in one 15 ms card read</div>
{rows}
<div style="font-weight:600;font-size:19px;margin-top:18px;line-height:1.35">Reading a card waits on the radio, not on the processor, so <span class="g">the slowest clock that meets the timing wins</span>.
At 4 MHz the MCU is under 1 % of a read.</div>
<div class="note" style="margin-top:8px">Q = I × t: 1.01 mA × 15 ms at 4 MHz (measured); 2.8 mA and 9 mA from the datasheet for 24 and 80 MHz.</div>
</div></div>
"""))

# memory: flash map
S.append(slide(f"""
<h1>Memory</h1>
<div style="zoom:1.12"><div style="font-weight:700;font-size:21px;margin-bottom:10px">STM32L432KB: 128 kB of flash, 64 pages of 2 kB</div>
<div style="display:flex;height:110px;border:1.5px solid {GREEN};background:#fff">
  <div style="flex:36;background:#7bb0b4;display:flex;flex-direction:column;justify-content:center;padding-left:18px;font-weight:700;font-size:21px;color:#fff;position:relative">Program: 36 pages, 72 kB
    <span style="font-weight:500;font-size:16px">image 60.6 kB at -Og, 11.4 kB free</span></div>
  <div style="flex:1;background:#f4a886;border-left:2px solid #fff;border-right:2px solid #fff"></div>
  <div style="flex:27;background:{GREEN};display:flex;flex-direction:column;justify-content:center;padding-left:18px;font-weight:700;font-size:21px;color:#fff">Attendance log: 27 pages
    <span style="font-weight:500;font-size:16px">6,858 records</span></div>
</div>
<div style="display:flex;gap:30px;font-size:15px;font-weight:600;margin-top:8px"><span><span class="sw" style="background:#7bb0b4"></span>program</span><span><span class="sw" style="background:#f4a886"></span>config page (device ID)</span><span><span class="sw" style="background:{GREEN}"></span>log</span></div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:40px;margin-top:30px">
<ul class="b" style="font-size:21px">
<li>One record is <b>8 bytes</b>: card number and time. That is exactly one flash double-word.</li>
<li>A page holds 254 records. <b>6,858 records</b> is about <b>64 lectures</b> of 100 students.</li>
<li>The log fills in about 16 teaching days. The app clears it each time a lecture starts.</li>
</ul>
<div>
<table>
<tr><th>Build</th><th class="r">Image</th><th>Fits 72 kB</th></tr>
<tr><td>Debug (-Og)</td><td class="r">62.1 kB</td><td>yes, 11.4 kB free</td></tr>
<tr class="hl"><td>Release (-Os)</td><td class="r">51.5 kB</td><td>yes, 21.7 kB free</td></tr>
</table>
<div class="note" style="margin-top:10px">Every page given to the program is 254 records less in the log, so 36 / 28 is the split we chose.</div>
</div></div></div>
"""))

# architecture diagram
def box(x, y, w, h, t, sub="", fill="#fff", stroke=GREEN, tc=INK):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    s += f'<text x="{x+w/2}" y="{y+h/2-(6 if sub else -6)}" text-anchor="middle" font-family="Poppins,Segoe UI,Arial" font-weight="700" font-size="19" fill="{tc}">{t}</text>'
    if sub:
        s += f'<text x="{x+w/2}" y="{y+h/2+16}" text-anchor="middle" font-family="Poppins,Segoe UI,Arial" font-weight="500" font-size="14" fill="{tc if fill!="#fff" else "#555"}">{sub}</text>'
    return s


def arrow(x1, y1, x2, y2, label="", lx=None, ly=None, both=False):
    s = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#0b6b46" stroke-width="2.4" marker-end="url(#a)" {"marker-start=\"url(#a2)\"" if both else ""}/>'
    if label:
        s += f'<text x="{lx if lx is not None else (x1+x2)/2}" y="{ly if ly is not None else (y1+y2)/2-8}" text-anchor="middle" font-family="Poppins,Segoe UI,Arial" font-weight="600" font-size="14" fill="#0b6b46">{label}</text>'
    return s


svg = f"""
<svg viewBox="0 0 1140 470" width="1140" height="470">
<defs><marker id="a" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0 0L9 4.5L0 9z" fill="#0b6b46"/></marker>
<marker id="a2" markerWidth="9" markerHeight="9" refX="2" refY="4.5" orient="auto"><path d="M9 0L0 4.5L9 9z" fill="#0b6b46"/></marker></defs>
{box(10,20,170,70,'USB-C','5 V and data')}
{box(250,20,180,70,'Charger','MCP73833')}
{box(500,20,170,70,'Li-ion cell','1000 mAh','#fde6da','#f4a886')}
{arrow(180,55,250,55,'')}{arrow(430,55,500,55,'')}
{box(500,150,170,64,'3.3 V LDO','TPS7A0233')}
{arrow(585,90,585,150,'')}
{box(445,275,280,100,'STM32L432KB','Cortex-M4 · 128 kB flash · 4 MHz','#119437','#0b6b46','#fff')}
{arrow(585,214,585,275,'3.3 V',612,250)}
{arrow(95,90,95,325,'',)}{arrow(95,325,445,325,'USB data',270,316)}
{box(800,275,290,100,'ST25R3916','13.56 MHz NFC reader')}
{arrow(725,325,800,325,'SPI',762,316,both=True)}
{box(800,140,150,66,'Antenna','3-turn PCB loop','#e3f3e8')}
{arrow(875,206,875,275,'')}
<path d="M670 55 H1040 V275" fill="none" stroke="#0b6b46" stroke-width="2.4" marker-end="url(#a)"/>
<text x="1030" y="110" text-anchor="end" font-family="Poppins,Segoe UI,Arial" font-weight="600" font-size="14" fill="#0b6b46">reader and motor run straight from the cell</text>
{box(270,420,180,46,'Green / red LED','', '#fff')}
{box(480,420,190,46,'Vibration motor','', '#fff')}
{box(700,420,170,46,'Power button','', '#fff')}
{arrow(360,420,500,375,'')}{arrow(575,420,585,375,'')}{arrow(785,420,660,375,'')}
</svg>"""
S.append(slide(f"""
<h1>Architecture</h1>
<div style="margin-top:-6px">{svg}</div>
<div class="note" style="margin-top:2px;font-size:16px;font-weight:600;color:#333">Firmware is two layers: <b>App</b> decides (it also runs on a PC for testing), <b>Bsp</b> only talks to the hardware.
The USB drive holds ATTEND.CSV (taps), LECTURES.CSV, STATUS.TXT and SETTINGS.CSV.</div>
"""))

S.append(slide(f"""
<h1>PCB Design</h1>
<img src="{IMG}pcb_top.png" style="position:absolute;left:60px;top:122px;height:580px">
<div style="margin-left:440px;padding-top:6px">
<ul class="b sm">
<li>Two layers, <b>60 × 89 mm</b>, 88 parts, all on the top side.</li>
<li>NFC loop antenna etched on the board, <b>40 × 30 mm</b>, 3 turns.</li>
<li>USB-C at the bottom edge charges the cell and shows the drive.</li>
<li>Reader and motor run straight from the cell; the MCU from a 3.3 V LDO.</li>
</ul>
<table style="margin-top:12px">
<tr><th>Block</th><th>Part</th></tr>
<tr><td>MCU</td><td>STM32L432KB</td></tr>
<tr><td>NFC reader</td><td>ST25R3916</td></tr>
<tr><td>Charger</td><td>MCP73833</td></tr>
<tr><td>LDO</td><td>TPS7A0233</td></tr>
<tr><td>USB protection</td><td>USBLC6-2SC6</td></tr>
</table>
</div>
"""))

S.append(slide(f"""
<h1>Enclosure Design</h1>
<img src="{IMG}case_exploded.png" style="position:absolute;left:60px;top:118px;height:580px">
<div style="position:absolute;left:740px;top:130px;width:470px">
<ul class="b" style="font-size:21px">
<li>Two printed parts and a button plunger: <b>base</b>, <b>lid</b>, <b>power button</b>.</li>
<li>Size <b>65 × 94 × 27.5 mm</b>.</li>
<li>The board screws down on four standoffs; the lid takes four M3 screws.</li>
<li>A bay under the board holds a LiPo up to 45 × 70 × 7 mm.</li>
<li>Cut-outs for the USB-C, the LEDs and the buttons.</li>
</ul>
<div class="note">Parametric: <b>Enclosure/enclosure.py</b> reads the board outline and writes the STL files.</div>
</div>
"""))

S.append(slide(f"""
<h1>The Companion App</h1>
<div style="display:grid;grid-template-columns:760px 1fr;gap:34px;align-items:start">
<img src="{IMG}app_lectures.png" style="width:760px;border:1.5px solid #119437;border-radius:6px;box-shadow:0 6px 18px rgba(0,0,0,.18)">
<div>
<ul class="b sm">
<li>Plug the device in and the app reads every tap.</li>
<li>Type a lecture name and press <b>Start lecture</b>.</li>
<li>See who came: index number, name, time.</li>
<li>Save each lecture as <b>CSV</b> or <b>PDF</b>.</li>
<li>Register new cards from the device.</li>
</ul>
<div class="note">Python + Qt, with a SQLite database on the PC. The device keeps no student list.</div>
</div></div>
"""))

def led(c, ms, vib=False):
    return ""

S.append(slide(f"""
<h1>Quick Guide</h1>
<div style="display:grid;grid-template-columns:1fr 470px;gap:40px">
<table>
<tr><th>You see</th><th>It means</th></tr>
<tr><td><span class="sw" style="background:#1fa855"></span>Green + one short buzz</td><td>Card recorded</td></tr>
<tr><td><span class="sw" style="background:#1fa855"></span>Two quick buzzes</td><td>Already recorded in this lecture</td></tr>
<tr><td><span class="sw" style="background:#1fa855"></span>Green + three quick buzzes</td><td>New lecture started</td></tr>
<tr><td><span class="sw" style="background:#d93434"></span>Red blinking 5 times</td><td>Battery low</td></tr>
<tr><td><span class="sw" style="background:#d93434"></span>Red + four buzzes</td><td>Memory full, tap not recorded</td></tr>
<tr><td><span class="sw" style="background:#d93434"></span>Red + long buzz</td><td>Switching off</td></tr>
</table>
<div>
<div style="font-weight:700;font-size:22px;margin-bottom:8px">The power button</div>
<table>
<tr><td>Press (off)</td><td>Switch on</td></tr>
<tr><td>Tap</td><td>Show the battery</td></tr>
<tr><td>Hold 2 s</td><td>Start next lecture</td></tr>
<tr><td>Hold 5 s</td><td>Switch off</td></tr>
</table>
<div style="font-weight:600;font-size:18px;margin-top:16px;line-height:1.35">It switches itself off after 3 minutes without a tap. Records are kept.</div>
</div></div>
<div style="margin-top:26px;display:flex;gap:18px;font-weight:600;font-size:19px">
<div class="card" style="padding:12px 18px"><span class="g">1</span> Switch on</div>
<div class="card" style="padding:12px 18px"><span class="g">2</span> Tap cards</div>
<div class="card" style="padding:12px 18px"><span class="g">3</span> Hold 2 s for the next lecture</div>
<div class="card" style="padding:12px 18px"><span class="g">4</span> Plug in, open the app</div>
</div>
"""))

costs = [("Electronic parts", 11.20), ("Battery, motor, case", 6.70), ("Import duty, VAT, levies", 4.80), ("PCB and assembly", 0.96),
         ("Test, freight, yield loss", 1.74)]
rows = "".join(f'<div class="barrow" style="grid-template-columns:260px 1fr 80px"><div>{n}</div><div><div class="bar" style="width:{v/11.2*100:.1f}%"></div></div><div class="val">${v:.2f}</div></div>' for n, v in costs)
S.append(slide(f"""
<h1>Total Cost</h1>
<div style="display:grid;grid-template-columns:620px 1fr;gap:44px">
<div>
<table>
<tr><th>Units made</th><th class="r">1</th><th class="r">100</th><th class="r">1,000</th><th class="r">10,000</th></tr>
<tr><td>Cost per unit (USD)</td><td class="r">227.62</td><td class="r">32.43</td><td class="r"><b>25.40</b></td><td class="r">18.31</td></tr>
<tr><td>Cost per unit (LKR)</td><td class="r">75,115</td><td class="r">10,702</td><td class="r"><b>8,382</b></td><td class="r">6,042</td></tr>
<tr class="hl"><td>Price at 40 % margin (USD)</td><td class="r">379</td><td class="r">54.05</td><td class="r">42.33</td><td class="r">30.52</td></tr>
</table>
<div class="note" style="margin-top:10px">Landed in Sri Lanka and tested: parts from LCSC, boards from JLCPCB, freight, 25 % import charges, final assembly. 1 USD = 330 LKR.</div>
<div style="font-weight:700;font-size:20px;margin-top:20px">Biggest parts at 1,000 units</div>
<div style="font-size:19px;font-weight:600;margin-top:6px;line-height:1.5">STM32L432KB $3.25 · ST25R3916 $3.40 · charger $1.12 · USB-C $0.72</div>
</div>
<div>
<div style="font-weight:700;font-size:22px;margin-bottom:6px">Where $25.40 goes (1,000 units)</div>
{rows}
<div class="note" style="margin-top:12px">Up to 100 units the case is 3D printed. At 1,000 it is moulded with an aluminium tool ($3,000), about $3 a unit.</div>
</div></div>
"""))

S.append(slide(f"""
<h1>What Is Next</h1>
<ul class="b" style="font-size:26px">
<li>Tune the antenna (C16 to C19, R15), then measure the field current and the idle current again.</li>
<li>Count false wake-ups over an hour with no card near.</li>
<li>Ask ST or a distributor for a quote at 100 units or more: LCSC held only 27 ST25R3916.</li>
<li>Radio type approval for a 13.56 MHz transmitter (TRCSL) before selling.</li>
<li>Change R6 to 2 kΩ so the charger suits a USB-C port (500 mA).</li>
</ul>
<div style="position:absolute;right:70px;bottom:52px;font-size:44px;font-weight:800;font-family:'Inter Tight',sans-serif;letter-spacing:-0.04em;color:{GREEN}">Thank you</div>
"""))

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Attendance Management System - Group 05</title>
<style>{CSS}</style></head><body>{"".join(S)}</body></html>"""
open(os.path.join(HERE, "deck.html"), "w", encoding="utf-8").write(html)
print("slides:", len(S))
