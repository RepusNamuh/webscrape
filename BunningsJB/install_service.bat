@echo off
setlocal enabledelayedexpansion
echo Installing Web Scraper Service...

REM Set default values
set "default_frequency=1"
set "default_time=12:00"

REM Try to read from frequency.txt, use defaults if not found
if exist "%~dp0frequency.txt" (
    set /p frequency=<"%~dp0frequency.txt"
    for /f "skip=1 delims=" %%a in ('type "%~dp0frequency.txt"') do (
        set "interval=%%a"
        goto :continue
    )
) else (
    set "frequency=!default_frequency!"
    set "interval=!default_time!"
    (
        echo !frequency!
        echo !interval!
    ) > "%~dp0frequency.txt"
    echo Created frequency.txt with default settings
)

:continue


REM Create the scheduled task with daily frequency
schtasks /create /tn "WebScraperService2" /tr "%~dp0bunningsJB.exe service" /sc "daily" /mo "!frequency!" /st "!interval!" /ru "SYSTEM" /f

if !errorlevel! neq 0 (
    echo Failed to install service. Please run this script as an administrator.
    pause
    exit /b 1
)
echo Installation complete.
echo Service will run every !frequency! day(s) at !interval!
pause