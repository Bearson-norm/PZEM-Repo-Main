# ========================================
# PZEM Monitoring VPS Diagnosis Script
# ========================================
# Script untuk troubleshooting masalah monitoring system
#
# Masalah yang ditemukan:
# - Status: Pending (tidak merespons)
# - Response: N/A
# - Uptime 24 jam: 65.93% (sangat rendah)
# - Banyak red/orange bars di grafik monitoring
#
# ========================================

Write-Host "======================================" -ForegroundColor Cyan
Write-Host " PZEM Monitoring VPS Diagnosis Tool" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# VPS Configuration
$VPS_USER = "foom"
$VPS_HOST = "103.31.39.189"
$SSH_KEY = "$env:USERPROFILE\.ssh\foom-vps"
$VPS_DEPLOY_DIR = "/opt/pzem-monitoring"
$DASHBOARD_PORT = 5000
$DOMAIN = "pzem.moof-set.web.id"

# Check if SSH key exists
Write-Host "[1/10] Checking SSH Key..." -ForegroundColor Yellow
if (Test-Path $SSH_KEY) {
    Write-Host "  ✅ SSH key found: $SSH_KEY" -ForegroundColor Green
} else {
    Write-Host "  ❌ SSH key not found: $SSH_KEY" -ForegroundColor Red
    Write-Host "  Please ensure your SSH key exists at the correct path" -ForegroundColor Red
    exit 1
}

# Test SSH Connection
Write-Host "`n[2/10] Testing SSH Connection..." -ForegroundColor Yellow
$sshTest = ssh -i $SSH_KEY -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "echo 'SSH OK'" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ SSH connection successful" -ForegroundColor Green
} else {
    Write-Host "  ❌ SSH connection failed" -ForegroundColor Red
    Write-Host "  Error: $sshTest" -ForegroundColor Red
    Write-Host "`n  Possible causes:" -ForegroundColor Yellow
    Write-Host "  - VPS is down or unreachable" -ForegroundColor Yellow
    Write-Host "  - Firewall blocking SSH (port 22)" -ForegroundColor Yellow
    Write-Host "  - SSH key not authorized on VPS" -ForegroundColor Yellow
    Write-Host "  - Network connectivity issues" -ForegroundColor Yellow
    exit 1
}

# Check VPS is reachable
Write-Host "`n[3/10] Pinging VPS..." -ForegroundColor Yellow
$pingResult = Test-Connection -ComputerName $VPS_HOST -Count 3 -Quiet
if ($pingResult) {
    Write-Host "  ✅ VPS is reachable" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  VPS ping failed (may be normal if ICMP blocked)" -ForegroundColor Yellow
}

# Check Docker status
Write-Host "`n[4/10] Checking Docker Status..." -ForegroundColor Yellow
$dockerStatus = ssh -i $SSH_KEY "$VPS_USER@$VPS_HOST" "docker --version && systemctl is-active docker" 2>&1
Write-Host "  Docker info:" -ForegroundColor Cyan
Write-Host "  $dockerStatus" -ForegroundColor Gray

if ($dockerStatus -match "active") {
    Write-Host "  ✅ Docker service is running" -ForegroundColor Green
} else {
    Write-Host "  ❌ Docker service is not running" -ForegroundColor Red
}

# Check Docker Containers
Write-Host "`n[5/10] Checking Docker Containers..." -ForegroundColor Yellow
$containers = ssh -i $SSH_KEY "$VPS_USER@$VPS_HOST" "cd $VPS_DEPLOY_DIR && docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'" 2>&1
Write-Host "$containers" -ForegroundColor Gray

$containerCount = ssh -i $SSH_KEY "$VPS_USER@$VPS_HOST" "docker ps --filter 'name=pzem' --quiet | wc -l" 2>&1
Write-Host "`n  Found $containerCount PZEM containers running" -ForegroundColor Cyan

if ([int]$containerCount -lt 3) {
    Write-Host "  ⚠️  Expected 3 containers (dashboard, mqtt-listener, db) but found $containerCount" -ForegroundColor Yellow
} else {
    Write-Host "  ✅ All containers are running" -ForegroundColor Green
}

# Check Container Health
Write-Host "`n[6/10] Checking Container Health..." -ForegroundColor Yellow
$containerHealth = ssh -i $SSH_KEY "$VPS_USER@$VPS_HOST" @"
cd $VPS_DEPLOY_DIR
echo "Dashboard container:"
docker ps --filter "name=dashboard" --format "Status: {{.Status}}"
echo ""
echo "MQTT Listener container:"
docker ps --filter "name=mqtt" --format "Status: {{.Status}}"
echo ""
echo "Database container:"
docker ps --filter "name=db" --format "Status: {{.Status}}"
"@
Write-Host "$containerHealth" -ForegroundColor Gray

# Check Port Accessibility
Write-Host "`n[7/10] Checking Port Accessibility..." -ForegroundColor Yellow
Write-Host "  Testing port $DASHBOARD_PORT on VPS..." -ForegroundColor Cyan

