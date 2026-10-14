#!/usr/bin/env python3
"""Slim two-part 3D-printable enclosure for the Attendance Management System PCB.

The board carries its tall parts on the back (J2 battery connector, J5 SWD header,
TH1), so the front is flat but for the USB-C socket and the buttons. The case is:
  base  the deep part: battery, motor and the back-side parts under the board
  lid   a thin flat-topped shell, hollow over the board, with walled light pipes to the
        LEDs, guide tubes to BOOT0 / RESET and a flexure POWER button over SW3

Writes binary STL files to stl/ next to this script, each in its print orientation,
none needing supports:
  base.stl       floor on the bed
  lid.stl        top face on the bed
  lid_inlay.stl  the tap graphic and power-button marks as a separate body, for a second
                 colour (optional)
  battery.stl    the 803040 cell and motor.stl the coin motor, in their fitted position
  motor.stl      (reference models, not for printing)
  assembly.stl   everything in place: base, lid, inlay, board (from stl/pcb.stl, written
                 by export_pcb.py), battery and motor; for viewing only

Needs:  pip install manifold3d numpy matplotlib    (matplotlib only for the text outline)

Hardware: M3 countersunk screws (ISO 10642 / DIN 7991) and 4 M3 hex nuts; the script
picks the length for each hole (printed at the end). Each screw goes down through the
lid and the board's mounting hole into a nut pushed up into the hex pocket under the base.

Parts it is sized for:
  battery  803040 LiPo, 40 x 30 x 8 mm, under the board, clear of the NFC loop: walled
           bay on a raised platform, clamped by the board through a 1 mm foam pad
  motor    10 mm coin vibration motor, in a cup on a pedestal beside the battery,
           clamped by the board the same way (thin pad)
Fitted on the back: J2 (JST-XH B2B-XH-A in the XA footprint, battery plugged in) and J5 (SWD). J4 takes the motor
leads soldered straight into its holes; J3 (PN532 socket) is not fitted.

Board parts (position, side, courtyard, through-hole pads) are read from the .kicad_pcb
at run time; set AMS_PCB to use another board file.
Coordinates: x = KiCad x - 100, y = 145 - KiCad y (board spans 0..60 x 0..88.5,
USB-C edge at y = 0), z = 0 at the underside of the base. All values in mm.
"""
import math
import os
import re
import struct

import numpy as np
from manifold3d import CrossSection, FillRule, Manifold, set_circular_segments

set_circular_segments(96)

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.environ.get('AMS_PCB', os.path.join(HERE, '..', 'PCB', 'Attendance Management System.kicad_pcb'))

# ---------------------------------------------------------------- board facts
BOARD_W, BOARD_L, BOARD_R = 60.0, 88.5, 2.0      # Edge.Cuts outline, corner radius
BOARD_T = 1.6
MOUNT_HOLES = [(4.25, 84.25), (55.75, 84.25), (4.25, 38.25), (55.75, 4.25)]  # 4.4 mm holes
MOUNT_HOLE_D = 4.4

USB_X = 30.04             # J1 (GCT USB4110) centre; shell 8.94 x 3.26, front at the board edge
USB_SHELL_H = 3.26
SW_POWER = (4.5, 6.0)     # SW3, CK PTS636 SM25, 2.5 mm tall
SW_BOOT0 = (12.0, 6.0)    # SW2
SW_RESET = (19.5, 6.0)    # SW1
SW_TOP = 2.5
STATUS_LEDS = [(12.5, 15.74), (15.0, 15.74)]              # D6 green, D5 red
CHARGE_LEDS = [(39.0, 2.5), (41.5, 2.5), (44.0, 2.5)]     # charger STAT1 / STAT2 / PG
ANTENNA = (29.5, 68.5, 40.0, 30.0)  # AE1 loop centre and size
J2_PLUG_H = 9.8                     # JST-XH B2B-XH-A with the XHP-2 plug mated (JST: 7.0 header, 9.8 mated)

# Height of each footprint away from its side of the board, by footprint name; first
# match wins. None: not there (antenna copper, logo, standoffs and J3 not fitted).
PART_HEIGHTS = [
    ('Mounting_Wuerth', None), ('NFC_Loop', None), (':wx', None), ('SolderWirePad', None),
    ('PinSocket', None),                   # J3, PN532 socket: not fitted
    ('PinHeader_1x02', 2.0),               # J4: motor leads soldered in, no header
    ('JST_XA', J2_PLUG_H),                 # J2: XA footprint, XH header fitted (same 2.5 mm pitch)
    ('PinHeader', 8.5),                    # J5, SWD
    ('R_Axial', 7.0),                      # TH1, standing NTC
    ('USB_C', USB_SHELL_H),
    ('SW_Tactile', SW_TOP),
    ('D_SMA', 2.4),
    ('', 1.3),                             # passives, ICs, crystals, LEDs
]


def _sexpr(text):
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)
    stack = [[]]
    for t in tokens:
        if t == '(':
            stack.append([])
        elif t == ')':
            node = stack.pop()
            stack[-1].append(node)
        else:
            stack[-1].append(t[1:-1] if t.startswith('"') else t)
    return stack[0][0]


