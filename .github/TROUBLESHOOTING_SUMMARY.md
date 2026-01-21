# 📊 Summary - Troubleshooting Tools untuk PZEM Monitoring

## 🎯 Masalah yang Anda Laporkan

Berdasarkan screenshot monitoring https://pzem.moof-set.web.id/:

| Metrik | Nilai Saat Ini | Target | Status |
|--------|----------------|--------|--------|
| **Status** | PENDING | UP | ❌ |
| **Response** | N/A | <2000ms | ❌ |
| **Uptime 24h** | 65.93% | >99% | ❌ |
| **Grafik** | Banyak merah/orange | Hijau semua | ❌ |

---

## 📦 Tools yang Telah Dibuat

Saya telah membuat tools lengkap untuk membantu Anda mendiagnosis dan memperbaiki masalah:

### 1. Diagnosis Scripts

| File | Platform | Lokasi | Fungsi |
|------|----------|--------|--------|
| `diagnose-vps.ps1` | Windows | `.github/` | Script diagnosis otomatis (PowerShell) |
| `diagnose-vps.sh` | Linux/Mac | `.github/` | Script diagnosis otomatis (Bash) |

**Apa yang diperiksa:**
- ✅ Koneksi SSH ke VPS
- ✅ Status Docker service
- ✅ Status semua containers (dashboard, mqtt, db)
- ✅ Port 5000 accessibility (internal & external)
- ✅ HTTP response & health endpoint
- ✅ Domain accessibility (HTTPS)
- ✅ Container logs (20 baris terakhir)
- ✅ VPS resource usage (CPU, Memory, Disk)

### 2. Quick Fix Scripts

| File | Lokasi | Fungsi |
|------|--------|--------|
| `quick-fix.sh` | `.github/` & `pzem-monitoring/V9-Docker/` | Script fix otomatis |

**Commands tersedia:**
- `restart` - Restart semua containers (paling sering dipakai)
- `rebuild` - Rebuild & restart containers
- `clearlog` - Clear semua logs
- `clearcache` - Clear Docker cache
- `reset` - Full reset (LAST RESORT)
- `check` - Check system status

### 3. Documentation

| File | Deskripsi |
|------|-----------|
| `QUICK_FIX_PENDING.md` | Quick guide 5 menit untuk fix masalah |
| `.github/TROUBLESHOOTING_README.md` | Overview semua tools |
| `.github/TROUBLESHOOTING_PENDING_STATUS.md` | Panduan lengkap step-by-step |

---

## 🚀 Cara Menggunakan

### Option 1: Quick Fix (Recommended)

1. **Jalankan Diagnosis:**

   **Windows:**
   ```powershell
   cd .github
   .\diagnose-vps.ps1
   ```

   **Linux/Mac:**
   ```bash
   cd .github
   chmod +x diagnose-vps.sh
   ./diagnose-vps.sh
   ```

2. **Baca hasil diagnosis** - script akan memberitahu masalahnya

3. **Fix sesuai masalah:**

   SSH ke VPS:
   ```bash
   ssh -i ~/.ssh/foom-vps foom@103.31.39.189
   cd /opt/pzem-monitoring
   ```

   Quick restart:
   ```bash
   bash quick-fix.sh restart
   ```

4. **Verify:**
   ```bash
   bash quick-fix.sh check
   curl http://localhost:5000/health
   ```

### Option 2: Manual Troubleshooting

Ikuti panduan lengkap di: `.github/TROUBLESHOOTING_PENDING_STATUS.md`

---

## 🔍 Common Issues & Solutions

### Issue 1: Container Restart Loop
**Gejala:** Container terus restart, status "Restarting"  
**Solusi:** `bash quick-fix.sh restart`

### Issue 2: Database Connection Error
**Gejala:** Dashboard error "Connection refused"  
**Solusi:** 
```bash
docker restart pzem-monitoring-db-1
sleep 10
docker restart pzem-monitoring-dashboard-1
```

### Issue 3: Port 5000 Not Accessible
**Gejala:** Curl dari luar VPS failed  
**Solusi:** 
```bash
sudo ufw allow 5000/tcp
sudo ufw reload
bash quick-fix.sh restart
```

### Issue 4: Memory/Disk Full
**Gejala:** VPS slow, containers crash  
**Solusi:** 
```bash
bash quick-fix.sh clearcache
bash quick-fix.sh restart
```

### Issue 5: Domain Not Accessible
**Gejala:** HTTPS error atau 502 Bad Gateway  
**Solusi:** 
```bash
sudo systemctl restart nginx
bash quick-fix.sh restart
```

---

## 📋 Pre-Flight Checklist

