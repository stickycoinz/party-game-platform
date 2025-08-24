@echo off
echo Testing network connectivity for Party Game Platform...
echo.

REM Get IPv4 address
for /f "tokens=14" %%a in ('ipconfig ^| findstr IPv4') do (
    set LOCAL_IP=%%a
    echo Your IP address: %%a
    echo.
    
    echo Testing if port 8000 is accessible...
    netstat -an | findstr :8000
    
    if %errorlevel% equ 0 (
        echo ✅ Port 8000 is listening
    ) else (
        echo ❌ Port 8000 is not listening - make sure the server is running
    )
    
    echo.
    echo 🌐 URLs to test:
    echo   Local: http://127.0.0.1:8000/static/index.html
    echo   Network: http://%%a:8000/static/index.html
    echo.
    echo 📤 Share with friends: http://%%a:8000/static/index.html
    echo.
    echo 🔍 Troubleshooting:
    echo   1. Make sure the server is running
    echo   2. Run open_firewall.bat as Administrator
    echo   3. Check if you're on the same WiFi network
    echo   4. Some routers block device-to-device communication
    echo.
)

pause
