# Panduan Memeriksa Status Docker di VPS

Panduan lengkap untuk memeriksa kondisi dan status Docker containers di VPS production.

---

## 🔍 PEMERIKSAAN DASAR

### 1. Status Container secara Umum

**Perintah:**
```bash
# Melihat semua container (running dan stopped)
docker ps -a

# Hanya container yang sedang running
docker ps

# Dengan format yang lebih detail
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"
```

**Contoh Output:**
```
NAMES                 STATUS         PORTS                    IMAGE
pzem-dashboard        Up 2 hours     0.0.0.0:5000->5000/tcp  pzem-dashboard:latest
pzem-mqtt-listener    Up 2 hours                              pzem-mqtt:latest
pzem-db               Up 2 hours     5432/tcp                 postgres:15
```

### 2. Status Menggunakan Docker Compose

**Jika menggunakan Docker Compose:**
```bash
# Masuk ke directory deployment
cd /opt/pzem-monitoring  # atau directory deployment Anda

# Status semua services
docker-compose ps

# Atau untuk Docker Compose v2
docker compose ps
```

**Contoh Output:**
```
NAME                  COMMAND                  SERVICE             STATUS          PORTS
pzem-monitoring-db-1  "docker-entrypoint.s…"   db                  running         5432/tcp
pzem-monitoring-dashboard-1  "python app_with_…"  dashboard  running  0.0.0.0:5000->5000/tcp
pzem-monitoring-mqtt-listener-1  "python mqtt_…"  mqtt-listener  running
```

---

## 📊 PEMERIKSAAN DETAIL

### 3. Resource Usage (CPU, Memory, Disk)

```bash
# Statistik real-time semua container
docker stats

# Statistik untuk container tertentu
docker stats pzem-dashboard

# Statistik tanpa streaming (sekali saja)
docker stats --no-stream

# Statistik dengan format khusus
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
```

**Contoh Output:**
```
CONTAINER           CPU %     MEM USAGE / LIMIT     NET I/O
pzem-dashboard      0.50%     120.5MiB / 2GiB      1.2MB / 800KB
pzem-mqtt-listener  0.30%     85.2MiB / 2GiB       500KB / 200KB
pzem-db             1.20%     180.3MiB / 2GiB      2.1MB / 1.5MB
```

### 4. Logs Container

```bash
# Logs dari container tertentu (tail)
docker logs pzem-dashboard

# Logs dengan follow (real-time)
docker logs -f pzem-dashboard

# Logs dengan limit baris
docker logs --tail 100 pzem-dashboard

# Logs dengan timestamp
docker logs -t pzem-dashboard

# Logs beberapa container sekaligus
docker-compose logs

# Logs service tertentu dengan follow
docker-compose logs -f dashboard

# Logs dari waktu tertentu
docker logs --since 10m pzem-dashboard  # 10 menit terakhir
docker logs --since 2024-01-01T10:00:00 pzem-dashboard
```

### 5. Inspect Container Detail

```bash
# Informasi lengkap container
docker inspect pzem-dashboard

# Informasi spesifik (contoh: IP address)
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' pzem-dashboard

# Informasi status
docker inspect -f '{{.State.Status}}' pzem-dashboard

# Informasi port mapping
docker port pzem-dashboard

# Informasi environment variables
docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' pzem-dashboard
```

---

## 🌐 PEMERIKSAAN NETWORK

### 6. Network Docker

```bash
# List semua network
docker network ls

# Inspect network tertentu
docker network inspect bridge

# List container yang terhubung ke network
docker network inspect bridge | grep -A 5 "Containers"
```

### 7. Port Checking

```bash
# Check port yang sedang digunakan
sudo netstat -tulpn | grep :5000

# Atau menggunakan ss
sudo ss -tulpn | grep :5000

# Check dari dalam container
docker exec pzem-dashboard netstat -tuln
```

---

## 💾 PEMERIKSAAN VOLUME DAN DATA

### 8. Docker Volumes

```bash
# List semua volumes
docker volume ls

# Inspect volume tertentu
docker volume inspect pzem-monitoring_pgdata

# Check penggunaan disk volumes
docker system df -v
```

**Contoh Output:**
```
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          3         3         1.2GB     0B (0%)
Containers      3         3         120MB     0B (0%)
Local Volumes   2         2         500MB     0B (0%)
Build Cache     0         0         0B        0B
```

### 9. Database Connectivity

```bash
# Test koneksi ke database dari container dashboard
docker exec pzem-dashboard python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='db',
        database='pzem_monitoring',
        user='postgres',
        password='Admin123'
    )
    print('✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
"

# Atau menggunakan psql langsung
docker exec -it pzem-db psql -U postgres -d pzem_monitoring -c "SELECT version();"
```

---

## 🔧 HEALTH CHECK

### 10. Health Check Endpoint

```bash
# Dari VPS
curl http://localhost:5000/health

# Dari lokal (Windows PowerShell)
Invoke-WebRequest -Uri http://103.31.39.189:5000/health

# Dengan verbose
curl -v http://localhost:5000/health

# Check HTTP status code
curl -o /dev/null -s -w "%{http_code}\n" http://localhost:5000/health
```

### 11. Docker Health Status