$portTest = ssh -i $SSH_KEY "$VPS_USER@$VPS_HOST" "netstat -tlnp 2>/dev/null | grep :$DASHBOARD_PORT || ss -tlnp 2>/dev/null | grep :$DASHBOARD_PORT" 2>&1
if ($portTest) {
    Write-Host "  ✅ Port $DASHBOARD_PORT is listening on VPS" -ForegroundColor Green
    Write-Host "  $portTest" -ForegroundColor Gray
} else {
    Write-Host "  ❌ Port $DASHBOARD_PORT is NOT listening" -ForegroundColor Red
    Write-Host "  Dashboard service may not be running properly" -ForegroundColor Red
}

# Test HTTP Response from VPS (internal)
Write-Host "`n[8/10] Testing HTTP Response (from VPS internal)..." -ForegroundColor Yellow
$httpInternal = ssh -i $SSH_KEY "$VPS_USER@$VPS_HOST" "curl -s -o /dev/null -w '%{http_code}' -m 5 http://localhost:$DASHBOARD_PORT/ || echo 'FAILED'" 2>&1
if ($httpInternal -eq "200") {
    Write-Host "  ✅ Dashboard responds with HTTP 200 (internal)" -ForegroundColor Green
} else {
    Write-Host "  ❌ Dashboard not responding (got: $httpInternal)" -ForegroundColor Red
}

# Test HTTP Response from external
Write-Host "`n[9/10] Testing HTTP Response (from external)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://$VPS_HOST`:$DASHBOARD_PORT/" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✅ Dashboard accessible externally (HTTP $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Dashboard not accessible externally" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`n  Possible causes:" -ForegroundColor Yellow
    Write-Host "  - Firewall blocking port $DASHBOARD_PORT" -ForegroundColor Yellow
    Write-Host "  - Dashboard container not running" -ForegroundColor Yellow
    Write-Host "  - Dashboard crashed or error" -ForegroundColor Yellow
}

# Test Domain (if configured)
Write-Host "`n[10/10] Testing Domain Access..." -ForegroundColor Yellow
try {
    $domainResponse = Invoke-WebRequest -Uri "https://$DOMAIN" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✅ Domain accessible (HTTPS $($domainResponse.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Domain not accessible" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Check Recent Logs
Write-Host "`n" -NoNewline
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Container Logs (Last 20 lines)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

Write-Host "`n--- Dashboard Logs ---" -ForegroundColor Yellow
$dashboardLogs = ssh -i $SSH_KEY "$VPS_USER@$VPS_HOST" "cd $VPS_DEPLOY_DIR && docker logs --tail 20 \$(docker ps --filter 'name=dashboard' -q) 2>&1 | tail -20" 2>&1
Write-Host "$dashboardLogs" -ForegroundColor Gray

Write-Host "`n--- MQTT Listener Logs ---" -ForegroundColor Yellow
$mqttLogs = ssh -i $SSH_KEY "$VPS_USER@$VPS_HOST" "cd $VPS_DEPLOY_DIR && docker logs --tail 20 \$(docker ps --filter 'name=mqtt' -q) 2>&1 | tail -20" 2>&1
Write-Host "$mqttLogs" -ForegroundColor Gray

Write-Host "`n--- Database Logs ---" -ForegroundColor Yellow
$dbLogs = ssh -i $SSH_KEY "$VPS_USER@$VPS_HOST" "cd $VPS_DEPLOY_DIR && docker logs --tail 20 \$(docker ps --filter 'name=db' -q) 2>&1 | tail -20" 2>&1
Write-Host "$dbLogs" -ForegroundColor Gray

# Summary
Write-Host "`n" -NoNewline
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " DIAGNOSIS SUMMARY" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "`nBased on the monitoring screenshot you provided:" -ForegroundColor White
Write-Host "  - Status: PENDING (not responding)" -ForegroundColor Red
Write-Host "  - 24h Uptime: 65.93% (should be >99%)" -ForegroundColor Red
Write-Host "  - Many red/orange bars in monitoring graph" -ForegroundColor Red
Write-Host ""
Write-Host "Common Causes:" -ForegroundColor Yellow
Write-Host "  1. Dashboard container crashed or restarting frequently" -ForegroundColor White
Write-Host "  2. Database connection issues" -ForegroundColor White
Write-Host "  3. Memory/resource exhaustion on VPS" -ForegroundColor White
Write-Host "  4. Network connectivity problems" -ForegroundColor White
Write-Host "  5. Firewall blocking external access" -ForegroundColor White
Write-Host ""
Write-Host "Recommended Actions:" -ForegroundColor Yellow
Write-Host "  1. Check the logs above for errors" -ForegroundColor White
Write-Host "  2. Verify all 3 containers are in 'Up' status" -ForegroundColor White
Write-Host "  3. Check VPS resources: CPU, Memory, Disk" -ForegroundColor White
Write-Host "  4. Test health endpoint: http://$VPS_HOST`:$DASHBOARD_PORT/health" -ForegroundColor White
Write-Host "  5. Restart containers if needed: cd $VPS_DEPLOY_DIR && docker-compose restart" -ForegroundColor White
Write-Host ""
Write-Host "For detailed fix guides, see:" -ForegroundColor Cyan
Write-Host "  - .github\DOCKER_STATUS_CHECK_GUIDE.md" -ForegroundColor Gray
Write-Host "  - pzem-monitoring\V9-Docker\QUICK_FIX_VPS.md" -ForegroundColor Gray
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
