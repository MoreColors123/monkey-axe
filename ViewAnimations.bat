@echo off
REM Play the baked Guybrush character (viewer.html) - move, run, JUMP, ATTACK,
REM JUMP+ATTACK, magic, get hit, die - animated exactly as the game draws it.
REM Regenerates the page from the baked assets each time, then opens it.
setlocal
cd /d "%~dp0JavaGoldenAxe\tools\guybrush"

echo Regenerating viewer.html ...
python make_viewer.py
if errorlevel 1 (
    echo.
    echo Failed to build the viewer. Python 3 with Pillow and numpy is required.
    pause
    exit /b 1
)

echo Opening viewer.html ...
start "" "viewer.html"
endlocal
