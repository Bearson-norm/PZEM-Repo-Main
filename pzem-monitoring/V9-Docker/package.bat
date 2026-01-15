@echo off
REM Package script to create deployment archive for Ubuntu VPS

echo 📦 Creating PZEM Monitoring System Deployment Package
echo =====================================================

REM Create package directory
set PACKAGE_DIR=pzem-monitoring-ubuntu
set DATE=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set DATE=%DATE: =0%
set PACKAGE_NAME=pzem-monitoring-ubuntu-%DATE%.zip

echo 📁 Creating package directory: %PACKAGE_DIR%
if exist "%PACKAGE_DIR%" rmdir /s /q "%PACKAGE_DIR%"
mkdir "%PACKAGE_DIR%"

echo 📋 Copying project files...
xcopy /E /I /Y dashboard "%PACKAGE_DIR%\dashboard"
xcopy /E /I /Y mqtt "%PACKAGE_DIR%\mqtt"
copy /Y docker-compose.yml "%PACKAGE_DIR%\"
if exist docker-compose.production.yml copy /Y docker-compose.production.yml "%PACKAGE_DIR%\"
copy /Y start.sh "%PACKAGE_DIR%\"
if exist deploy.sh copy /Y deploy.sh "%PACKAGE_DIR%\"
copy /Y ubuntu-deploy.sh "%PACKAGE_DIR%\"
if exist env.example copy /Y env.example "%PACKAGE_DIR%\"
copy /Y README.md "%PACKAGE_DIR%\"
if exist UBUNTU-DEPLOYMENT.md copy /Y UBUNTU-DEPLOYMENT.md "%PACKAGE_DIR%\"

echo 📝 Creating deployment instructions...
(
echo # 🚀 PZEM Monitoring System - Ubuntu VPS Deployment
echo.
echo ## Quick Start
echo.
echo 1. **Upload to VPS:**
echo ```bash
echo scp -r pzem-monitoring-ubuntu/* user@your-vps-ip:/opt/pzem-monitoring/
echo ```
echo.
echo 2. **SSH into VPS:**
echo ```bash
echo ssh user@your-vps-ip
echo cd /opt/pzem-monitoring
echo ```
echo.
echo 3. **Run deployment:**
echo ```bash
echo chmod +x deploy.sh
echo sudo ./deploy.sh
echo ```
echo.
echo 4. **Configure environment:**
echo ```bash
echo cp env.example .env
echo nano .env  # Edit with your settings
echo ```
echo.
echo 5. **Start system:**
echo ```bash
echo ./start.sh
echo ```
echo.
echo ## Access URLs
echo - Dashboard: http://your-vps-ip:5000
echo - Reports: http://your-vps-ip:5000/reports
echo - Health: http://your-vps-ip:5000/health
echo.
echo ## Configuration
echo Edit `.env` file with your settings:
echo - DB_PASSWORD: Secure database password
echo - MQTT_BROKER: Your MQTT broker IP/domain
echo - MQTT_TOPIC: Your MQTT topic
echo.
echo ## Management Commands
echo ```bash
echo # View logs
echo docker-compose logs -f
echo.
echo # Restart services
echo docker-compose restart
echo.
echo # Backup data
echo ./backup.sh
echo.
echo # Update system
echo ./update.sh
echo ```
) > "%PACKAGE_DIR%\DEPLOYMENT.md"

echo ⚡ Creating quick start script...
(
echo #!/bin/bash
echo # Quick start script for Ubuntu VPS deployment
echo.
echo echo "🚀 PZEM Monitoring System - Quick Start"
echo echo "======================================="
echo.
echo # Check if running as root
echo if [[ "$EUID" -eq 0 ]]; then
echo     echo "✅ Running as root - good for VPS deployment"
echo else
echo     echo "⚠️  Not running as root. Some operations may require sudo."
echo fi
echo.
echo # Install Docker if not present
echo if ! command -v docker ^&^> /dev/null; then
echo     echo "📦 Installing Docker..."
echo     curl -fsSL https://get.docker.com -o get-docker.sh
echo     sh get-docker.sh
echo     usermod -aG docker $USER
echo     echo "✅ Docker installed. Please log out and back in."
echo fi
echo.
echo # Install Docker Compose if not present
echo if ! command -v docker-compose ^&^> /dev/null; then
echo     echo "📦 Installing Docker Compose..."
echo     curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
echo     chmod +x /usr/local/bin/docker-compose
echo     echo "✅ Docker Compose installed"
echo fi
echo.
echo # Configure environment
echo if [ ! -f .env ]; then
echo     echo "⚙️  Setting up environment..."
echo     cp env.example .env
echo     echo "📝 Please edit .env file with your settings:"
echo     echo "   - DB_PASSWORD: Set a secure password"
echo     echo "   - MQTT_BROKER: Your MQTT broker address"
echo     echo "   - MQTT_TOPIC: Your MQTT topic"
echo     echo ""
echo     echo "Then run: ./start.sh"
echo else
echo     echo "✅ Environment already configured"
echo     echo "🚀 Starting services..."
echo     ./start.sh
echo fi
) > "%PACKAGE_DIR%\quick-start.sh"

