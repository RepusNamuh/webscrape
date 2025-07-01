@echo off
echo Installing Web Scraper Service...
schtasks /create /tn "WebScraperService" /tr "%~dp0BunningsScraper.exe service" /sc onlogon /ru SYSTEM
if %errorlevel% neq 0 (
    echo Failed to install service. Please run this script as an administrator.
    pause
    exit /b 1
)
echo Installation complete.
pause