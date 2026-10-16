@echo off
cd /d "%~dp0"
title Golden Axe - Guybrush Threepwood mod

REM Find a Java runtime: PATH first, then JAVA_HOME.
set "JAVA=java"
"%JAVA%" -version >nul 2>nul
if errorlevel 1 if defined JAVA_HOME if exist "%JAVA_HOME%\bin\java.exe" set "JAVA=%JAVA_HOME%\bin\java.exe"
"%JAVA%" -version >nul 2>nul
if errorlevel 1 goto nojava

if not exist "monkeyaxe.jar" (
    echo monkeyaxe.jar is missing. Rebuild it with scripts\BuildRelease.bat ^(needs a JDK^).
    pause
    exit /b 1
)

"%JAVA%" -jar "monkeyaxe.jar"
if errorlevel 1 pause
exit /b 0

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
