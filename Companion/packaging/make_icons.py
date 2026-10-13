#!/usr/bin/env python3
"""
Writes the app icon for the installers: icon.png (256 px, Linux) and icon.ico (16-256 px, Windows), drawn the
same way as app_icon() in attendance_qt.py (an indigo tile with a white check mark), so no image files are kept
in the repository.

    python make_icons.py OUT_DIR
"""
import os
import struct
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen  # noqa: E402

import app_helpers as H  # noqa: E402


def draw(size):
    """The 64 px drawing of app_icon(), scaled to size."""
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 64.0, size / 64.0)
    p.setBrush(QColor(H.PAL["indigo"]))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(2, 2, 60, 60, 14, 14)
    pen = QPen(QColor("white"), 7)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPolyline([QPointF(17, 33), QPointF(28, 44), QPointF(47, 22)])
    p.end()
    return img


def png_bytes(img):
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    buf.close()
    return bytes(data)


def write_ico(path, sizes):
    """An ICO holding one PNG per size (Windows Vista and later read PNG entries)."""
    pngs = [png_bytes(draw(s)) for s in sizes]
    out = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    for s, data in zip(sizes, pngs):
        out += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    with open(path, "wb") as f:
        f.write(out + b"".join(pngs))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])  # noqa: F841 (QPainter needs one)
    draw(256).save(os.path.join(out, "icon.png"), "PNG")
    write_ico(os.path.join(out, "icon.ico"), (16, 24, 32, 48, 64, 128, 256))
    print("Icons in %s" % out)


if __name__ == "__main__":
    main()