def board_parts(path=PCB):
    """[(ref, footprint, bottom, (x0, y0, x1, y1) courtyard, height, [(x, y) THT pads])]."""
    def kids(node, key):
        return [c for c in node if isinstance(c, list) and c and c[0] == key]

    parts = []
    for fp in kids(_sexpr(open(path).read()), 'footprint'):
        name = fp[1]
        height = next(h for key, h in PART_HEIGHTS if key in name)
        if height is None:
            continue
        bottom = kids(fp, 'layer')[0][1] == 'B.Cu'
        at = kids(fp, 'at')[0]
        fx, fy = float(at[1]), float(at[2])
        rot = math.radians(-float(at[3])) if len(at) > 3 else 0.0

        def place(px, py):
            x = fx + px * math.cos(rot) - py * math.sin(rot)
            y = fy + px * math.sin(rot) + py * math.cos(rot)
            return x - 100.0, 145.0 - y

        pts = []
        for g in fp:
            if not (isinstance(g, list) and g[0] in ('fp_line', 'fp_rect', 'fp_poly', 'fp_circle', 'fp_arc')):
                continue
            if not any('CrtYd' in lay[1] for lay in kids(g, 'layer')):
                continue
            for sub in g:
                if isinstance(sub, list) and sub[0] in ('start', 'end', 'mid', 'center'):
                    pts.append(place(float(sub[1]), float(sub[2])))
                elif isinstance(sub, list) and sub[0] == 'pts':
                    pts += [place(float(p[1]), float(p[2])) for p in kids(sub, 'xy')]
        if not pts:
            continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        tht = [place(float(kids(p, 'at')[0][1]), float(kids(p, 'at')[0][2]))
               for p in kids(fp, 'pad') if p[2] == 'thru_hole']
        ref = next(p[2] for p in kids(fp, 'property') if p[1] == 'Reference')
        parts.append((ref, name.split(':')[-1], bottom, (min(xs), min(ys), max(xs), max(ys)), height, tht))
    return parts


# ---------------------------------------------------------------- bought parts
BATT_L, BATT_W, BATT_T = 40.0, 30.0, 8.0         # 803040
MOTOR_D, MOTOR_T = 10.0, 3.0                     # coin motor
SCREW_D, CSK_D = 3.4, 6.6                        # M3 clearance hole, countersink top diameter
NUT_AF, NUT_H = 5.5, 2.4                         # M3 hex nut

# ---------------------------------------------------------------- case parameters
GAP = 0.4                 # board edge to wall
WALL = 2.2
FLOOR = 1.4
BELOW = 10.6              # board underside to floor: JST-XH plug 9.8, then 1.6 mm (with the floor pocket)
                          # for its leads to bend flat: tight for 1.2 mm insulation
LEAD_TAIL = 2.0           # through-hole leads out of the far side of the board
LID_H = 5.2               # board top to lid top: USB-C shell 3.26 + 0.34 under a 1.6 mm top
TOP = 1.6                 # lid top thickness
COLUMN_D = 7.0            # lid screw columns, bearing on the board round each hole
LIP_T, LIP_H, LIP_CLR = 1.0, 1.6, 0.15   # base lip that locates the lid
BOSS_D = 8.0              # round the nut; clears J2 by 0.15 mm
NUT_POCKET_AF = NUT_AF + 0.3
CHAMFER_TOP, CHAMFER_BED, REVEAL = 0.8, 0.6, 0.5   # lid top edges, base bottom edge, seam groove
LED_TOP = 1.3             # LED height above the board
LED_PIPE_D, LED_BORE = 3.2, 1.9       # walled light pipe from the lid down to each LED
PIN_TUBE_D, PIN_BORE = 3.6, 1.6       # paper-clip guide tube down to BOOT0 / RESET

# Moulding: one straight pull per part, parting line at the seam; no undercuts. Walls
# carry DRAFT_WALL, everything else DRAFT_CORE, tapering away from the parting line.
# Thick sections are cored out (rib grid under the battery, tubes for posts and pedestal).
DRAFT_WALL = 1.0          # degrees
DRAFT_CORE = 0.5
RIB_T = 1.2               # ribs and gussets, about 0.55 x WALL

# USB-C: a three-sided bezel. The outer pocket for the cable's overmould runs up through
# the top of the lid (a U-notch in the front edge, chamfered on the left, right and
# bottom); behind it a thin inner face hugs the socket, so the plug's metal seats within
# 0.5 mm of the socket face and nothing else shows. The pocket's bottom corners lie wholly
# in the base and the mouth's top corners in the lid, so each half is an open notch.
USB_PLUG_W, USB_PLUG_H, USB_PLUG_R = 12.4, 7.0, 1.5      # outer pocket (overmould)
USB_MOUTH_W, USB_MOUTH_H = 9.6, 4.0                     # inner opening round the 8.94 x 3.26 shell
USB_MOUTH_R = (0.3, 1.0)                                # bottom, top corner radius (bottom stays in the base)
USB_STEP_Y = -1.0                     # face of the inner step; the shell front is at y = -0.5
USB_BEZEL = 0.6                       # 45 degree chamfer round the outer pocket