echo 🔧 Creating systemd service...
(
echo [Unit]
echo Description=PZEM 3-Phase Energy Monitoring System
echo Requires=docker.service
echo After=docker.service
echo.
echo [Service]
echo Type=oneshot
echo RemainAfterExit=yes
echo WorkingDirectory=/opt/pzem-monitoring
echo ExecStart=/usr/local/bin/docker-compose up -d
echo ExecStop=/usr/local/bin/docker-compose down
echo TimeoutStartSec=0
echo.
echo [Install]
echo WantedBy=multi-user.target
) > "%PACKAGE_DIR%\pzem-monitoring.service"

echo 💾 Creating backup script...
(
echo #!/bin/bash
echo # Backup script for PZEM monitoring system
echo.
echo BACKUP_DIR="/opt/backups/pzem-monitoring"
echo DATE=$(date +%%Y%%m%%d_%%H%%M%%S)
echo.
echo mkdir -p "$BACKUP_DIR"
echo.
echo echo "Creating backup: pzem_backup_$DATE.tar.gz"
echo.
echo # Backup database
echo docker-compose exec -T db pg_dump -U postgres pzem_monitoring ^> "$BACKUP_DIR/database_$DATE.sql"
echo.
echo # Backup reports
echo if [ -d "reports" ]; then
echo     tar -czf "$BACKUP_DIR/reports_$DATE.tar.gz" reports/
echo fi
echo.
echo # Backup configuration
echo tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" docker-compose.yml *.sh *.md .env
echo.
echo echo "Backup completed: $BACKUP_DIR"
) > "%PACKAGE_DIR%\backup.sh"

echo 🔄 Creating update script...
REM Copy update.sh dari ubuntu-deploy.sh yang sudah ada (jika ada)
if exist ubuntu-deploy.sh (
    REM Extract update.sh dari ubuntu-deploy.sh
    powershell -Command "(Get-Content ubuntu-deploy.sh -Raw) -match '(?s)cat > update.sh << ''EOF''(.*?)EOF' | Out-Null; if ($matches) { $matches[1] -replace '`r`n', '`n' | Out-File -Encoding ASCII -NoNewline '%PACKAGE_DIR%\update.sh' }"
) else (
    REM Fallback: create simple update script
    (
    echo #!/bin/bash
    echo # Update script for PZEM monitoring system
    echo docker-compose down
    echo docker-compose pull
    echo docker-compose build
    echo docker-compose up -d
    echo echo "Update completed!"
    ) > "%PACKAGE_DIR%\update.sh"
)
REM Convert to Unix line endings using PowerShell for all scripts
echo 🔧 Converting script line endings to Unix format...
powershell -Command "(Get-Content '%PACKAGE_DIR%\update.sh' -Raw) -replace '`r`n', '`n' | Set-Content -NoNewline '%PACKAGE_DIR%\update.sh' -Encoding ASCII"
if exist "%PACKAGE_DIR%\backup.sh" (
    powershell -Command "(Get-Content '%PACKAGE_DIR%\backup.sh' -Raw) -replace '`r`n', '`n' | Set-Content -NoNewline '%PACKAGE_DIR%\backup.sh' -Encoding ASCII"
)
if exist "%PACKAGE_DIR%\quick-start.sh" (
    powershell -Command "(Get-Content '%PACKAGE_DIR%\quick-start.sh' -Raw) -replace '`r`n', '`n' | Set-Content -NoNewline '%PACKAGE_DIR%\quick-start.sh' -Encoding ASCII"
)
if exist "%PACKAGE_DIR%\start.sh" (
    powershell -Command "(Get-Content '%PACKAGE_DIR%\start.sh' -Raw) -replace '`r`n', '`n' | Set-Content -NoNewline '%PACKAGE_DIR%\start.sh' -Encoding ASCII"
)
if exist "%PACKAGE_DIR%\ubuntu-deploy.sh" (
    powershell -Command "(Get-Content '%PACKAGE_DIR%\ubuntu-deploy.sh' -Raw) -replace '`r`n', '`n' | Set-Content -NoNewline '%PACKAGE_DIR%\ubuntu-deploy.sh' -Encoding ASCII"
)

echo 📦 Creating deployment package...
REM Create ZIP dengan struktur folder yang benar - compress folder, bukan isinya
REM Ini memastikan saat unzip akan langsung jadi folder pzem-monitoring-ubuntu
cd ..
powershell Compress-Archive -Path "%PACKAGE_DIR%" -DestinationPath "%PACKAGE_NAME%" -Force
cd %~dp0

REM Cleanup
rmdir /s /q "%PACKAGE_DIR%"

echo.
echo 🎉 Package created successfully!
echo 📦 Package: %PACKAGE_NAME%
for %%A in ("%PACKAGE_NAME%") do echo 📏 Size: %%~zA bytes
echo.
echo 📋 Deployment Instructions:
echo 1. Upload package to your Ubuntu VPS:
echo    scp %PACKAGE_NAME% user@your-vps-ip:/opt/
echo.
echo 2. SSH into VPS and extract:
echo    ssh user@your-vps-ip
echo    cd /opt
echo    unzip %PACKAGE_NAME%
echo    mv pzem-monitoring-ubuntu pzem-monitoring
echo    cd pzem-monitoring
echo.
echo 3. Run quick start:
echo    chmod +x quick-start.sh
echo    sudo ./quick-start.sh
echo.
echo 4. Configure and start:
echo    nano .env  # Edit configuration
echo    ./start.sh
echo.
echo 🌐 Access your system at: http://your-vps-ip:5000

pause



