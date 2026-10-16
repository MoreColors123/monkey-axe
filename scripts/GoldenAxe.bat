@echo off
REM Double-click this file to build (first time) and play Golden Axe
REM with Guybrush Threepwood as a playable character.
setlocal
cd /d "%~dp0"

echo ============================================
echo   Golden Axe  -  Guybrush Threepwood mod
echo ============================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
set "ERR=%ERRORLEVEL%"

if not "%ERR%"=="0" (
    echo.
    echo ------------------------------------------------------------
    echo Something went wrong (exit code %ERR%).
    echo Make sure a JDK (Java 17 or newer) is installed and on your PATH.
    echo You can check with:  java -version
    echo ------------------------------------------------------------
    echo.
    pause
)

endlocal
