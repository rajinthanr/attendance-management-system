"""Draw the routed board from the .kicad_pcb file: soldermask green, copper, pads, vias."""
import math
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection, PatchCollection
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle, Polygon

PCB = r"D:\attendance_management\Attendance-Management-System\PCB\Attendance Management System.kicad_pcb"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img")
os.makedirs(OUT, exist_ok=True)

TOK = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')


def parse(text):
    stack = [[]]
    for m in TOK.finditer(text):
        t = m.group(0)
        if t == "(":
            stack.append([])
        elif t == ")":
            x = stack.pop()
            stack[-1].append(x)
        elif t.startswith('"'):
            stack[-1].append(("s", t[1:-1]))
        else:
            try:
                stack[-1].append(float(t))
            except ValueError:
                stack[-1].append(t)
    return stack[0][0]


def kids(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def kid(node, name):
    k = kids(node, name)
    return k[0] if k else None


def sval(x):
    return x[1] if isinstance(x, tuple) else x


def layer_of(node):
    l = kid(node, "layer")
    return sval(l[1]) if l else None


def tf(fx, fy, fr, px, py):
    a = math.radians(fr)
    return fx + px * math.cos(a) + py * math.sin(a), fy - px * math.sin(a) + py * math.cos(a)


tree = parse(open(PCB, encoding="utf-8").read())

segs = {"F.Cu": [], "B.Cu": []}
vias = []
for s in kids(tree, "segment"):
    st, en, w, lay = kid(s, "start"), kid(s, "end"), kid(s, "width"), layer_of(s)
    if lay in segs:
        segs[lay].append(((st[1], st[2]), (en[1], en[2]), w[1]))
for v in kids(tree, "via"):
    at, size = kid(v, "at"), kid(v, "size")
    vias.append((at[1], at[2], size[1]))

pours = {"F.Cu": [], "B.Cu": []}
for z in kids(tree, "zone"):
    for fp in kids(z, "filled_polygon"):
        lay = layer_of(fp)
        pts = kid(fp, "pts")
        coords = []
        for xy in kids(pts, "xy"):
            coords.append((xy[1], xy[2]))
        if lay in pours and len(coords) > 2:
            pours[lay].append(coords)

pads, fpgfx, labels = [], [], {}
for f in kids(tree, "footprint"):
    at = kid(f, "at")
    fx, fy = at[1], at[2]
    fr = at[3] if len(at) > 3 else 0.0
    side = layer_of(f)
    ref = None
    for p in kids(f, "property"):
        if sval(p[1]) == "Reference":
            ref = sval(p[2])
    labels[ref] = (fx, fy)
    for pad in kids(f, "pad"):
        lay = kid(pad, "layers")
        lays = [sval(x) for x in lay[1:]] if lay else []
        if not any(l in ("F.Cu", "*.Cu") for l in lays) and side == "F.Cu":
            continue
        pat = kid(pad, "at")
        size = kid(pad, "size")
        if not pat or not size:
            continue
        x, y = tf(fx, fy, fr, pat[1], pat[2])
        ang = pat[3] if len(pat) > 3 else fr
        w, h = size[1], size[2]
        if round(ang) % 180 == 90:
            w, h = h, w
        shape = pad[3] if len(pad) > 3 else "rect"
        drill = kid(pad, "drill")
        pads.append((x, y, w, h, shape, drill[1] if drill and isinstance(drill[1], float) else None))
    for kind in ("fp_line", "fp_arc"):
        for g in kids(f, kind):
            if layer_of(g) != "F.Cu":
                continue
            st, en = kid(g, "start"), kid(g, "end")
            w = kid(g, "width") or kid(kid(g, "stroke"), "width") if kid(g, "stroke") else kid(g, "width")
            if kind == "fp_line" and st and en:
                a = tf(fx, fy, fr, st[1], st[2]); b = tf(fx, fy, fr, en[1], en[2])
                fpgfx.append((a, b, (kid(kid(g, "stroke"), "width")[1] if kid(g, "stroke") else 0.2)))
            elif kind == "fp_arc":
                mid = kid(g, "mid")
                if st and en and mid:
                    pts3 = [tf(fx, fy, fr, p[1], p[2]) for p in (st, mid, en)]
                    fpgfx.append((pts3, None, (kid(kid(g, "stroke"), "width")[1] if kid(g, "stroke") else 0.2)))

# board outline
edge_lines = []
for kind in ("gr_line", "gr_arc"):
    for g in kids(tree, kind):
        if layer_of(g) != "Edge.Cuts":
            continue
        st, en = kid(g, "start"), kid(g, "end")
        if kind == "gr_line":
            edge_lines.append(((st[0 + 1], st[2]), (en[1], en[2])))
xs = [p[0] for l in edge_lines for p in l]
ys = [p[1] for l in edge_lines for p in l]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
print("board", x0, y0, x1, y1, "segments", {k: len(v) for k, v in segs.items()}, "vias", len(vias),
      "pads", len(pads), "pours", {k: len(v) for k, v in pours.items()}, "fp gfx", len(fpgfx))


def arc_pts(a, m, b, n=24):
    # circle through three points
    (x1_, y1_), (x2_, y2_), (x3_, y3_) = a, m, b
    d = 2 * (x1_ * (y2_ - y3_) + x2_ * (y3_ - y1_) + x3_ * (y1_ - y2_))
    if abs(d) < 1e-9:
        return [a, b]
    ux = ((x1_**2 + y1_**2) * (y2_ - y3_) + (x2_**2 + y2_**2) * (y3_ - y1_) + (x3_**2 + y3_**2) * (y1_ - y2_)) / d
    uy = ((x1_**2 + y1_**2) * (x3_ - x2_) + (x2_**2 + y2_**2) * (x1_ - x3_) + (x3_**2 + y3_**2) * (x2_ - x1_)) / d
    r = math.hypot(x1_ - ux, y1_ - uy)
    a1, a2, a3 = (math.atan2(p[1] - uy, p[0] - ux) for p in (a, m, b))
    # sweep from a1 to a3 passing a2
    def norm(t):
        return (t + 2 * math.pi) % (2 * math.pi)
    s2, s3 = norm(a2 - a1), norm(a3 - a1)
    sweep = s3 if s2 < s3 else s3 - 2 * math.pi
    return [(ux + r * math.cos(a1 + sweep * i / n), uy + r * math.sin(a1 + sweep * i / n)) for i in range(n + 1)]


def draw(top=True, labels_on=True, size=(7.6, 10.4)):
    fig = plt.figure(figsize=size, dpi=220)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_aspect("equal")
    ax.axis("off")
    mask, mask_dark = "#1f7a52", "#17603f"
    board = FancyBboxPatch((x0 + 2, y0 + 2), (x1 - x0) - 4, (y1 - y0) - 4, boxstyle="round,pad=2,rounding_size=2",
                           fc=mask, ec="#0e4a30", lw=1.2, zorder=1)
    ax.add_patch(board)
    # pours under the mask: slightly lighter than the board
    for coords in pours["F.Cu"]:
        ax.add_patch(Polygon(coords, closed=True, fc="#2f9a69", ec="none", alpha=0.9, zorder=2))
    # back copper, faint
    ax.add_collection(LineCollection([(a, b) for a, b, w in segs["B.Cu"]], colors="#1a6a47", linewidths=[max(w * 2.6, 0.6) for a, b, w in segs["B.Cu"]], zorder=2, alpha=0.7))
    # front traces: copper under mask, lighter green
    ax.add_collection(LineCollection([(a, b) for a, b, w in segs["F.Cu"]], colors="#6fd0a0", linewidths=[max(w * 2.6, 0.5) for a, b, w in segs["F.Cu"]], zorder=3, capstyle="round"))
    # antenna coil and other F.Cu graphics in footprints
    for a, b, w in fpgfx:
        if b is None:
            pts = arc_pts(*a)
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#e9c46a", lw=max(w * 2.6, 0.8), solid_capstyle="round", zorder=3)
        else:
            ax.plot([a[0], b[0]], [a[1], b[1]], color="#e9c46a", lw=max(w * 2.6, 0.8), solid_capstyle="round", zorder=3)
    # pads: bare gold
    for x, y, w, h, shape, drill in pads:
        if shape == "circle":
            ax.add_patch(Circle((x, y), max(w, h) / 2, fc="#e9c46a", ec="none", zorder=4))
        elif shape == "oval":
            ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=%f" % (min(w, h) / 2), fc="#e9c46a", ec="none", zorder=4))
        else:
            ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc="#e9c46a", ec="none", zorder=4))
        if drill:
            ax.add_patch(Circle((x, y), drill / 2, fc="#0b2f20", ec="none", zorder=5))
    for x, y, d in vias:
        ax.add_patch(Circle((x, y), d / 2, fc="#cfe8d8", ec="#0b2f20", lw=0.3, zorder=5))
    ax.set_xlim(x0 - 3, x1 + 3)
    ax.set_ylim(y1 + 3, y0 - 3)     # KiCad y points down
    return fig, ax


if __name__ == "__main__":
    fig, ax = draw()
    fig.savefig(os.path.join(OUT, "pcb_top.png"), transparent=True)
    print("saved")
    print({k: labels.get(k) for k in ("U4", "U5", "J1", "J2", "U2", "U3", "AE3", "Y1", "Y2", "SW3", "J4", "Q1", "J3", "J7", "J5", "U1", "J6")})
