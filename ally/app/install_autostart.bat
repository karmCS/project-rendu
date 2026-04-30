@echo off
REM install_autostart.bat — dev-side installer that creates desktop and
REM Start Menu shortcuts to dist\Rendu.exe. Despite the file name (kept for
REM compatibility), Rendu does NOT auto-start. The user launches it manually.
REM Run from ally\app\ AFTER building dist\Rendu.exe.

setlocal

set "EXE=%~dp0dist\Rendu.exe"
set "DESKTOP=%USERPROFILE%\Desktop"
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"

if not exist "%EXE%" (
    echo ERROR: %EXE% not found. Run build_exe.bat first.
    exit /b 1
)

powershell -NoProfile -Command ^
    "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%DESKTOP%\Rendu.lnk');" ^
    "$s.TargetPath='%EXE%';" ^
    "$s.WorkingDirectory='%~dp0dist';" ^
    "$s.Description='Rendu — clinical note assistant';" ^
    "$s.Save()"

powershell -NoProfile -Command ^
    "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%STARTMENU%\Rendu.lnk');" ^
    "$s.TargetPath='%EXE%';" ^
    "$s.WorkingDirectory='%~dp0dist';" ^
    "$s.Description='Rendu — clinical note assistant';" ^
    "$s.Save()"

echo === Rendu shortcuts installed ===
echo Desktop:    %DESKTOP%\Rendu.lnk
echo Start Menu: %STARTMENU%\Rendu.lnk
echo Done. Tap the desktop icon to launch.
