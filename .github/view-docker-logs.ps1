# Script PowerShell untuk melihat logs Docker container dari Windows (via SSH)

param(
    [string]$Service = "all",  # all, dashboard, mqtt, db
    [int]$Lines = 100,
    [switch]$Follow = $false
)

# Konfigurasi SSH
$VPS_USER = "foom"
$VPS_HOST = "103.31.39.189"
$SSH_KEY = "C:\Users\info\.ssh\github_actions_vps"
$DEPLOY_DIR = "/opt/pzem-monitoring"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Docker Logs Viewer - PZEM Monitoring" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function untuk menampilkan logs
function Show-Logs {
    param(
        [string]$ContainerName,
        [string]$ServiceName,
        [int]$LogLines = 100,
        [bool]$IsFollow = $false
    )
    
    Write-Host "========================================" -ForegroundColor Blue
    Write-Host "📋 Logs: $ServiceName ($ContainerName)" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Blue
    
    if ($IsFollow) {
        Write-Host "Following logs (Ctrl+C to exit)..." -ForegroundColor Green
        ssh -i $SSH_KEY ${VPS_USER}@${VPS_HOST} "docker logs -f $ContainerName"
    } else {
        ssh -i $SSH_KEY ${VPS_USER}@${VPS_HOST} "docker logs --tail $LogLines $ContainerName"
    }
    Write-Host ""
}

# Function untuk menggunakan docker-compose logs
function Show-ComposeLogs {
    param(
        [string]$ServiceName = "",
        [int]$LogLines = 100,
        [bool]$IsFollow = $false
    )
    
    $followFlag = if ($IsFollow) { "-f" } else { "" }
    $linesFlag = if (-not $IsFollow) { "--tail $LogLines" } else { "" }
    
    if ($ServiceName -ne "") {
        Write-Host "========================================" -ForegroundColor Blue
        Write-Host "📋 Logs: $ServiceName" -ForegroundColor Yellow
        Write-Host "========================================" -ForegroundColor Blue
        ssh -i $SSH_KEY ${VPS_USER}@${VPS_HOST} "cd $DEPLOY_DIR && docker-compose logs $followFlag $linesFlag $ServiceName 2>/dev/null || docker compose logs $followFlag $linesFlag $ServiceName"
    } else {
        ssh -i $SSH_KEY ${VPS_USER}@${VPS_HOST} "cd $DEPLOY_DIR && docker-compose logs $followFlag $linesFlag 2>/dev/null || docker compose logs $followFlag $linesFlag"
    }
    Write-Host ""
}

# Main logic
switch ($Service.ToLower()) {
    "all" {
        if ($Follow) {
            Write-Host "Following logs dari semua container (Ctrl+C to exit)..." -ForegroundColor Green
            Show-ComposeLogs -IsFollow $true
        } else {
            Write-Host "Menampilkan logs terakhir $Lines baris dari semua container..." -ForegroundColor Green
            Write-Host ""
            Show-Logs -ContainerName "pzem-monitoring-db-1" -ServiceName "Database" -LogLines $Lines
            Show-Logs -ContainerName "pzem-monitoring-dashboard-1" -ServiceName "Dashboard" -LogLines $Lines
            Show-Logs -ContainerName "pzem-monitoring-mqtt-listener-1" -ServiceName "MQTT Listener" -LogLines $Lines
        }
    }
    "dashboard" {
        if ($Follow) {
            Show-Logs -ContainerName "pzem-monitoring-dashboard-1" -ServiceName "Dashboard" -IsFollow $true
        } else {
            Show-Logs -ContainerName "pzem-monitoring-dashboard-1" -ServiceName "Dashboard" -LogLines $Lines
        }
    }
    "mqtt" {
        if ($Follow) {
            Show-Logs -ContainerName "pzem-monitoring-mqtt-listener-1" -ServiceName "MQTT Listener" -IsFollow $true
        } else {
            Show-Logs -ContainerName "pzem-monitoring-mqtt-listener-1" -ServiceName "MQTT Listener" -LogLines $Lines
        }
    }
    "db" {
        if ($Follow) {
            Show-Logs -ContainerName "pzem-monitoring-db-1" -ServiceName "Database" -IsFollow $true
        } else {
            Show-Logs -ContainerName "pzem-monitoring-db-1" -ServiceName "Database" -LogLines $Lines
        }
    }
    default {
        Write-Host "Penggunaan:" -ForegroundColor Yellow
        Write-Host "  .\view-docker-logs.ps1 [-Service <all|dashboard|mqtt|db>] [-Lines <number>] [-Follow]"
        Write-Host ""
        Write-Host "Contoh:" -ForegroundColor Cyan
        Write-Host "  .\view-docker-logs.ps1 -Service all -Lines 50"
        Write-Host "  .\view-docker-logs.ps1 -Service dashboard -Follow"
        Write-Host "  .\view-docker-logs.ps1 -Service mqtt -Lines 200"
        exit 1
    }
}

Write-Host "✅ Selesai" -ForegroundColor Green