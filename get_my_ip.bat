@echo off
echo Finding your IP address for sharing...
echo.

REM Get IPv4 address
for /f "tokens=14" %%a in ('ipconfig ^| findstr IPv4') do (
    echo Your local IP address: %%a
    echo.
    echo Share this URL with friends:
    echo http://%%a:8000/static/index.html
    echo.
)

echo.
echo Make sure:
echo 1. Your firewall allows connections on port 8000
echo 2. Your friends are on the same network (WiFi)
echo 3. The server is running with start_game.bat
echo.
pause
