@echo off
REM Build a standalone monkeyaxe.jar (game + assets) into the repo root.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_release.ps1"
pause
endlocal
