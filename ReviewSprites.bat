@echo off
REM Open the visual sprite mapping editor (reviewer.html) with a local server so
REM "Export mapping.json" can save in place (backup: mapping.backup.json).
setlocal
cd /d "%~dp0JavaGoldenAxe\tools\guybrush"

echo Regenerating reviewer.html ...
python make_reviewer.py
if errorlevel 1 (
    echo.
    echo Failed to build the editor. Python 3 with Pillow and numpy is required.
    pause
    exit /b 1
)

echo Starting the sprite mapper server (Ctrl+C here to stop)...
python serve_reviewer.py
endlocal
