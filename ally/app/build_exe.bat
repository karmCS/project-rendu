@echo off
REM Build Rendu.exe — run from ally\app directory.
REM Requires: pip install pyinstaller, and a built frontend in static/

cd /d %~dp0

if not exist static\index.html (
    echo ERROR: static\index.html missing. Run "npm run build" inside frontend\ first.
    exit /b 1
)

echo === Cleaning previous build ===
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo === Running PyInstaller ===
pyinstaller Rendu.spec --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller failed.
    exit /b 1
)

echo.
echo === Build complete ===
echo Executable: %CD%\dist\Rendu.exe
echo Size:
for %%I in (dist\Rendu.exe) do echo   %%~zI bytes
