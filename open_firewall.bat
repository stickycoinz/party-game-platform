@echo off
echo Opening Windows Firewall for Party Game Platform...
echo.

REM Add firewall rule for port 8000
netsh advfirewall firewall add rule name="Party Game Platform" dir=in action=allow protocol=TCP localport=8000

if %errorlevel% equ 0 (
    echo ✅ Firewall rule added successfully!
    echo Port 8000 is now open for incoming connections.
) else (
    echo ❌ Failed to add firewall rule.
    echo Please run this as Administrator or add the rule manually.
    echo.
    echo Manual steps:
    echo 1. Press Windows + R, type "wf.msc"
    echo 2. Click "Inbound Rules" then "New Rule"
    echo 3. Select "Port" then "TCP" then "8000"
    echo 4. Select "Allow the connection"
)

echo.
pause
