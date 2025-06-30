@echo off
echo Installing Web Scraper Service...
schtasks /create /tn "WebScraperService" /tr "%CD%\BunningsScraper.exe service" /sc onstart /ru SYSTEM
if %errorlevel% neq 0 (
    echo Failed to install service. Please run this script as an administrator.
    pause
    exit /b 1
)
echo Installation complete.
pause