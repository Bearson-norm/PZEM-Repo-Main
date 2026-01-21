# 🩺 PZEM Monitoring - Troubleshooting Tools

Tools untuk mendiagnosis dan memperbaiki masalah pada PZEM Monitoring System.

## 📋 Masalah yang Anda Alami

Berdasarkan screenshot monitoring:
- ❌ **Status**: PENDING (tidak merespons)
- ❌ **Response**: N/A
- ❌ **Uptime 24 jam**: 65.93% (seharusnya >99%)
- ❌ **Grafik**: Banyak bar merah/orange

---

## 🚀 Langkah Pertama - Diagnosis Otomatis

### Windows (PowerShell)

```powershell
cd .github
.\diagnose-vps.ps1
```

### Linux/Mac (Bash)

```bash
cd .github
chmod +x diagnose-vps.sh
./diagnose-vps.sh
```

Script ini akan memeriksa:
- ✅ Koneksi SSH ke VPS
- ✅ Status Docker service  
- ✅ Status semua containers
- ✅ Port accessibility
- ✅ HTTP response
- ✅ Container logs
- ✅ Resource usage

---

## 🛠️ Quick Fix Tools

Jika diagnosis menunjukkan masalah, gunakan quick fix script:

### Di VPS (SSH ke VPS dulu)

```bash
ssh -i ~/.ssh/foom-vps foom@103.31.39.189
cd /opt/pzem-monitoring
```

### Quick Fix Options

```bash
# 1. Restart containers (paling cepat)
bash quick-fix.sh restart

# 2. Check status
bash quick-fix.sh check

# 3. Rebuild containers (jika restart tidak membantu)
bash quick-fix.sh rebuild

# 4. Clear logs (jika disk penuh)
bash quick-fix.sh clearlog

# 5. Clear Docker cache (jika disk penuh)
bash quick-fix.sh clearcache

# 6. Full reset (LAST RESORT)
bash quick-fix.sh reset
```

---

## 📖 Panduan Lengkap

Untuk troubleshooting detail, baca:
- **[TROUBLESHOOTING_PENDING_STATUS.md](TROUBLESHOOTING_PENDING_STATUS.md)** - Panduan lengkap step-by-step

---

## 🔍 Common Issues & Quick Solutions

### 1. Container Restart Terus-Menerus

**Cek:**
```bash
docker ps -a | grep pzem
docker logs pzem-monitoring-dashboard-1
```

**Fix:**
```bash
cd /opt/pzem-monitoring
docker-compose restart
```

### 2. Database Connection Error

**Cek:**
```bash
docker exec pzem-monitoring-db-1 pg_isready -U postgres
```

**Fix:**
```bash
docker restart pzem-monitoring-db-1
sleep 10
docker restart pzem-monitoring-dashboard-1
docker restart pzem-monitoring-mqtt-listener-1
```

### 3. Port 5000 Tidak Accessible

**Cek:**
```bash
# Internal
curl http://localhost:5000/health

# External (dari komputer lokal)
curl http://103.31.39.189:5000/health
```

**Fix:**
```bash
# Buka firewall
sudo ufw allow 5000/tcp
sudo ufw reload

# Restart containers
cd /opt/pzem-monitoring
docker-compose restart
```

### 4. Memory Habis

**Cek:**
```bash
free -h
docker stats --no-stream
```

**Fix:**
```bash
# Restart untuk free memory
docker-compose restart

# Clear Docker cache
docker image prune -a -f
docker container prune -f
```

### 5. Disk Penuh

**Cek:**
```bash
df -h /
```

**Fix:**
```bash
# Clear logs
bash quick-fix.sh clearlog

# Clear Docker cache
bash quick-fix.sh clearcache

# Remove old backups
rm -f ~/.pzem-backups/*backup*.sql
```

---

## 📊 Monitoring Configuration

Jika Anda menggunakan uptime monitoring service (UptimeRobot, StatusCake, dll):

### Recommended Settings:

1. **Monitor Type**: HTTP(s)
2. **URL**: `https://pzem.moof-set.web.id/health` (lebih reliable dari home page)
3. **Check Interval**: 60 seconds
4. **Timeout**: 15 seconds (bukan default 5 seconds)
5. **Expected Status**: 200
6. **Expected Keyword**: `"status": "healthy"`

### Multiple Monitors:

Untuk monitoring lebih baik, buat 3 monitors:

1. **Primary (Domain + Health)**
   - URL: `https://pzem.moof-set.web.id/health`
   - Interval: 60s
   
2. **Fallback (Direct IP + Health)**
   - URL: `http://103.31.39.189:5000/health`
   - Interval: 60s
   
3. **Main Page**
   - URL: `https://pzem.moof-set.web.id/`
   - Interval: 300s (5 minutes)

---

## 🔄 Preventive Maintenance

Untuk mencegah downtime, jalankan maintenance script secara berkala:

### Buat Cron Job

```bash
# Edit crontab
crontab -e

# Add these lines:

# Clear logs setiap minggu
0 2 * * 0 /opt/pzem-monitoring/quick-fix.sh clearlog

# Check status setiap jam
0 * * * * /opt/pzem-monitoring/quick-fix.sh check >> /var/log/pzem-health.log 2>&1

# Backup database setiap hari
0 3 * * * docker exec pzem-monitoring-db-1 pg_dump -U postgres pzem_monitoring > ~/.pzem-backups/daily_$(date +\%Y\%m\%d).sql
```

---

## 📞 Emergency Contact Info

**VPS Details:**
- User: `foom`
- Host: `103.31.39.189`
- Deploy Dir: `/opt/pzem-monitoring`
- SSH Key: `~/.ssh/foom-vps`

**URLs:**
- Domain: https://pzem.moof-set.web.id
- Direct IP: http://103.31.39.189:5000
- Health Check: http://103.31.39.189:5000/health

**GitHub Workflow:**
- CI: `.github/workflows/ci.yml`
- CD: `.github/workflows/deploy.yml`

---

## 📝 Get Help

Jika masih ada masalah setelah mengikuti panduan:

1. Jalankan diagnosis dan simpan output:
   ```bash
   # Windows
   .github\diagnose-vps.ps1 > diagnostic-report.txt
   
   # Linux/Mac
   .github/diagnose-vps.sh > diagnostic-report.txt
   ```

2. Collect logs:
   ```bash
   # Dari VPS
   cd /opt/pzem-monitoring
   docker-compose logs > all-logs.txt
   ```

3. Share kedua file tersebut untuk analisis lebih lanjut

---

## ✅ Success Indicators

Setelah fix, pastikan semua ini OK:

- [ ] `docker ps` menunjukkan 3 containers UP
- [ ] `curl http://localhost:5000/health` return status "healthy"
- [ ] Dashboard bisa diakses dari browser
- [ ] No errors di `docker-compose logs`
- [ ] Memory usage < 80%
- [ ] Disk usage < 80%
- [ ] Monitoring service shows "UP" status
- [ ] Uptime >99% dalam 24 jam ke depan

---

**Created**: 2026-01-17  
**Last Updated**: 2026-01-17  
**Version**: 1.0
