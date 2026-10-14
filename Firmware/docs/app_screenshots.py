#!/usr/bin/env python3
"""Screenshots of the companion app for the easy guide, taken off-screen from its demo data.

Run with the Python that has PySide6 (the Companion's .venv):
    QT_QPA_PLATFORM=offscreen ../../Companion/.venv/bin/python app_screenshots.py
Writes guide_img/app_*.png next to this script.
"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPANION = HERE.parents[1] / "Companion"
OUT = HERE / "guide_img"
sys.path.insert(0, str(COMPANION))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import attendance_qt as Q          # noqa: E402
import attendance_app as A         # noqa: E402
import attendance_db as D          # noqa: E402
from PySide6.QtWidgets import QApplication   # noqa: E402


def settle(seconds=1.5):
    end = time.time() + seconds
    while time.time() < end:
        QApplication.processEvents()
        time.sleep(0.02)


def save(widget, name):
    widget.grab().save(str(OUT / name))
    print("wrote", OUT / name)


def main():
    OUT.mkdir(exist_ok=True)
    data_dir = tempfile.mkdtemp(prefix="guide-data-")
    device = tempfile.mkdtemp(prefix="guide-device-")
    try:
        A.make_demo(data_dir, device)
        qapp = QApplication.instance() or QApplication(sys.argv[:1])
        qapp.setStyle("Fusion")
        qapp.setStyleSheet(Q.style_sheet())
        db = D.Database(os.path.join(data_dir, "attendance.db"))
        win = Q.MainWindow(A.App(db, device, data_dir), data_dir, demo=False)
        win.resize(1280, 800)
        win.show()
        settle(3)
        save(win, "app_lectures.png")

        win.nav.setCurrentRow(1)
        settle()
        save(win, "app_students.png")

        tap = Q.TapDialog(win, "Tap a card", lambda card: None)
        tap.show()
        settle()
        save(tap, "app_tap.png")
        tap.closed = True
        tap.reject()

        reg = Q.StudentDialog(win, None, {"card_id": 183769758, "student_no": "EN/22/045",
                                          "name": "Nimali Wickramasinghe"})
        reg.show()
        settle(0.3)
        reg.e_card.setCursorPosition(0)
        reg.e_card.clearFocus()
        settle(0.5)
        save(reg, "app_register.png")
        reg.reject()

        win.nav.setCurrentRow(0)
        settle()
        win.shutdown()
        win.close()
        db.close()
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)
        shutil.rmtree(device, ignore_errors=True)


if __name__ == "__main__":
    main()
