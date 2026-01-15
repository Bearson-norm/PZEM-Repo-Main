@echo off
REM Script untuk Export Database PostgreSQL PZEM Monitoring (Windows)
REM Usage: export_database.bat [format] [output]

echo ========================================
echo PZEM Database Exporter
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python tidak ditemukan!
    echo Silakan install Python terlebih dahulu.
    pause
    exit /b 1
)

REM Set default values
set FORMAT=all
set OUTPUT=

REM Parse arguments
if not "%1"=="" set FORMAT=%1
if not "%2"=="" set OUTPUT=%2

REM Set database connection (ubah sesuai kebutuhan)
REM Atau gunakan environment variables: DB_HOST, DB_NAME, DB_USER, DB_PASS
set DB_HOST=localhost
set DB_NAME=pzem_monitoring
set DB_USER=postgres
set DB_PASS=Admin123

echo Konfigurasi Database:
echo   Host: %DB_HOST%
echo   Database: %DB_NAME%
echo   User: %DB_USER%
echo   Format: %FORMAT%
echo.

REM Run export script
if "%OUTPUT%"=="" (
    python export_database.py --format %FORMAT%
) else (
    python export_database.py --format %FORMAT% --output %OUTPUT%
)

if errorlevel 1 (
    echo.
    echo ERROR: Export gagal!
    pause
    exit /b 1
)

echo.
echo Export selesai!
pause



