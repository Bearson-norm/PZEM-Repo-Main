@echo off
REM ==============================================
REM PZEM Monitoring System - Windows Startup
REM ==============================================

echo.
echo ========================================
echo PZEM Energy Monitoring System (Windows)
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo [INFO] Python is available
python --version

REM Test database connection
echo.
echo [INFO] Testing database connection...
python -c "import psycopg2; conn = psycopg2.connect(host='localhost', database='pzem_monitoring', user='postgres', password='Admin123'); print('[SUCCESS] Database connection OK'); conn.close()" 2>nul
if errorlevel 1 (
    echo [ERROR] Database connection failed
    echo Please check:
    echo   1. PostgreSQL is running
    echo   2. Database 'pzem_monitoring' exists
    echo   3. User credentials are correct
    pause
    exit /b 1
)

echo.
echo [INFO] Starting services...
echo.
echo Choose an option:
echo   1. Start MQTT Client only
echo   2. Start Dashboard only
echo   3. Start both services
echo.
set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" (
    echo.
    echo [STARTING] MQTT Client...
    echo Press Ctrl+C to stop
    python mqtt_client_windows.py
) else if "%choice%"=="2" (
    echo.
    echo [STARTING] Dashboard...
    echo Open browser to: http://localhost:5000
    echo Press Ctrl+C to stop
    python app_windows.py
) else if "%choice%"=="3" (
    echo.
    echo [STARTING] Both services...
    echo MQTT Client will start in background
    echo Dashboard will start in foreground
    echo Open browser to: http://localhost:5000
    echo Press Ctrl+C to stop all
    start /b python mqtt_client_windows.py
    python app_windows.py
) else (
    echo [ERROR] Invalid choice
    pause
    exit /b 1
)

pause