```bash
# Check health status dari docker inspect
docker inspect --format='{{.State.Health.Status}}' pzem-dashboard

# Health check logs
docker inspect --format='{{json .State.Health}}' pzem-dashboard | jq .
```

---

## 🚨 TROUBLESHOOTING COMMANDS

### 12. Container yang Tidak Running

```bash
# List container yang stopped
docker ps -a --filter "status=exited"

# Check logs container yang stopped
docker logs pzem-dashboard  # Works even if container is stopped

# Restart container
docker restart pzem-dashboard

# Atau menggunakan docker-compose
docker-compose restart dashboard
```

### 13. Container yang Crash Loop

```bash
# Check exit code
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.ExitCode}}"

# Check logs untuk error
docker logs --tail 200 pzem-dashboard

# Check events
docker events --since 10m
```

### 14. Resource Issues

```bash
# Check disk space
df -h

# Check Docker disk usage
docker system df

# Clean up unused resources
docker system prune -a  # Hati-hati, ini akan menghapus images yang tidak digunakan

# Check memory
free -h

# Check CPU usage
top
# atau
htop
```

---

## 📝 SCRIPT PEMERIKSAAN LENGKAP

### Script Quick Check (Bash)

Simpan sebagai `check-docker-status.sh`:

```bash
#!/bin/bash

echo "========================================"
echo "Docker Status Check"
echo "========================================"
echo ""

echo "📦 Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "💾 Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
echo ""

echo "🌐 Network:"
docker network ls
echo ""

echo "💿 Volumes:"
docker volume ls
echo ""

echo "🔍 Health Check:"
if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
fi
echo ""

echo "📊 Disk Usage:"
docker system df
echo ""

echo "========================================"
```

**Cara menggunakan:**
```bash
chmod +x check-docker-status.sh
./check-docker-status.sh
```

### Script Quick Check (PowerShell - untuk Windows)

Simpan sebagai `check-docker-status.ps1`:

```powershell
# Script untuk check Docker status dari Windows (via SSH)

$VPS_USER = "foom"
$VPS_HOST = "103.31.39.189"
$SSH_KEY = "C:\Users\info\.ssh\github_actions_vps"
$DEPLOY_DIR = "/opt/pzem-monitoring"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Docker Status Check (Remote VPS)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📦 Container Status:" -ForegroundColor Yellow
ssh -i $SSH_KEY ${VPS_USER}@${VPS_HOST} "cd ${DEPLOY_DIR} && docker-compose ps"
Write-Host ""

Write-Host "💾 Resource Usage:" -ForegroundColor Yellow
ssh -i $SSH_KEY ${VPS_USER}@${VPS_HOST} "docker stats --no-stream --format 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}'"
Write-Host ""

Write-Host "🔍 Health Check:" -ForegroundColor Yellow
$healthCheck = ssh -i $SSH_KEY ${VPS_USER}@${VPS_HOST} "curl -f -s http://localhost:5000/health"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Health check passed" -ForegroundColor Green
    Write-Host $healthCheck
} else {
    Write-Host "❌ Health check failed" -ForegroundColor Red
}
Write-Host ""

Write-Host "📊 Disk Usage:" -ForegroundColor Yellow
ssh -i $SSH_KEY ${VPS_USER}@${VPS_HOST} "docker system df"
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
```

**Cara menggunakan:**
```powershell
.\check-docker-status.ps1
```

---

## 🔄 COMMON OPERATIONS

### Start Services

```bash
cd /opt/pzem-monitoring
docker-compose up -d
```

### Stop Services

```bash
cd /opt/pzem-monitoring
docker-compose down
```

### Restart Services

```bash
cd /opt/pzem-monitoring
docker-compose restart
```

### Rebuild dan Restart

```bash
cd /opt/pzem-monitoring
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### View Real-time Logs

```bash
cd /opt/pzem-monitoring
docker-compose logs -f
```

---

## 📋 CHECKLIST RUTIN

### Harian:
- [ ] Check container status: `docker ps`
- [ ] Check resource usage: `docker stats --no-stream`
- [ ] Check health endpoint: `curl http://localhost:5000/health`

### Mingguan:
- [ ] Review logs: `docker-compose logs --tail 500`
- [ ] Check disk usage: `docker system df`
- [ ] Verify backup berjalan dengan baik

### Bulanan:
- [ ] Clean up unused resources: `docker system prune`
- [ ] Update Docker images
- [ ] Review security updates

---

## 🆘 QUICK TROUBLESHOOTING

| Problem | Command |
|---------|---------|
| Container tidak start | `docker logs [container-name]` |
| Port sudah digunakan | `sudo netstat -tulpn \| grep :5000` |
| Out of memory | `docker stats` → Check memory usage |
| Disk full | `docker system df` → Check volumes |
| Network issue | `docker network inspect bridge` |
| Database connection failed | `docker exec [container] psql -U postgres` |

---

## 📚 REFERENSI

- [Docker CLI Documentation](https://docs.docker.com/engine/reference/commandline/cli/)
- [Docker Compose Documentation](https://docs.docker.com/compose/reference/)
- [Docker Troubleshooting Guide](https://docs.docker.com/config/daemon/#troubleshooting)

---

**Panduan ini dapat digunakan untuk memonitor dan troubleshooting Docker containers di production environment.**