# battery and motor under the board, each clamped between a raised seat and the board
BATT_XY = (8.8, 8.0)                             # lower-left corner: no leads above it
BATT_PAD = 1.0                                   # foam pad between battery and board
BATT_LEADS_Y = (16.0, 17.6)                      # where the model's leads leave the +x end
BATT_LEAD_L = 4.0
BAY_CLR, BAY_WALL, BAY_WALL_H, BAY_LEG = 0.3, 1.2, 4.0, 6.0   # walls rise 4 mm up its sides
SEAT_PITCH = 8.0                                 # rib grid the battery sits on
MOTOR_XY = (55.2, 26.0)                          # between J2 and J4, 0.2 mm off the drafted wall
MOTOR_PAD = 0.5                                  # thin pad between motor and board
MOTOR_CUP = 1.5                                  # depth of the cup round the motor
MOTOR_CUP_WALL = 1.2
PEDESTAL_BORE = 7.0                              # cored pedestal under the motor
J2_POCKET = 0.8                                  # floor pocket under the plug for the wire bend

# board supports: under the POWER switch and under the tap area (cored tubes, gusseted)
POSTS = [(4.5, 6.0), (12.0, 62.0), (48.0, 62.0), (12.0, 78.0), (48.0, 78.0)]
POST_D, POST_BORE = 5.0, 2.0
POST_GUSSET = (3.0, 5.0)                         # length, height
BOSS_GUSSET = (4.0, 7.0)
BOSS_RIB_REACH = 8.0                             # boss-to-wall ribs where a wall is this close
RIB_DROP = 2.0                                   # ribs stop this far under the board

# POWER button: a flexure tab cut out of the top, its stem resting just above SW3.
# 1.0 mm thick, 8.4 mm wide, hinged 16 mm from the stem: about 0.7 N of spring on top
# of the switch's own 1.6-2.5 N, and 0.4 mm of travel.
TAB = (0.6, 1.0, 9.0, 22.0)                      # x0, y0 (free end), x1, y1 (hinge)
TAB_SLOT = 0.6
TAB_T = 1.0
STEM_D = 4.0
STEM_CLR = 0.15                                  # stem to switch top, at rest
SKIRT_T = 0.8                                    # wall round the slot, hides the inside
BUTTON_RING_R = 3.6                              # ring round the power symbol marks where to press
MARK_DEPTH = 0.6                                 # debossed marks; colour change at this print height

Z_BOARD_BOT = FLOOR + BELOW
Z_BOARD_TOP = Z_BOARD_BOT + BOARD_T              # base/lid split plane
Z_SPLIT = Z_BOARD_TOP
Z_TOP = Z_BOARD_TOP + LID_H
Z_CEIL = Z_TOP - TOP
Z_USB = Z_BOARD_TOP + USB_SHELL_H / 2

# where the battery and motor sit, for the fit check and view.py
BATT_BOX = (BATT_XY[0], BATT_XY[1], Z_BOARD_BOT - BATT_PAD - BATT_T,
            BATT_XY[0] + BATT_L, BATT_XY[1] + BATT_W, Z_BOARD_BOT - BATT_PAD)
MOTOR_Z = (Z_BOARD_BOT - MOTOR_PAD - MOTOR_T, Z_BOARD_BOT - MOTOR_PAD)

STD_SCREWS = (6, 8, 10, 12, 16, 20, 25, 30)


def hole_top(y):
    return Z_TOP


def screw_length(y):
    """Longest standard M3 screw whose tip stays inside the base."""
    return max(l for l in STD_SCREWS if l <= hole_top(y))


def nut_pocket_top(y):
    """The nut sits at the top of its pocket, wholly above the screw tip."""
    return hole_top(y) - screw_length(y) + NUT_H + 0.3


# ---------------------------------------------------------------- geometry helpers
def rrect(w, l, r, x0=0.0, y0=0.0):
    """Rounded rectangle with its lower-left corner at (x0, y0)."""
    return (CrossSection.square((w - 2 * r, l - 2 * r))
            .translate((x0 + r, y0 + r)).offset(r))


def rect(x0, y0, x1, y1):
    return CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))


def board_outline(grow):
    return rrect(BOARD_W, BOARD_L, BOARD_R).offset(grow)


def slab(cs, z0, z1):
    return Manifold.extrude(cs, z1 - z0).translate((0, 0, z0))


def cyl(x, y, z0, z1, d, d_top=None):
    r = d / 2
    rt = r if d_top is None else d_top / 2
    return Manifold.cylinder(z1 - z0, r, rt).translate((x, y, z0))


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def chamfered_slab(cs, z0, z1, c_bot=0.0, c_top=0.0):
    """Extrusion of a convex outline with 45 degree chamfers on its bottom and top edges."""
    layers = []
    if c_bot:
        layers.append(slab(cs.offset(-c_bot), z0, z0 + 0.01))
    layers.append(slab(cs, z0 + c_bot, z1 - c_top))
    if c_top:
        layers.append(slab(cs.offset(-c_top), z1 - 0.01, z1))
    return Manifold.batch_hull(layers)


def tan_deg(a):
    return math.tan(math.radians(a))


def profiled(cs, points):
    """Hull of a convex outline offset by o at each height z, for (z, o) in points."""
    return Manifold.batch_hull([slab(cs.offset(o), z, z + 0.001) for z, o in points])


