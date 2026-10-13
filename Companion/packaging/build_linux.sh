#!/bin/sh
# Builds the Attendance Logger for Linux: a standalone app (PyInstaller, no Python needed on the target) packed as
#     dist/attendance-logger_<version>_<arch>.deb      install:  sudo apt install ./attendance-logger_*.deb
#     dist/attendance-logger-<version>-linux-<arch>.tar.gz   unpack anywhere and run AttendanceLogger
# Run from anywhere:  sh packaging/build_linux.sh   (VERSION=1.2.0 sh packaging/build_linux.sh to set the version)
# Needs python3 (with venv) and dpkg-deb. The build venv goes in build/venv, separate from .venv.
# The app runs on distributions with the same or a newer glibc than the build machine's.
set -eu
umask 022
VERSION=${VERSION:-1.0.0}
NAME=attendance-logger
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=$(dirname "$HERE")
BUILD=$SRC/build
DIST=$SRC/dist
cd "$SRC"
mkdir -p "$DIST"

if [ ! -x "$BUILD/venv/bin/python" ]; then
    python3 -m venv "$BUILD/venv"
fi
PY=$BUILD/venv/bin/python
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet "PySide6-Essentials>=6.5" pyinstaller

"$PY" packaging/make_icons.py "$BUILD/icons"
"$PY" -m PyInstaller --noconfirm --clean --distpath "$BUILD/linux-app" --workpath "$BUILD/linux-work" \
    packaging/attendance_logger.spec

ARCH=$(dpkg --print-architecture 2>/dev/null || uname -m)

# Portable archive
tar -C "$BUILD/linux-app" -czf "$DIST/$NAME-$VERSION-linux-$ARCH.tar.gz" AttendanceLogger

# .deb: the app in /opt, a launcher in /usr/bin, a menu entry and an icon
ROOT=$BUILD/deb
rm -rf "$ROOT"
mkdir -p "$ROOT/DEBIAN" "$ROOT/opt/$NAME" "$ROOT/usr/bin" "$ROOT/usr/share/applications" \
    "$ROOT/usr/share/icons/hicolor/256x256/apps"
cp -a "$BUILD/linux-app/AttendanceLogger/." "$ROOT/opt/$NAME/"
ln -s "/opt/$NAME/AttendanceLogger" "$ROOT/usr/bin/$NAME"
cp "$BUILD/icons/icon.png" "$ROOT/usr/share/icons/hicolor/256x256/apps/$NAME.png"
cat > "$ROOT/usr/share/applications/$NAME.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Attendance Logger
Comment=Import taps from the RFID attendance logger, register cards and export lecture lists
Exec=/opt/$NAME/AttendanceLogger %U
Icon=$NAME
Terminal=false
Categories=Office;Education;
StartupWMClass=AttendanceLogger
EOF
SIZE=$(du -sk "$ROOT/opt" | cut -f1)
cat > "$ROOT/DEBIAN/control" <<EOF
Package: $NAME
Version: $VERSION
Section: education
Priority: optional
Architecture: $ARCH
Installed-Size: $SIZE
Depends: libc6, libegl1, libgl1, libfontconfig1, libxkbcommon0, libxkbcommon-x11-0, libxcb-cursor0, libdbus-1-3
Maintainer: Attendance Management System <noreply@localhost>
Description: Companion app for the RFID attendance logger
 Reads the attendance logger's USB drive, keeps students, lectures and taps in
 a local database, registers cards by tapping them on the device and exports
 lecture lists as CSV or PDF.
EOF
cat > "$ROOT/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
EOF
chmod 755 "$ROOT/DEBIAN/postinst"
cp "$ROOT/DEBIAN/postinst" "$ROOT/DEBIAN/postrm"
dpkg-deb --root-owner-group --build "$ROOT" "$DIST/${NAME}_${VERSION}_${ARCH}.deb"

echo
echo "Built:"
ls -lh "$DIST"/*.deb "$DIST"/*.tar.gz
