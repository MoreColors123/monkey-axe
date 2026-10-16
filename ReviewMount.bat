@echo off
REM Open the mount editor (mount_editor.html): drag the riding pose onto every
REM beast; Save writes mount_placements.json through the local server.
setlocal
cd /d "%~dp0JavaGoldenAxe\tools\guybrush"

echo Starting the mount editor (Ctrl+C here to stop)...
python serve_mount.py
endlocal
