@echo off
rem Builds the Attendance Logger for Windows: a standalone app (PyInstaller, no Python needed on the target) and
rem its installer, dist\AttendanceLogger-Setup-<version>.exe.
rem Run from the Companion folder or by double-click:  packaging\build_windows.bat [version]
rem Needs Python 3 (python.org, 64-bit) and Inno Setup 6 (https://jrsoftware.org/isinfo.php; iscc.exe on PATH or
rem in its default folder). The build venv goes in build\venv, separate from .venv.
setlocal
cd /d "%~dp0.."
set VERSION=%1
if "%VERSION%"=="" set VERSION=1.0.0

if not exist "build\venv\Scripts\python.exe" (
    python -m venv build\venv || goto :fail
)
set PY=build\venv\Scripts\python.exe
%PY% -m pip install --quiet --upgrade pip || goto :fail
%PY% -m pip install --quiet "PySide6-Essentials>=6.5" pyinstaller || goto :fail
%PY% packaging\make_icons.py build\icons || goto :fail
%PY% -m PyInstaller --noconfirm --clean --distpath build\windows-app --workpath build\windows-work packaging\attendance_logger.spec || goto :fail

set "ISCC="
for %%I in (iscc.exe) do set "ISCC=%%~$PATH:I"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    echo Inno Setup 6 was not found. Install it from https://jrsoftware.org/isinfo.php
    goto :fail
)
"%ISCC%" /Q /DAppVersion=%VERSION% packaging\installer.iss || goto :fail

echo.
echo Built dist\AttendanceLogger-Setup-%VERSION%.exe
goto :eof

:fail
echo.
echo The build failed (see above).
exit /b 1