def dcyl(x, y, z0, z1, d, narrow_at, angle=DRAFT_CORE):
    """Cylinder of diameter d at one end, drafted narrower towards narrow_at ('top' / 'bottom')."""
    dn = d - 2 * (z1 - z0) * tan_deg(angle)
    return cyl(x, y, z0, z1, d, dn) if narrow_at == 'top' else cyl(x, y, z0, z1, dn, d)


def dbox(x0, y0, x1, y1, z0, z1, narrow_at='top', angle=DRAFT_CORE):
    """Box drafted narrower towards narrow_at."""
    d = min((z1 - z0) * tan_deg(angle), (x1 - x0) / 4, (y1 - y0) / 4)
    wide, narrow = rect(x0, y0, x1, y1), rect(x0 + d, y0 + d, x1 - d, y1 - d)
    zw, zn = (z0, z1 - 0.001) if narrow_at == 'top' else (z1 - 0.001, z0)
    return Manifold.batch_hull([slab(wide, zw, zw + 0.001), slab(narrow, zn, zn + 0.001)])


def gusset(x, y, r, ux, uy, length, height):
    """Triangular rib on the floor, from the surface of a round boss (radius r) outwards."""
    def strip(dist, z, t):                 # thin slab across the rib, t thick, at height z
        cx, cy = x + ux * dist, y + uy * dist
        hx, hy = (0.05, t / 2) if ux else (t / 2, 0.05)
        return slab(rect(cx - hx, cy - hy, cx + hx, cy + hy), z, z + 0.01)
    top_t = RIB_T - 2 * height * tan_deg(DRAFT_CORE)
    return Manifold.batch_hull([strip(r - 0.5, FLOOR - 0.01, RIB_T), strip(r - 0.5, FLOOR + height - 0.01, top_t),
                                strip(r + length, FLOOR - 0.01, RIB_T)])


def port_shape(w, h, r_bot, r_top):
    """Rectangle w x h centred on the origin, bottom corners r_bot, top corners r_top."""
    bottom = rrect(w, h / 2 + r_bot, r_bot, -w / 2, -h / 2)
    top = rrect(w, h / 2 + r_top, r_top, -w / 2, -r_top)
    return bottom + top


def hexagon(x, y, af):
    return CrossSection.circle(af / np.sqrt(3), 6).translate((x, y))


