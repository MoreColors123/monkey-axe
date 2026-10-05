@echo off
REM Open the visual sprite mapping editor (reviewer.html).
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

echo Opening the sprite mapper in your browser...
start "" "%~dp0JavaGoldenAxe\tools\guybrush\reviewer.html"
endlocal
