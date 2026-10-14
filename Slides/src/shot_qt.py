"""Screenshots of the Qt companion app on demo data (grabs the widget, no screen capture)."""
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, r"D:\attendance_management\Attendance-Management-System\Companion")
os.environ.setdefault("ATTENDANCE_VENV_TRIED", "1")

import attendance_app as A  # noqa: E402
import attendance_db as D  # noqa: E402
import attendance_qt as Q  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img")
data = tempfile.mkdtemp(prefix="deck-data-")
dev = tempfile.mkdtemp(prefix="deck-dev-")
A.make_demo(data, dev)
db = D.Database(os.path.join(data, "attendance.db"))

app = QApplication.instance() or QApplication(sys.argv[:1])
app.setStyle("Fusion")
app.setStyleSheet(Q.style_sheet())
win = Q.MainWindow(A.App(db, dev, data), data, demo=True)
win.resize(1180, 760)
win.show()


def pump(sec):
    end = time.time() + sec
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


pump(4)
print([n for n in dir(win) if n.startswith(("show_", "goto", "page", "select"))][:20])
win.grab().save(os.path.join(OUT, "app_lectures.png"))
for name in ("go_students", "show_students", "open_students"):
    if hasattr(win, name):
        getattr(win, name)()
        break
else:
    try:
        win.pages.setCurrentIndex(1)
    except Exception as e:
        print("no page switch", e)
pump(1.5)
win.grab().save(os.path.join(OUT, "app_students.png"))
win.shutdown()
db.close()
shutil.rmtree(data, ignore_errors=True)
shutil.rmtree(dev, ignore_errors=True)
print("ok")
