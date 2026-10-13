#!/bin/sh
# Builds the Windows installer, dist/AttendanceLogger-Setup-<version>.exe, from Linux: runs Windows Python,
# PyInstaller and Inno Setup under Wine in the tobix/pywine Docker image. Needs Docker and a network connection.
#     sh packaging/build_windows_docker.sh          (VERSION=1.2.0 sh packaging/build_windows_docker.sh)
# On a Windows PC, packaging\build_windows.bat does the same natively.
set -eu
VERSION=${VERSION:-1.0.0}
IMAGE=${PYWINE_IMAGE:-tobix/pywine:3.12}
# Qt 6.9 and later need the icuuc.dll that Windows 10 ships and Wine lacks; 6.8 (LTS) does not.
PYSIDE=${PYSIDE:-PySide6-Essentials==6.8.3}
INNO_URL=https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=$(dirname "$HERE")
mkdir -p "$SRC/build/wine-cache"

docker run --rm -v "$SRC:/src" -w /src -e VERSION="$VERSION" -e PYSIDE="$PYSIDE" -e INNO_URL="$INNO_URL" \
    -e WINEDEBUG=-all -e HOME_UID="$(id -u)" -e HOME_GID="$(id -g)" "$IMAGE" sh -euc '
    # Inno Setup'"'"'s installer needs a display, and wineserver keeps the one it started with: give it one from the start.
    Xvfb :99 -nolisten tcp >/dev/null 2>&1 &
    export DISPLAY=:99 PIP_CACHE_DIR=Z:\\src\\build\\wine-cache\\pip
    wine python -m pip install --quiet "$PYSIDE" pyinstaller
    QT_QPA_PLATFORM=offscreen wine python packaging/make_icons.py build/icons
    wine python -m PyInstaller --noconfirm --clean --distpath build/windows-app --workpath build/windows-work \
        packaging/attendance_logger.spec
    if [ ! -f build/wine-cache/innosetup.exe ]; then
        curl -fsSL --retry 3 -o build/wine-cache/innosetup.exe "$INNO_URL"
    fi
    wine build/wine-cache/innosetup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /ALLUSERS
    ISCC=$(find /opt/wineprefix/drive_c -iname ISCC.exe | head -n1)
    wine "$ISCC" /Q "/DAppVersion=$VERSION" packaging/installer.iss
    chown -R "$HOME_UID:$HOME_GID" build dist
'
echo
echo "Built:"
ls -lh "$SRC/dist/AttendanceLogger-Setup-$VERSION.exe"
