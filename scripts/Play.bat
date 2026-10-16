@echo off
REM Play the game. This file ships INSIDE monkeyaxe.zip, next to monkeyaxe.jar.
REM In a git checkout it lives in scripts\; scripts\BuildRelease.bat then puts
REM the jar one level up, which the second check below covers.
cd /d "%~dp0"
title Golden Axe - Guybrush Threepwood mod

REM Where is the game? Next to this file (unzipped zip), else one level up (repo).
if exist "monkeyaxe.jar" goto jarfound
if exist "..\monkeyaxe.jar" cd /d ".."
if not exist "monkeyaxe.jar" goto nojar

:jarfound
REM Find a Java runtime: PATH first, then JAVA_HOME.
set "JAVA=java"
"%JAVA%" -version >nul 2>nul
if errorlevel 1 if defined JAVA_HOME if exist "%JAVA_HOME%in\java.exe" set "JAVA=%JAVA_HOME%in\java.exe"
"%JAVA%" -version >nul 2>nul
if errorlevel 1 goto nojava

"%JAVA%" -jar "monkeyaxe.jar"
if errorlevel 1 pause
exit /b 0

:nojar
echo.
echo   monkeyaxe.jar was not found next to this file.
echo.
echo   * Unpacked only part of the archive? Unzip the WHOLE monkeyaxe.zip into
echo     one folder, then double-click the Play.bat inside it.
echo   * Working from a git checkout? Build the jar first, then run this again:
echo         scripts\BuildRelease.bat
echo.
pause
exit /b 1

:nojava
echo.
echo   Golden Axe needs Java 17 or newer and it was not found.
echo.
echo   * Opening the Java 17 download page now.
echo   * Install the Windows x64 JRE (keep the default options),
echo     then double-click Play.bat again.
echo.
start "" "https://adoptium.net/temurin/releases/?version=17&os=windows&arch=x64&package=jre"
pause
exit /b 1