Sebelum troubleshooting, pastikan:

- [ ] SSH key ada di `~/.ssh/foom-vps` (Windows: `C:\Users\[user]\.ssh\foom-vps`)
- [ ] Bisa SSH ke VPS: `ssh -i ~/.ssh/foom-vps foom@103.31.39.189`
- [ ] VPS masih running (tidak down)
- [ ] Internet connection OK

---

## 🎯 Success Indicators

Setelah fix berhasil, Anda akan melihat:

**Di Monitoring Dashboard (https://pzem.moof-set.web.id/):**
- ✅ Status: **UP** (bukan PENDING)
- ✅ Response: **<2000ms** (bukan N/A)
- ✅ Uptime 24h: **>99%** (bukan 65.93%)
- ✅ Grafik: **Bar hijau semua** (bukan merah/orange)

**Di VPS:**
```bash
# All containers running
docker ps
# Output: 3 containers dengan status "Up"

# Health check OK
curl http://localhost:5000/health
# Output: {"status": "healthy", ...}

# Resources OK
free -h
# Output: Memory usage < 80%

df -h
# Output: Disk usage < 80%
```

---

## 🔄 Maintenance Schedule

Untuk mencegah masalah berulang, setup cron job:

```bash
# Edit crontab
crontab -e

# Add:
# Clear logs setiap minggu
0 2 * * 0 /opt/pzem-monitoring/quick-fix.sh clearlog

# Health check setiap jam
0 * * * * /opt/pzem-monitoring/quick-fix.sh check >> /var/log/pzem-health.log 2>&1

# Backup database setiap hari
0 3 * * * docker exec pzem-monitoring-db-1 pg_dump -U postgres pzem_monitoring > ~/.pzem-backups/daily_$(date +\%Y\%m\%d).sql
```

---

## 🆘 Emergency Contacts

**VPS Info:**
- Host: `103.31.39.189`
- User: `foom`
- SSH Key: `~/.ssh/foom-vps`
- Deploy Dir: `/opt/pzem-monitoring`

**URLs:**
- Domain: https://pzem.moof-set.web.id
- Direct IP: http://103.31.39.189:5000
- Health: http://103.31.39.189:5000/health

**GitHub Actions:**
- CI Workflow: `.github/workflows/ci.yml`
- CD Workflow: `.github/workflows/deploy.yml`

---

## 📞 Get Additional Help

Jika masih ada masalah setelah mengikuti panduan:

1. **Collect diagnostic info:**
   ```bash
   # Windows
   .github\diagnose-vps.ps1 > diagnostic-output.txt
   
   # Linux/Mac
   .github/diagnose-vps.sh > diagnostic-output.txt
   ```

2. **Collect logs dari VPS:**
   ```bash
   ssh -i ~/.ssh/foom-vps foom@103.31.39.189
   cd /opt/pzem-monitoring
   docker-compose logs > all-logs.txt
   ```

3. **Share files:**
   - `diagnostic-output.txt`
   - `all-logs.txt`

---

## 📚 Documentation Index

| Document | Purpose | When to Use |
|----------|---------|-------------|
| `QUICK_FIX_PENDING.md` | Quick 5-minute guide | Ketika sistem down dan butuh fix cepat |
| `.github/TROUBLESHOOTING_README.md` | Tools overview | Memahami tools yang tersedia |
| `.github/TROUBLESHOOTING_PENDING_STATUS.md` | Detailed troubleshooting | Untuk diagnosis mendalam |
| `.github/DOCKER_STATUS_CHECK_GUIDE.md` | Docker monitoring | Cek status Docker containers |
| `pzem-monitoring/V9-Docker/QUICK_FIX_VPS.md` | VPS quick fixes | Fix masalah VPS umum |

---

## ✅ Next Steps

1. **Immediate:** Jalankan diagnosis script untuk identifikasi masalah
2. **Short-term:** Fix masalah sesuai output diagnosis
3. **Long-term:** Setup monitoring & maintenance schedule

---

**Created**: 2026-01-17  
**Version**: 1.0  
**Status**: Ready to Use ✅

---

## 🎬 Quick Start Commands

```bash
# 1. DIAGNOSIS (dari komputer lokal)
cd .github
./diagnose-vps.sh

# 2. FIX (SSH ke VPS)
ssh -i ~/.ssh/foom-vps foom@103.31.39.189
cd /opt/pzem-monitoring
bash quick-fix.sh restart

# 3. VERIFY
bash quick-fix.sh check
curl http://localhost:5000/health

# 4. MONITOR (buka di browser)
# https://pzem.moof-set.web.id
```

---

Semua tools sudah siap digunakan! 🚀
