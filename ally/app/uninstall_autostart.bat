@echo off
REM Removes the Rendu shortcuts (desktop + Start Menu, plus any legacy Startup).
del "%USERPROFILE%\Desktop\Rendu.lnk" 2>nul
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Rendu.lnk" 2>nul
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Rendu.lnk" 2>nul
echo Rendu shortcuts removed.
