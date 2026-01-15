@echo off
REM Quick transfer script - creates package and shows upload instructions

echo ========================================
echo  PZEM Monitoring - Quick Transfer Tool
echo ========================================
echo.

REM Run package script first
echo Step 1: Creating package...
call package.bat

echo.
echo ========================================
echo  Transfer Instructions
echo ========================================
echo.

REM Find the latest zip file
for /f "delims=" %%i in ('dir /b /o-d pzem-monitoring-ubuntu-*.zip 2^>nul') do (
    set LATEST_ZIP=%%i
    goto :found
)

:found
if not defined LATEST_ZIP (
    echo ERROR: Package file not found!
    pause
    exit /b 1
)

echo Package created: %LATEST_ZIP%
echo.

echo Choose transfer method:
echo.
echo [1] SCP (Command Line - requires SSH)
echo [2] WinSCP (GUI - recommended for beginners)
echo [3] FileZilla (GUI - SFTP)
echo [4] Cloud Storage (Google Drive, Dropbox, etc.)
echo [5] USB Drive
echo.

set /p METHOD="Enter method (1-5): "

if "%METHOD%"=="1" goto :scp
if "%METHOD%"=="2" goto :winscp
if "%METHOD%"=="3" goto :filezilla
if "%METHOD%"=="4" goto :cloud
if "%METHOD%"=="5" goto :usb

echo Invalid choice!
pause
exit /b 1

:scp
echo.
echo ========================================
echo  SCP Transfer Method
echo ========================================
echo.
echo 1. Open PowerShell or Git Bash
echo.
echo 2. Run this command (replace with your VPS details):
echo.
echo    scp %LATEST_ZIP% user@your-vps-ip:/opt/
echo.
echo 3. Enter your VPS password when prompted
echo.
echo 4. After upload, SSH to VPS and run:
echo.
echo    ssh user@your-vps-ip
echo    cd /opt
echo    unzip %LATEST_ZIP%
echo    mv pzem-monitoring-ubuntu pzem-monitoring
echo    cd pzem-monitoring
echo    chmod +x ubuntu-deploy.sh
echo    sudo ./ubuntu-deploy.sh
echo.
goto :end

:winscp
echo.
echo ========================================
echo  WinSCP Transfer Method
echo ========================================
echo.
echo 1. Download WinSCP: https://winscp.net/
echo.
echo 2. Install and open WinSCP
echo.
echo 3. Create new connection:
echo    - Protocol: SFTP
echo    - Host: your-vps-ip
echo    - Username: your-username
echo    - Password: your-password
echo.
echo 4. Connect to VPS
echo.
echo 5. Navigate to /opt folder on VPS
echo.
echo 6. Drag and drop %LATEST_ZIP% to /opt/
echo.
echo 7. Right-click on uploaded file → Extract
echo.
echo 8. SSH to VPS and run deployment:
echo    ssh user@your-vps-ip
echo    cd /opt/pzem-monitoring-ubuntu
echo    chmod +x ubuntu-deploy.sh
echo    sudo ./ubuntu-deploy.sh
echo.
goto :end

:filezilla
echo.
echo ========================================
echo  FileZilla Transfer Method
echo ========================================
echo.
echo 1. Download FileZilla: https://filezilla-project.org/
echo.
echo 2. Install and open FileZilla
echo.
echo 3. Click "File" → "Site Manager" → "New Site"
echo    - Protocol: SFTP
echo    - Host: your-vps-ip
echo    - Username: your-username
echo    - Password: your-password
echo.
echo 4. Connect to VPS
echo.
echo 5. Navigate to /opt on remote site
echo.
echo 6. Drag %LATEST_ZIP% from local to remote /opt/
echo.
echo 7. SSH to VPS and extract:
echo    ssh user@your-vps-ip
echo    cd /opt
echo    unzip %LATEST_ZIP%
echo    mv pzem-monitoring-ubuntu pzem-monitoring
echo    cd pzem-monitoring
echo    chmod +x ubuntu-deploy.sh
echo    sudo ./ubuntu-deploy.sh
echo.
goto :end

:cloud
echo.
echo ========================================
echo  Cloud Storage Transfer Method
echo ========================================
echo.
echo 1. Upload %LATEST_ZIP% to:
echo    - Google Drive, OR
echo    - Dropbox, OR
echo    - OneDrive, OR
echo    - Mega.nz
echo.
echo 2. Get shareable/download link
echo.
echo 3. On VPS, download the file:
echo.
echo    ssh user@your-vps-ip
echo    cd /opt
echo    wget "YOUR_DOWNLOAD_LINK" -O pzem-monitoring.zip
echo    # OR use curl:
echo    curl -L "YOUR_DOWNLOAD_LINK" -o pzem-monitoring.zip
echo.
echo 4. Extract and deploy:
echo    unzip pzem-monitoring.zip
echo    mv pzem-monitoring-ubuntu pzem-monitoring
echo    cd pzem-monitoring
echo    chmod +x ubuntu-deploy.sh
echo    sudo ./ubuntu-deploy.sh
echo.
goto :end

:usb
echo.
echo ========================================
echo  USB Drive Transfer Method
echo ========================================
echo.
echo 1. Copy %LATEST_ZIP% to USB drive
echo.
echo 2. Plug USB into computer with access to VPS
echo.
echo 3. Copy from USB to VPS:
echo    scp /path/to/usb/%LATEST_ZIP% user@your-vps-ip:/opt/
echo.
echo 4. Or if USB is connected to VPS:
echo    ssh user@your-vps-ip
echo    sudo cp /media/usb/%LATEST_ZIP% /opt/
echo    cd /opt
echo    unzip %LATEST_ZIP%
echo    mv pzem-monitoring-ubuntu pzem-monitoring
echo    cd pzem-monitoring
echo    chmod +x ubuntu-deploy.sh
echo    sudo ./ubuntu-deploy.sh
echo.
goto :end

:end
echo.
echo ========================================
echo  Next Steps
echo ========================================
echo.
echo After transfer, see UBUNTU-DEPLOYMENT.md for detailed instructions
echo.
echo Quick start on VPS:
echo    cd /opt/pzem-monitoring
echo    nano .env  # Edit configuration
echo    ./start.sh
echo.
pause