# ---------------------------------------------------------------- top-face graphics
def text_outline(s, size, cx, cy):
    """Bold sans-serif text as a CrossSection, centred on (cx, cy)."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    tp = TextPath((0, 0), s, size=size, prop=FontProperties(family='DejaVu Sans', weight='bold'))
    cs = CrossSection([p[:-1] for p in tp.to_polygons() if len(p) > 3], FillRule.EvenOdd)
    b = cs.bounds()
    return cs.translate((cx - (b[0] + b[2]) / 2, cy - (b[1] + b[3]) / 2))


def arc(cx, cy, r, w, a0, a1):
    """Annular sector of mid radius r and width w, from angle a0 to a1 (degrees), round ends."""
    ring = CrossSection.circle(r + w / 2) - CrossSection.circle(r - w / 2)
    a = np.radians(np.linspace(a0, a1, 64))
    wedge = CrossSection([np.vstack([[0, 0], np.c_[np.cos(a), np.sin(a)] * (r + w)])])
    out = ring ^ wedge
    for t in (np.radians(a0), np.radians(a1)):
        out += CrossSection.circle(w / 2).translate((r * np.cos(t), r * np.sin(t)))
    return out.translate((cx, cy))


def tap_graphic():
    """Outline round the NFC loop, contactless waves and 'TAP CARD'."""
    ax, ay, aw, al = ANTENNA
    w, l = aw + 4, al + 2
    frame = (rrect(w, l, 4, ax - w / 2, ay - l / 2)
             - rrect(w - 2.4, l - 2.4, 2.8, ax - w / 2 + 1.2, ay - l / 2 + 1.2))
    wx, wy = ax, ay - 3.0                       # waves rise from a dot above the text
    waves = CrossSection.circle(1.6).translate((wx, wy))
    for r in (4.5, 8.0, 11.5):
        waves += arc(wx, wy, r, 1.6, 45, 135)
    label = text_outline('TAP CARD', 6.0, ax, ay - 9.5)
    return frame + waves + label


def power_symbol(cx, cy, r=2.3, w=0.8):
    ring = arc(cx, cy, r, w, 120, 420)
    bar = rect(cx - w / 2, cy, cx + w / 2, cy + r + w / 2)
    return ring + bar + CrossSection.circle(w / 2).translate((cx, cy))


def button_marks():
    """Power symbol in a ring: the spot to press, right over the stem."""
    ring = CrossSection.circle(BUTTON_RING_R + 0.3) - CrossSection.circle(BUTTON_RING_R - 0.3)
    return power_symbol(*SW_POWER) + ring.translate(SW_POWER)


def top_marks():
    """Everything debossed into the top face (and printed in a second colour by the inlay)."""
    return tap_graphic() + button_marks()


# ---------------------------------------------------------------- shared pieces
def usb_cut():
    """Two-step stadium opening through the front wall, with a chamfered bezel."""
    def along_y(cs, y_out, y_in):          # extrude a section in the XZ plane from y_out to y_in
        return Manifold.extrude(cs, y_in - y_out).rotate((90, 0, 0)).translate((USB_X, y_in, Z_USB))
    y_face = -(GAP + WALL)
    up = Z_TOP - Z_USB + 1.0                  # far enough to break through the top

    def open_top(w, h, r):                    # rounded bottom corners, straight up and out
        return port_shape(w, h, r, r) + rect(-w / 2, 0, w / 2, up)
    plug = open_top(USB_PLUG_W, USB_PLUG_H, USB_PLUG_R)
    pocket = along_y(plug, y_face - 1.0, USB_STEP_Y)
    mouth = along_y(port_shape(USB_MOUTH_W, USB_MOUTH_H, *USB_MOUTH_R), USB_STEP_Y - 0.1, 0.3)
    c = USB_BEZEL
    bezel = Manifold.batch_hull([
        along_y(open_top(USB_PLUG_W + 2 * c, USB_PLUG_H + 2 * c, USB_PLUG_R + c), y_face - 0.5, y_face),
        along_y(plug, y_face + c - 0.001, y_face + c)])
    return pocket + mouth + bezel


def part_volumes(parts, grow=0.0, side=None):
    """Each part as a box from its face of the board to its height, clipped to the case inside."""
    inside = board_outline(GAP)
    out = []
    for ref, name, bottom, (x0, y0, x1, y1), h, _ in parts:
        if side is not None and bottom != (side == 'bottom'):
            continue
        cs = rect(x0 - grow, y0 - grow, x1 + grow, y1 + grow) ^ inside
        if bottom:
            out.append((ref, slab(cs, Z_BOARD_BOT - h - grow, Z_BOARD_BOT)))
        else:
            out.append((ref, slab(cs, Z_BOARD_TOP, Z_BOARD_TOP + h + grow)))
    return out


def lead_tails(parts, d, extra=0.0):
    """Through-hole leads sticking out of the far side of the board from each part."""
    out = Manifold()
    for _, _, bottom, _, _, tht in parts:
        for x, y in tht:
            if bottom:
                out += cyl(x, y, Z_BOARD_TOP, Z_BOARD_TOP + LEAD_TAIL + extra, d)
            else:
                out += cyl(x, y, Z_BOARD_BOT - LEAD_TAIL - extra, Z_BOARD_BOT, d)
    return out


# ---------------------------------------------------------------- parts
def make_base(parts=None):
    parts = board_parts() if parts is None else parts
    outer = board_outline(GAP + WALL)
    inner = board_outline(GAP)
    t = tan_deg(DRAFT_WALL)
    base = profiled(outer, [(0, -(Z_SPLIT * t) - CHAMFER_BED),
                            (CHAMFER_BED, -(Z_SPLIT - CHAMFER_BED) * t),
                            (Z_SPLIT - REVEAL, -REVEAL * t),
                            (Z_SPLIT - 0.001, -REVEAL)])
    # lip, then one drafted cut for the inside of the tray and the inner face of the lip
    dl = LIP_H * tan_deg(DRAFT_WALL)
    base += profiled(inner, [(Z_SPLIT - 0.01, LIP_T), (Z_SPLIT + LIP_H - 0.001, LIP_T - dl)])
    base -= profiled(inner, [(FLOOR, -(Z_SPLIT - FLOOR) * t), (Z_SPLIT + LIP_H + 0.01, (LIP_H + 0.01) * t)])

    # anything a rib or gusset may not touch
    keep_out = Manifold()
    for _, vol in part_volumes(parts, 0.3, side='bottom'):
        keep_out += vol
    keep_out += box(*BATT_BOX) + cyl(*MOTOR_XY, *MOTOR_Z, MOTOR_D + 0.6)

    def add_if_clear(m):
        nonlocal base
        if (m ^ keep_out).volume() < 1e-3:
            base += m

    # screw bosses: drafted, ribbed to nearby walls, gusseted elsewhere
    wall_x, wall_y = (-GAP, BOARD_W + GAP), (-GAP, BOARD_L + GAP)
    for x, y in MOUNT_HOLES:
        base += dcyl(x, y, FLOOR - 0.01, Z_BOARD_BOT, BOSS_D, 'top')
        rib_top = Z_BOARD_BOT - RIB_DROP
        for ux, uy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            wall = (wall_x[ux > 0] if ux else wall_y[uy > 0])
            reach = abs(wall - (x if ux else y)) - BOSS_D / 2
            if reach <= BOSS_RIB_REACH:
                a, b = sorted(((x if ux else y), wall + (ux or uy) * 0.5))
                rib = (dbox(a, y - RIB_T / 2, b, y + RIB_T / 2, FLOOR - 0.01, rib_top) if ux else
                       dbox(x - RIB_T / 2, a, x + RIB_T / 2, b, FLOOR - 0.01, rib_top))
                add_if_clear(rib)
            else:
                add_if_clear(gusset(x, y, BOSS_D / 2, ux, uy, *BOSS_GUSSET))

    # support posts: cored tubes with four gussets each
    for x, y in POSTS:
        base += dcyl(x, y, FLOOR - 0.01, Z_BOARD_BOT, POST_D, 'top')
        for ux, uy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            add_if_clear(gusset(x, y, POST_D / 2, ux, uy, *POST_GUSSET))

    # battery bay: a rib-grid seat, walls on three sides, corner legs on the lead end (+x)
    bx0, by0, bz0, bx1, by1, _ = BATT_BOX
    ix0, iy0, ix1, iy1 = bx0 - BAY_CLR, by0 - BAY_CLR, bx1 + BAY_CLR, by1 + BAY_CLR
    w, top = BAY_WALL, bz0 + BAY_WALL_H
    seat = [(ix0, iy0, ix1, iy0 + RIB_T), (ix0, iy1 - RIB_T, ix1, iy1),
            (ix0, (iy0 + iy1 - RIB_T) / 2, ix1, (iy0 + iy1 + RIB_T) / 2)]
    nx = max(1, round((ix1 - ix0) / SEAT_PITCH))
    for i in range(nx + 1):
        xr = ix0 + i * (ix1 - ix0 - RIB_T) / nx
        seat.append((xr, iy0, xr + RIB_T, iy1))
    for x0, y0, x1, y1 in seat:
        base += dbox(x0, y0, x1, y1, FLOOR - 0.01, bz0)
    for x0, y0, x1, y1 in [(ix0 - w, iy0 - w, ix0, iy1 + w), (ix0 - w, iy0 - w, ix1, iy0),
                           (ix0 - w, iy1, ix1, iy1 + w), (ix1, iy0 - w, ix1 + w, iy0 + BAY_LEG),
                           (ix1, iy1 - BAY_LEG, ix1 + w, iy1 + w)]:
        base += dbox(x0, y0, x1, y1, FLOOR - 0.01, top)

    # motor: a cored pedestal with a cup on top and a slot for the leads towards J4 (+y)
    mx, my = MOTOR_XY
    mz0 = MOTOR_Z[0]
    cup_d = MOTOR_D + 0.4 + 2 * MOTOR_CUP_WALL
    base += dcyl(mx, my, FLOOR - 0.01, mz0 + MOTOR_CUP, cup_d, 'top')

    dh = tan_deg(DRAFT_CORE)
    for x, y in MOUNT_HOLES:
        base -= dcyl(x, y, -0.1, Z_BOARD_BOT + 0.1, SCREW_D + 2 * (Z_BOARD_BOT + 0.2) * dh, 'bottom')
        top = nut_pocket_top(y)
        base -= profiled(hexagon(x, y, NUT_POCKET_AF), [(-0.1, 0.0), (top - 0.001, -(top + 0.1) * dh)])
    for x, y in POSTS:
        base -= dcyl(x, y, FLOOR + 1.0, Z_BOARD_BOT + 0.1, POST_BORE, 'bottom')
    base -= dcyl(mx, my, FLOOR + 1.0, mz0 + 0.01, PEDESTAL_BORE, 'bottom')
    base -= dcyl(mx, my, mz0, mz0 + MOTOR_CUP + 0.1, MOTOR_D + 0.4, 'bottom')
    base -= dbox(mx - 1.25, my, mx + 1.25, my + MOTOR_D, mz0 + 0.5, mz0 + MOTOR_CUP + 0.1, 'bottom')
    for ref, name, bottom, (x0, y0, x1, y1), h, _ in parts:
        if bottom and 'JST_XA' in name:
            floor_area = inner.offset(-(Z_SPLIT - FLOOR) * t - 0.3)   # clear of the drafted wall
            for hx, hy in MOUNT_HOLES:                                  # and of the bosses' feet
                floor_area -= CrossSection.circle(BOSS_D / 2 + 0.3).translate((hx, hy))
            base -= (dbox(x0 - 0.5, y0 - 0.5, x1 + 0.5, y1 + 0.5, FLOOR - J2_POCKET, FLOOR + 0.1, 'bottom')
                     ^ slab(floor_area, FLOOR - J2_POCKET - 1, FLOOR + 1))
    base -= usb_cut()
    return base


def make_lid(parts=None):
    outer = board_outline(GAP + WALL)
    inner = board_outline(GAP)
    t = tan_deg(DRAFT_WALL)
    h = Z_TOP - Z_SPLIT
    lid = profiled(outer, [(Z_SPLIT, -REVEAL),
                           (Z_SPLIT + REVEAL, -REVEAL * t),
                           (Z_TOP - CHAMFER_TOP, -(h - CHAMFER_TOP) * t),
                           (Z_TOP - 0.001, -h * t - CHAMFER_TOP)])
    # inner wall nominal at the ceiling, opening out towards the rim (never into the board area)
    lid -= profiled(inner, [(Z_SPLIT - 1, (Z_CEIL - Z_SPLIT + 1) * t), (Z_CEIL - 0.001, 0.0)])
    dl = (LIP_H + 0.2) * tan_deg(DRAFT_WALL)
    lid -= (profiled(inner, [(Z_SPLIT - 1, LIP_T + LIP_CLR + dl), (Z_SPLIT + LIP_H + 0.2, LIP_T + LIP_CLR - dl)])
            - slab(inner, Z_SPLIT - 2, Z_SPLIT + LIP_H + 1))

    # hanging features taper towards their tips (the core pulls down, away from the ceiling)
    for x, y in MOUNT_HOLES:
        lid += dcyl(x, y, Z_BOARD_TOP, Z_CEIL + 0.01, COLUMN_D, 'bottom')
    for x, y in STATUS_LEDS + CHARGE_LEDS:
        lid += dcyl(x, y, Z_BOARD_TOP + LED_TOP + 0.4, Z_CEIL + 0.01, LED_PIPE_D, 'bottom')
    for x, y in (SW_RESET, SW_BOOT0):
        lid += dcyl(x, y, Z_BOARD_TOP + SW_TOP + 0.8, Z_CEIL + 0.01, PIN_TUBE_D, 'bottom')

    # POWER: a skirt round the slot, thin the tab from inside, add the stem, cut the slot
    tx0, ty0, tx1, ty1 = TAB
    g, k = TAB_SLOT, SKIRT_T
    z_skirt = Z_BOARD_TOP + SW_TOP + 0.4
    into_wall = 0.6                        # pieces next to a wall run into it
    for x0, y0, x1, y1 in [(min(tx0 - g - k, -GAP - into_wall), ty0 - g - k, tx0 - g, ty1),
                           (tx1 + g, ty0 - g - k, tx1 + g + k, ty1),
                           (min(tx0 - g - k, -GAP - into_wall), min(ty0 - g - k, -GAP - into_wall),
                            tx1 + g + k, ty0 - g)]:
        lid += dbox(x0, y0, x1, y1, z_skirt, Z_CEIL + 0.01, 'bottom')
    lid -= dbox(tx0 - g, ty0 - g, tx1 + g, ty1, Z_CEIL - 0.1, Z_TOP - TAB_T, 'top')
    lid += dcyl(*SW_POWER, Z_BOARD_TOP + SW_TOP + STEM_CLR, Z_TOP - TAB_T + 0.01, STEM_D, 'bottom')
    for x0, y0, x1, y1 in [(tx0 - g, ty0, tx0, ty1), (tx1, ty0, tx1 + g, ty1), (tx0 - g, ty0 - g, tx1 + g, ty0)]:
        lid -= dbox(x0, y0, x1, y1, Z_CEIL - 0.1, Z_TOP + 0.1, 'bottom', angle=DRAFT_CORE)
    for cx in (tx0 - g / 2, tx1 + g / 2):  # round relief at each end of the hinge
        lid -= dcyl(cx, ty1, Z_CEIL - 0.1, Z_TOP + 0.1, g + 2 * TOP * tan_deg(DRAFT_CORE), 'bottom')

    dh = 2 * (Z_TOP - Z_BOARD_TOP) * tan_deg(DRAFT_CORE)
    for x, y in STATUS_LEDS + CHARGE_LEDS:
        lid -= cyl(x, y, Z_BOARD_TOP, Z_TOP + 0.1, LED_BORE + dh, LED_BORE)
    for x, y in (SW_RESET, SW_BOOT0):
        lid -= cyl(x, y, Z_BOARD_TOP, Z_TOP + 0.1, PIN_BORE + dh, PIN_BORE)
    for x, y in MOUNT_HOLES:
        lid -= cyl(x, y, Z_SPLIT - 1, Z_TOP + 0.1, SCREW_D + dh, SCREW_D)
        lid -= cyl(x, y, Z_TOP - (CSK_D - SCREW_D) / 2, Z_TOP + 0.01, SCREW_D, CSK_D)
    lid -= usb_cut()
    lid -= slab(top_marks(), Z_TOP - MARK_DEPTH, Z_TOP + 0.1)
    return lid


def make_inlay():
    """The debossed marks as a solid, MARK_DEPTH thick, to print in a second colour."""
    return slab(top_marks().offset(-0.05), Z_TOP - MARK_DEPTH, Z_TOP)


# ---------------------------------------------------------------- bought parts, as fitted
def battery_model():
    """803040 pouch with rounded edges, and its two leads leaving the +x end towards J2."""
    x0, y0, z0, x1, y1, z1 = BATT_BOX
    pouch = slab(rrect(x1 - x0, y1 - y0, 1.5, x0, y0), z0, z1)
    zc = (z0 + z1) / 2
    leads = Manifold()
    for y in BATT_LEADS_Y:
        leads += Manifold.cylinder(BATT_LEAD_L, 0.6).rotate((0, 90, 0)).translate((x1 - 0.5, y, zc))
    return pouch + leads


def motor_model():
    """Coin motor and its two leads, out through the cup's slot towards J4."""
    mx, my = MOTOR_XY
    z0, z1 = MOTOR_Z
    body = cyl(mx, my, z0, z1, MOTOR_D)
    leads = Manifold()
    for dx in (-0.6, 0.6):
        leads += (Manifold.cylinder(MOTOR_D / 2 + 3.0, 0.3).rotate((-90, 0, 0))
                  .translate((mx + dx, my, z0 + 1.0)))
    return body + leads


