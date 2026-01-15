@echo off
REM Safe Deployment Script for Existing VPS (Windows)
REM This script deploys PZEM monitoring system WITHOUT deleting existing database

echo.
echo ========================================
echo PZEM Monitoring - Safe Deployment to VPS
echo ========================================
echo.
echo Target VPS: foom@103.31.39.189
echo.

REM Check if docker-compose.yml exists
if not exist "docker-compose.yml" (
    echo [ERROR] docker-compose.yml not found!
    echo Please run this script from the project root directory.
    pause
    exit /b 1
)

REM Create deployment package
echo [INFO] Creating deployment package...
set TIMESTAMP=%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set PACKAGE_NAME=pzem-monitoring-deploy-%TIMESTAMP%.tar.gz

REM Check if tar is available (Git Bash, WSL, or 7-Zip)
where tar >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Using tar command...
    tar -czf "%PACKAGE_NAME%" dashboard mqtt docker-compose.yml start.sh *.md 2>nul
) else (
    echo [INFO] tar not found, creating ZIP instead...
    set PACKAGE_NAME=pzem-monitoring-deploy-%TIMESTAMP%.zip
    powershell -Command "Compress-Archive -Path dashboard,mqtt,docker-compose.yml,start.sh -DestinationPath %PACKAGE_NAME% -Force"
)

if not exist "%PACKAGE_NAME%" (
    echo [ERROR] Failed to create package!
    pause
    exit /b 1
)

echo [SUCCESS] Package created: %PACKAGE_NAME%
echo.

REM Upload to VPS
echo [INFO] Uploading package to VPS...
echo [WARNING] You will be prompted for SSH password (or use SSH key if configured)
echo.

scp "%PACKAGE_NAME%" foom@103.31.39.189:/tmp/

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to upload package!
    echo.
    echo Alternative: Upload manually using WinSCP or FileZilla
    echo   Source: %CD%\%PACKAGE_NAME%
    echo   Destination: /tmp/ on VPS
    pause
    exit /b 1
)

echo [SUCCESS] Package uploaded to VPS
echo.

REM Create remote deployment script
echo [INFO] Creating remote deployment script...

REM Create remote script content
(
echo #!/bin/bash
echo # Remote deployment script - runs on VPS
echo set -e
echo.
echo VPS_DEPLOY_DIR="/opt/pzem-monitoring"
echo BACKUP_DIR="/opt/backups/pzem-monitoring"
echo PACKAGE_FILE=$(ls /tmp/pzem-monitoring-deploy-*.tar.gz /tmp/pzem-monitoring-deploy-*.zip 2^>nul | head -1^)
echo.
echo # Detect docker-compose
echo if command -v docker-compose ^&^> /dev/null; then
echo     DOCKER_COMPOSE="docker-compose"
echo elif docker compose version ^&^> /dev/null; then
echo     DOCKER_COMPOSE="docker compose"
echo else
echo     echo "docker-compose not found"
echo     exit 1
echo fi
echo.
echo echo "Starting deployment..."
echo.
echo # Backup existing database
echo if [ -d "${VPS_DEPLOY_DIR}" ]; then
echo     echo "Backing up existing database..."
echo     mkdir -p "${BACKUP_DIR}"
echo     if docker ps | grep -q "pzem.*db"; then
echo         docker exec $(docker ps | grep "pzem.*db" | awk '{print $1}') pg_dump -U postgres pzem_monitoring ^> "${BACKUP_DIR}/database_before_deploy_$(date +%%Y%%m%%d_%%H%%M%%S).sql" 2^>nul || true
echo     fi
echo     if [ -f "${VPS_DEPLOY_DIR}/.env" ]; then
echo         cp "${VPS_DEPLOY_DIR}/.env" "${BACKUP_DIR}/.env.backup.$(date +%%Y%%m%%d_%%H%%M%%S)"
echo     fi
echo     cd "${VPS_DEPLOY_DIR}"
echo     $DOCKER_COMPOSE down 2^>nul || true
echo fi
echo.
echo # Extract package
echo cd /opt
echo if [ -d "${VPS_DEPLOY_DIR}" ]; then
echo     mv "${VPS_DEPLOY_DIR}" "${VPS_DEPLOY_DIR}_backup_$(date +%%Y%%m%%d_%%H%%M%%S)"
echo fi
echo.
echo if echo "$PACKAGE_FILE" | grep -q "\.tar\.gz$"; then
echo     tar -xzf "$PACKAGE_FILE" -C /opt/
echo else
echo     unzip -q "$PACKAGE_FILE" -d /opt/
echo fi
echo.
echo # Restore .env
echo if [ -f "${BACKUP_DIR}/.env.backup."* ]; then
echo     cp $(ls -t "${BACKUP_DIR}/.env.backup."* | head -1) "${VPS_DEPLOY_DIR}/.env"
echo fi
echo.
echo # Build and start
echo cd "${VPS_DEPLOY_DIR}"
echo chmod +x *.sh 2^>nul || true
echo $DOCKER_COMPOSE build
echo $DOCKER_COMPOSE up -d
echo.
echo echo "Deployment completed!"
echo echo "Check status: cd ${VPS_DEPLOY_DIR} ^&^& $DOCKER_COMPOSE ps"
) > remote-deploy-temp.sh

REM Upload remote script
scp remote-deploy-temp.sh foom@103.31.39.189:/tmp/remote-deploy.sh

REM Execute remote deployment
echo [INFO] Executing deployment on VPS...
echo.

ssh foom@103.31.39.189 "chmod +x /tmp/remote-deploy.sh && bash /tmp/remote-deploy.sh"

REM Cleanup
del remote-deploy-temp.sh 2>nul
del "%PACKAGE_NAME%" 2>nul

echo.
echo [SUCCESS] Deployment completed!
echo.
echo Access your system:
echo   Dashboard: http://103.31.39.189:5000
echo   Reports: http://103.31.39.189:5000/reports
echo   Health: http://103.31.39.189:5000/health
echo.
echo Next steps:
echo   1. SSH to VPS: ssh foom@103.31.39.189
echo   2. Check status: cd /opt/pzem-monitoring ^&^& docker-compose ps
echo   3. View logs: cd /opt/pzem-monitoring ^&^& docker-compose logs -f
echo.
pause
