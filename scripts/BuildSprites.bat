@echo off
REM Bake mapping.json into the game's character sprites (then run GoldenAxe.bat).
setlocal
cd /d "%~dp0..\JavaGoldenAxe\tools\guybrush"

echo Rebuilding Guybrush character sprites from mapping.json ...
python build_atlas.py
if errorlevel 1 (
    echo.
    echo Failed. Python 3 with Pillow and numpy is required.
    pause
    exit /b 1
)

echo.
echo Done. Run GoldenAxe.bat to play.
pause
endlocal