# ---------------------------------------------------------------- fit check
def fit_check(base, lid, parts):
    """Rough models of the board, its parts, leads, battery and motor; none may touch the case."""
    holes = Manifold()
    for x, y in MOUNT_HOLES:
        holes += cyl(x, y, Z_BOARD_BOT - 1, Z_BOARD_TOP + 1, MOUNT_HOLE_D)
    things = [('board', slab(board_outline(0), Z_BOARD_BOT, Z_BOARD_TOP) - holes)]
    things += part_volumes(parts)
    things.append(('leads', lead_tails(parts, 1.2)))
    battery = battery_model()
    motor = motor_model()
    things += [('battery', battery), ('motor', motor)]

    problems = []
    for name, m in things:
        for part_name, part in (('base', base), ('lid', lid)):
            v = (m ^ part).volume()
            if v > 1e-3:
                problems.append(f'{name} hits the {part_name} ({v:.2f} mm^3)')
    for name, m in things[:-2]:
        for other, o in (('battery', battery), ('motor', motor)):
            v = (m ^ o).volume()
            if v > 1e-3:
                problems.append(f'{other} hits {name} ({v:.2f} mm^3)')
    v = (base ^ lid).volume()
    if v > 1e-3:
        problems.append(f'base and lid overlap ({v:.2f} mm^3)')
    for x, y in MOUNT_HOLES:
        tip = hole_top(y) - screw_length(y)
        if tip < 0 or nut_pocket_top(y) > Z_BOARD_BOT - 0.4:
            problems.append(f'no M3 screw length fits the hole at ({x}, {y})')
    return problems


