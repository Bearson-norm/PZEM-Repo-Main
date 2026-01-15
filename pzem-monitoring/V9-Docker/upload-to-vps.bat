@echo off
REM Script untuk upload package ke VPS dengan handling permission

echo ========================================
echo  PZEM Monitoring - Upload to VPS
echo ========================================
echo.

REM Check if package exists
set PACKAGE_FILE=
for %%f in (pzem-monitoring-ubuntu-*.zip) do set PACKAGE_FILE=%%f

if not defined PACKAGE_FILE (
    echo ERROR: Package file not found!
    echo Please run package.bat first to create the package.
    pause
    exit /b 1
)

echo Found package: %PACKAGE_FILE%
echo.

REM Get VPS details
set /p VPS_USER="Enter VPS username (e.g., foom): "
set /p VPS_IP="Enter VPS IP address (e.g., 103.31.39.189): "

echo.
echo ========================================
echo  Upload Options
echo ========================================
echo.
echo [1] Upload to home directory (recommended - no permission issue)
echo [2] Upload to /tmp directory
echo [3] Upload directly to /opt/ (requires sudo permission)
echo.

set /p UPLOAD_METHOD="Choose method (1-3): "

if "%UPLOAD_METHOD%"=="1" goto :home
if "%UPLOAD_METHOD%"=="2" goto :tmp
if "%UPLOAD_METHOD%"=="3" goto :opt

echo Invalid choice!
pause
exit /b 1

:home
echo.
echo Uploading to home directory...
scp %PACKAGE_FILE% %VPS_USER%@%VPS_IP%:~/
if errorlevel 1 (
    echo.
    echo ERROR: Upload failed!
    echo Please check:
    echo - VPS IP and username are correct
    echo - SSH connection is working
    echo - You have permission to access VPS
    pause
    exit /b 1
)
echo.
echo ✅ Upload successful!
echo.
echo Next steps on VPS:
echo    ssh %VPS_USER%@%VPS_IP%
echo    sudo mv ~/%PACKAGE_FILE% /opt/
echo    cd /opt
echo    sudo unzip %PACKAGE_FILE%
echo    sudo mv pzem-monitoring-ubuntu pzem-monitoring
echo    sudo chown -R $USER:$USER /opt/pzem-monitoring
echo    cd pzem-monitoring
echo    chmod +x ubuntu-deploy.sh
echo    sudo ./ubuntu-deploy.sh
goto :end

:tmp
echo.
echo Uploading to /tmp directory...
scp %PACKAGE_FILE% %VPS_USER%@%VPS_IP%:/tmp/
if errorlevel 1 (
    echo.
    echo ERROR: Upload failed!
    pause
    exit /b 1
)
echo.
echo ✅ Upload successful!
echo.
echo Next steps on VPS:
echo    ssh %VPS_USER%@%VPS_IP%
echo    sudo mv /tmp/%PACKAGE_FILE% /opt/
echo    cd /opt
echo    sudo unzip %PACKAGE_FILE%
echo    sudo mv pzem-monitoring-ubuntu pzem-monitoring
echo    sudo chown -R $USER:$USER /opt/pzem-monitoring
echo    cd pzem-monitoring
echo    chmod +x ubuntu-deploy.sh
echo    sudo ./ubuntu-deploy.sh
goto :end

:opt
echo.
echo ⚠️  WARNING: Direct upload to /opt/ requires sudo permission
echo This may fail if user doesn't have write access to /opt/
echo.
echo Uploading directly to /opt/...
scp %PACKAGE_FILE% %VPS_USER%@%VPS_IP%:/opt/
if errorlevel 1 (
    echo.
    echo ❌ Upload failed - Permission denied!
    echo.
    echo Solution: Use method 1 (home directory) instead
    echo Run this script again and choose option 1
    pause
    exit /b 1
)
echo.
echo ✅ Upload successful!
echo.
echo Next steps on VPS:
echo    ssh %VPS_USER%@%VPS_IP%
echo    cd /opt
echo    sudo unzip %PACKAGE_FILE%
echo    sudo mv pzem-monitoring-ubuntu pzem-monitoring
echo    sudo chown -R $USER:$USER /opt/pzem-monitoring
echo    cd pzem-monitoring
echo    chmod +x ubuntu-deploy.sh
echo    sudo ./ubuntu-deploy.sh
goto :end

:end
echo.
echo ========================================
echo  Upload Complete!
echo ========================================
echo.
pause











