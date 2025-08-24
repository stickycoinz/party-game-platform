@echo off
echo 📦 Setting up Git repository for cloud deployment...
echo.

REM Check if git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Git is not installed
    echo Please install Git from: https://git-scm.com/download/win
    echo.
    echo Or use the manual upload method in deploy_to_cloud.bat
    pause
    exit /b 1
)

echo ✅ Git is installed
echo.

REM Initialize git repository
if not exist ".git" (
    echo 🔧 Initializing Git repository...
    git init
    echo.
)

REM Add all files
echo 📁 Adding files to repository...
git add .

REM Commit
echo 💾 Creating commit...
git commit -m "Initial commit - Party Game Platform"

echo.
echo ✅ Git repository is ready!
echo.
echo 📋 Next steps:
echo 1. Create a repository on GitHub.com
echo 2. Copy the commands GitHub shows you
echo 3. Run them in this folder
echo 4. Use the GitHub repo for deployment
echo.

echo 🔗 Opening GitHub in your browser...
start https://github.com/new
echo.
pause
