@echo off
REM PZEM 3-Phase Monitoring System Startup Script for Windows

echo.
echo 🔋 PZEM 3-Phase Energy Monitoring System
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo 🐳 Starting Docker containers...
docker-compose up -d

echo.
echo ⏳ Waiting for services to start...
timeout /t 10 /nobreak >nul

echo.
echo 🔍 Checking service status...
docker-compose ps -q db >nul 2>&1 && echo Database:        ✅ Running || echo Database:        ❌ Failed
docker-compose ps -q dashboard >nul 2>&1 && echo Dashboard:       ✅ Running || echo Dashboard:       ❌ Failed
docker-compose ps -q mqtt-listener >nul 2>&1 && echo MQTT Listener:   ✅ Running || echo MQTT Listener:   ❌ Failed

echo.
echo 🌐 Service URLs:
echo Main Dashboard:     http://localhost:5000
echo Report Generator:   http://localhost:5000/reports
echo System Health:      http://localhost:5000/health

echo.
echo 📊 Useful Commands:
echo View logs:          docker-compose logs -f
echo Stop services:      docker-compose down
echo Restart services:   docker-compose restart
echo View status:        docker-compose ps

echo.
echo ✅ System startup complete!
echo 💡 Tip: Check the logs if services are not responding: docker-compose logs -f
echo.
pause