def triangles(m):
    """(N, 3, 3) triangle corners of a Manifold."""
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties, dtype=np.float32)[:, :3]
    return v[np.asarray(mesh.tri_verts, dtype=np.int64)]


def read_stl(path):
    """(N, 3, 3) triangle corners from an ASCII or binary STL."""
    data = open(path, 'rb').read()
    n = struct.unpack('<I', data[80:84])[0] if len(data) >= 84 else 0
    if len(data) == 84 + 50 * n:
        rec = np.frombuffer(data[84:], dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))
        return rec['v'].reshape(-1, 3, 3).astype(np.float32)
    nums = re.findall(rb'vertex\s+(\S+)\s+(\S+)\s+(\S+)', data)
    return np.array(nums, dtype=np.float32).reshape(-1, 3, 3)


def write_stl(path, *items):
    """Binary STL of any mix of Manifolds and (N, 3, 3) triangle arrays, as separate bodies."""
    tri = np.concatenate([triangles(m) if isinstance(m, Manifold) else m for m in items])
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(tri), dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))
    rec['n'] = n
    rec['v'] = tri.reshape(-1, 9)
    with open(path, 'wb') as f:
        f.write(b'Attendance Management System enclosure'.ljust(80, b' '))
        f.write(struct.pack("<I", len(tri)))
        f.write(rec.tobytes())


