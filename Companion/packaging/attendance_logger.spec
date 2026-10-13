# PyInstaller spec for the Attendance Logger, shared by build_linux.sh and build_windows.bat.
# Builds a one-folder app, dist/AttendanceLogger/, from attendance_qt.py. The icon comes from make_icons.py,
# written to build/icons/ before PyInstaller runs.
import os
import sys

HERE = os.path.abspath(SPECPATH)
SRC = os.path.dirname(HERE)
ICONS = os.path.join(SRC, "build", "icons")
WINDOWS = sys.platform == "win32"

a = Analysis(
    [os.path.join(SRC, "attendance_qt.py")],
    pathex=[SRC],
    hiddenimports=["attendance_app", "attendance_db", "app_helpers", "report_pages"],
    # Only QtCore, QtGui and QtWidgets are used; keep the rest of Qt and the stdlib GUI out.
    excludes=["tkinter", "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtWebEngineCore",
              "PySide6.QtWebEngineWidgets", "PySide6.QtMultimedia", "PySide6.Qt3DCore", "PySide6.QtPdf"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AttendanceLogger",
    console=False,
    icon=os.path.join(ICONS, "icon.ico") if WINDOWS else None,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="AttendanceLogger", upx=False)
