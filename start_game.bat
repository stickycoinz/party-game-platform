@echo off
title Party Game Platform
echo.
echo ================================
echo   🎮 Party Game Platform 🎮
echo ================================
echo.
echo Starting the server...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "app\main.py" (
    echo ❌ Please run this script from the party_game_app directory
    pause
    exit /b 1
)

REM Install dependencies if needed
echo 📦 Checking dependencies...
pip install -r requirements.txt --quiet

REM Start the server
echo.
echo 🚀 Starting Party Game Platform...
echo.
echo ✅ Server will be available at:
echo    📱 Test Client: http://127.0.0.1:8000/static/index.html
echo    📚 API Docs:    http://127.0.0.1:8000/docs
echo.
echo 💡 Press Ctrl+C to stop the server
echo.

echo.
echo 🌐 Server URLs:
echo    💻 For you (local):     http://127.0.0.1:8000/static/index.html
echo    📤 Share with friends:  http://localhost:8000/static/index.html
echo    📤 Or find your IP and use: http://YOUR_IP:8000/static/index.html
echo.
echo 💡 To find your IP for friends: Run 'ipconfig' and look for IPv4 Address
echo.

REM Start the server in the background and open browser
echo 🌐 Opening game in your browser...
timeout /t 3 /nobreak >nul
start http://127.0.0.1:8000/static/index.html

REM Start the server with auto-reload (bind to all interfaces)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo Server stopped. Press any key to exit...
pause >nul