def main():
    out = os.path.join(HERE, 'stl')
    os.makedirs(out, exist_ok=True)
    parts = board_parts()
    base, lid, inlay = make_base(parts), make_lid(parts), make_inlay()
    for name, m in (('base', base), ('lid', lid), ('inlay', inlay)):
        assert m.status().name == 'NoError' and not m.is_empty(), name

    problems = fit_check(base, lid, parts)
    for p in problems:
        print('FIT:', p)

    # bought parts in their fitted position, and everything together for a look
    battery, motor = battery_model(), motor_model()
    write_stl(os.path.join(out, 'battery.stl'), battery)
    write_stl(os.path.join(out, 'motor.stl'), motor)
    everything = [base, lid, inlay, battery, motor]
    board_stl = os.path.join(out, 'pcb.stl')
    if os.path.exists(board_stl):
        board = read_stl(board_stl)
        board[:, :, 2] += Z_BOARD_BOT
        everything.append(board)
    else:
        print('no stl/pcb.stl yet (run export_pcb.py): assembly.stl has no board')
    write_stl(os.path.join(out, 'assembly.stl'), *everything)
    # print orientations: base as it sits, lid and inlay top face down, all on z = 0
    write_stl(os.path.join(out, 'base.stl'), base)
    write_stl(os.path.join(out, 'lid.stl'), lid.rotate((180, 0, 0)).translate((0, 0, Z_TOP)))
    write_stl(os.path.join(out, 'lid_inlay.stl'), inlay.rotate((180, 0, 0)).translate((0, 0, Z_TOP)))

    bb = base.bounding_box()
    print(f'outside: {bb[3] - bb[0]:.1f} x {bb[4] - bb[1]:.1f} x {Z_TOP:.1f} mm')
    print(f'card to antenna: {LID_H:.1f} mm; board underside at z = {Z_BOARD_BOT:.1f}, '
          f'top (split) at {Z_BOARD_TOP:.1f}, lid ceiling at {Z_CEIL:.1f}')
    print(f'colour change for the marks at {MARK_DEPTH:.1f} mm print height')
    for x, y in MOUNT_HOLES:
        print(f'screw at ({x}, {y}): M3x{screw_length(y)} countersunk, '
              f'nut pocket {nut_pocket_top(y):.1f} mm deep')
    for name, m in (('base', base), ('lid', lid), ('inlay', inlay)):
        print(f'{name}: {m.volume() / 1000:.1f} cm^3, {m.num_tri()} triangles')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
