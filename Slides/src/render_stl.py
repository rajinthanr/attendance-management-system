"""Tiny z-buffer renderer for the enclosure STLs (numpy only), transparent background."""
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageFilter

STL = r"D:\attendance_management\Attendance-Management-System\Enclosure\stl"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img")
os.makedirs(OUT, exist_ok=True)


def load(name):
    b = open(os.path.join(STL, name + ".stl"), "rb").read()
    n = struct.unpack("<I", b[80:84])[0]
    a = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return a["v"].reshape(-1, 3, 3).astype(np.float64)


def rot(az, el):
    """World (x right, y into the screen along the board, z up) to camera."""
    a, e = np.radians(az), np.radians(el)
    rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    return rx @ rz


def render(parts, az=-35, el=32, size=(1400, 1000), ss=2, margin=0.06, light=(-0.45, -0.55, 0.7), shadow=True):
    """parts: list of (triangles Nx3x3, rgb tuple). Returns an RGBA PIL image."""
    R = rot(az, el)
    W, H = size[0] * ss, size[1] * ss
    allv = np.concatenate([p[0].reshape(-1, 3) for p in parts])
    c = (allv.min(0) + allv.max(0)) / 2
    cam_all = (allv - c) @ R.T
    # camera space: x right, y = depth axis (away), z up on screen
    xs, zs = cam_all[:, 0], cam_all[:, 2]
    scale = min(W * (1 - 2 * margin) / (xs.max() - xs.min()), H * (1 - 2 * margin) / (zs.max() - zs.min()))
    cx, cz = (xs.max() + xs.min()) / 2, (zs.max() + zs.min()) / 2
    L = np.array(light, float)
    L = L / np.linalg.norm(L)
    Lc = R @ L
    color = np.zeros((H, W, 3), np.float64)
    zbuf = np.full((H, W), np.inf)
    mask = np.zeros((H, W), bool)
    for tris, rgb in parts:
        v = (tris - c) @ R.T
        n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
        ln = np.linalg.norm(n, axis=1)
        ln[ln == 0] = 1
        n = n / ln[:, None]
        # camera looks along +y (depth); keep faces whose normal points toward the camera (-y)
        facing = n[:, 1] < 0.02
        base = np.array(rgb, float)
        px = (v[:, :, 0] - cx) * scale + W / 2
        py = H / 2 - (v[:, :, 2] - cz) * scale
        dep = v[:, :, 1]
        for i in np.nonzero(facing)[0]:
            x0, x1, x2 = px[i]
            y0, y1, y2 = py[i]
            minx = max(int(np.floor(min(x0, x1, x2))), 0)
            maxx = min(int(np.ceil(max(x0, x1, x2))), W - 1)
            miny = max(int(np.floor(min(y0, y1, y2))), 0)
            maxy = min(int(np.ceil(max(y0, y1, y2))), H - 1)
            if minx > maxx or miny > maxy:
                continue
            det = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(det) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(minx, maxx + 1) + 0.5, np.arange(miny, maxy + 1) + 0.5)
            l0 = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / det
            l1 = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / det
            l2 = 1 - l0 - l1
            inside = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
            if not inside.any():
                continue
            d = l0 * dep[i, 0] + l1 * dep[i, 1] + l2 * dep[i, 2]
            sub = zbuf[miny:maxy + 1, minx:maxx + 1]
            upd = inside & (d < sub)
            if not upd.any():
                continue
            lam = max(0.0, float(n[i] @ Lc))
            hl = max(0.0, float(n[i] @ np.array([0.0, -1.0, 0.0])))      # a soft headlight
            shade = 0.62 + 0.36 * lam + 0.10 * hl
            col = np.clip(base * shade + 0.06 * lam ** 8 * 255, 0, 255)
            sub[upd] = d[upd]
            color[miny:maxy + 1, minx:maxx + 1][upd] = col
            mask[miny:maxy + 1, minx:maxx + 1][upd] = True
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = color.astype(np.uint8)
    rgba[..., 3] = (mask * 255).astype(np.uint8)
    img = Image.fromarray(rgba, "RGBA")
    if shadow:
        a = np.array(img)[..., 3] > 0
        ys, xs_ = np.nonzero(a)
        if len(xs_):
            sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            arr = np.zeros((H, W), np.uint8)
            y_base = ys.max() - int(0.02 * H)
            xl, xr = xs_.min(), xs_.max()
            yy, xx = np.mgrid[0:H, 0:W]
            ell = (((xx - (xl + xr) / 2) / ((xr - xl) * 0.52)) ** 2 + ((yy - y_base) / (H * 0.035)) ** 2) < 1
            arr[ell] = 70
            shimg = Image.fromarray(arr, "L").filter(ImageFilter.GaussianBlur(H * 0.012))
            sh.putalpha(shimg)
            sh.paste(img, (0, 0), img)
            img = sh
    return img.resize(size, Image.LANCZOS)


PEACH = (244, 166, 134)
TEAL = (96, 170, 146)
DARK = (28, 110, 78)

if __name__ == "__main__":
    asm = load("assembly")
    base = load("base")
    lid = load("lid").copy()
    btn = load("button").copy()
    # hero: the finished case
    render([(asm, PEACH)], az=-32, el=30, size=(1500, 1100)).save(os.path.join(OUT, "case_hero.png"))
    # lid back into its mounting orientation (it is printed upside down)
    lid[:, :, 1] *= -1
    lid[:, :, 2] = 14.0 - lid[:, :, 2]
    lid[:, :, 2] += 13.5
    b2 = base.copy()
    l2 = lid.copy()
    l2[:, :, 2] += 22
    btn2 = btn.copy()
    btn2[:, :, 0] += 72
    btn2[:, :, 1] += 40
    render([(b2, PEACH), (l2, TEAL), (btn2, DARK)], az=-32, el=26, size=(1600, 1100)).save(os.path.join(OUT, "case_exploded.png"))
    print("done")
