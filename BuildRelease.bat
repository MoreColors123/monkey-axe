@echo off
REM Build a standalone GoldenAxe.jar (game + assets) into the dist\ folder.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_release.ps1"
pause
endlocal
