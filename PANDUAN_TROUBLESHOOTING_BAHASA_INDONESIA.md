# 🔧 Cara Mengatasi Masalah "Status PENDING" - PZEM Monitoring

## 📌 Ringkasan Masalah Anda

Dari screenshot yang Anda tunjukkan (https://pzem.moof-set.web.id/):
- ❌ **Status**: PENDING - sistem tidak merespons
- ❌ **Response time**: N/A - tidak ada respons
- ❌ **Uptime 24 jam**: 65.93% - terlalu rendah (harusnya >99%)
- ❌ **Grafik monitoring**: Banyak bar merah/orange - menandakan sering down

---

## ⚡ Solusi Super Cepat (5-10 Menit)

### Langkah 1: Diagnosis Otomatis

Saya sudah buatkan script yang akan otomatis mengecek semua masalah.

**Jika Anda pakai Windows:**
1. Buka PowerShell
2. Jalankan:
```powershell
cd "C:\Users\info\Documents\Project\not-released\IoT-Project\PZEM-Project\.github"
.\diagnose-vps.ps1
```

**Jika Anda pakai Linux/Mac:**
1. Buka Terminal
2. Jalankan:
```bash
cd ~/path/ke/project/.github
chmod +x diagnose-vps.sh
./diagnose-vps.sh
```

Script ini akan mengecek:
- ✅ Apakah VPS masih hidup?
- ✅ Apakah bisa SSH ke VPS?
- ✅ Apakah Docker jalan?
- ✅ Apakah semua container (dashboard, mqtt, database) running?
- ✅ Apakah port 5000 terbuka?
- ✅ Apakah dashboard bisa diakses?
- ✅ Apakah ada error di log?

### Langkah 2: Baca Hasil Diagnosis

Script akan menampilkan hasil pemeriksaan. Biasanya masalahnya adalah salah satu dari ini:

#### Masalah A: Container Mati atau Restart Terus
**Tanda-tanda:**
- Script bilang "Container not running" atau "Restarting"
- Ada error di log container

**Solusi:**
```bash
# 1. SSH ke VPS
ssh -i ~/.ssh/foom-vps foom@103.31.39.189

# 2. Masuk ke folder project
cd /opt/pzem-monitoring

# 3. Restart containers
bash quick-fix.sh restart

# 4. Tunggu 30 detik, lalu cek
bash quick-fix.sh check
```

#### Masalah B: Database Error
**Tanda-tanda:**
- Log bilang "Connection refused" atau "Database error"
- Dashboard error waktu akses data

**Solusi:**
```bash
# 1. SSH ke VPS
ssh -i ~/.ssh/foom-vps foom@103.31.39.189

# 2. Restart database dulu
docker restart pzem-monitoring-db-1

# 3. Tunggu 10 detik
sleep 10

# 4. Restart dashboard & mqtt
docker restart pzem-monitoring-dashboard-1
docker restart pzem-monitoring-mqtt-listener-1

# 5. Cek status
cd /opt/pzem-monitoring
bash quick-fix.sh check
```

#### Masalah C: Port 5000 Tidak Bisa Diakses dari Luar
**Tanda-tanda:**
- Script bilang "Port not accessible from external"
- Bisa akses dari dalam VPS tapi tidak dari browser

**Solusi:**
```bash
# 1. SSH ke VPS
ssh -i ~/.ssh/foom-vps foom@103.31.39.189

# 2. Buka firewall untuk port 5000
sudo ufw allow 5000/tcp
sudo ufw reload

# 3. Restart nginx (kalau pakai domain)
sudo systemctl restart nginx

# 4. Restart containers
cd /opt/pzem-monitoring
bash quick-fix.sh restart
```

#### Masalah D: Memory atau Disk Penuh
**Tanda-tanda:**
- Script bilang "Memory usage >90%" atau "Disk full"
- VPS lemot atau container sering mati

**Solusi:**
```bash
# 1. SSH ke VPS
ssh -i ~/.ssh/foom-vps foom@103.31.39.189

# 2. Hapus cache Docker
cd /opt/pzem-monitoring
bash quick-fix.sh clearcache

# 3. Hapus log lama
bash quick-fix.sh clearlog

# 4. Restart
bash quick-fix.sh restart

# 5. Cek disk space
df -h /
```

### Langkah 3: Verifikasi Sudah Beres

Setelah fix, cek apakah sudah bener:

```bash
# 1. SSH ke VPS (kalau belum)
ssh -i ~/.ssh/foom-vps foom@103.31.39.189

# 2. Cek status lengkap
cd /opt/pzem-monitoring
bash quick-fix.sh check

# 3. Test health endpoint
curl http://localhost:5000/health
# Harusnya dapat respons: {"status": "healthy", ...}

# 4. Cek semua container running
docker ps
# Harusnya ada 3 containers dengan status "Up"
```

**Lalu buka browser:**
- https://pzem.moof-set.web.id
- Harusnya dashboard sudah bisa diakses

**Tunggu 5-10 menit**, lalu cek monitoring service Anda:
- Status harusnya berubah dari PENDING jadi **UP**
- Response time muncul (tidak N/A lagi)
- Bar di grafik mulai hijau

---

## 🆘 Jika Masih Bermasalah - Nuclear Option

Kalau semua cara di atas tidak berhasil, ada "full reset":

```bash
# 1. SSH ke VPS
ssh -i ~/.ssh/foom-vps foom@103.31.39.189

# 2. Full reset (database tetap aman)
cd /opt/pzem-monitoring
bash quick-fix.sh reset

# Script akan:
# - Backup database otomatis
# - Stop semua containers
# - Hapus cache
# - Rebuild semua
# - Start ulang

# 3. Tunggu selesai (sekitar 2-3 menit)

# 4. Verify
bash quick-fix.sh check
```

---

## 📊 Monitoring Service Configuration

Kalau Anda pakai uptime monitoring service (kayak UptimeRobot, StatusCake, dll), sebaiknya setting seperti ini:

### Setting yang Lebih Baik:

1. **Monitor Type**: HTTP(s)
2. **URL**: Ganti jadi `https://pzem.moof-set.web.id/health` 
   - Lebih reliable daripada homepage
3. **Check Interval**: 60 seconds (sudah OK)
4. **Timeout**: Ganti jadi **15 seconds** (dari default 5s)
   - Kadang VPS butuh waktu lebih lama untuk respond
5. **Expected Status Code**: 200
6. **Expected Keyword**: `healthy` (optional tapi recommended)

### Buat 2-3 Monitors:

Untuk monitoring lebih bagus, buat beberapa monitor:

**Monitor 1 - Primary (Domain + Health):**
- URL: `https://pzem.moof-set.web.id/health`
- Interval: 60s
- Priority: High

**Monitor 2 - Fallback (IP Direct):**
- URL: `http://103.31.39.189:5000/health`
- Interval: 60s
- Priority: Medium

**Monitor 3 - Homepage:**
- URL: `https://pzem.moof-set.web.id/`
- Interval: 300s (5 menit aja)
- Priority: Low

Dengan cara ini, kalau domain bermasalah tapi VPS OK, Anda tetap tahu sistemnya jalan.

---

## 🔄 Maintenance Rutin (Agar Tidak Bermasalah Lagi)

Untuk mencegah masalah berulang:

### Setup Cron Job (Otomatis):

```bash
# 1. SSH ke VPS
ssh -i ~/.ssh/foom-vps foom@103.31.39.189

# 2. Edit crontab
crontab -e

# 3. Tambahkan baris ini (tekan i untuk insert):

# Clear logs setiap minggu (Minggu jam 2 pagi)
0 2 * * 0 /opt/pzem-monitoring/quick-fix.sh clearlog

# Health check setiap jam (simpan ke log)
0 * * * * /opt/pzem-monitoring/quick-fix.sh check >> /var/log/pzem-health.log 2>&1

# Backup database setiap hari (jam 3 pagi)
0 3 * * * docker exec pzem-monitoring-db-1 pg_dump -U postgres pzem_monitoring > ~/.pzem-backups/daily_$(date +\%Y\%m\%d).sql

# Restart containers setiap hari (jam 4 pagi) - optional
0 4 * * * cd /opt/pzem-monitoring && bash quick-fix.sh restart

# 4. Save (tekan Esc, lalu ketik :wq)
```

### Manual Check Seminggu Sekali:

```bash
# SSH ke VPS
ssh -i ~/.ssh/foom-vps foom@103.31.39.189

# Cek status
cd /opt/pzem-monitoring
bash quick-fix.sh check

# Cek disk space
df -h

# Cek memory
free -h

# Cek logs (pastikan tidak ada error banyak)
docker logs --tail 50 pzem-monitoring-dashboard-1
```

---

## ✅ Checklist Setelah Fix

Pastikan semua ini OK:

- [ ] `docker ps` menunjukkan 3 containers dengan status "Up"
- [ ] `curl http://localhost:5000/health` return `{"status": "healthy", ...}`
- [ ] Dashboard bisa dibuka di browser: https://pzem.moof-set.web.id
- [ ] Monitoring service menunjukkan status "UP" (tidak PENDING lagi)
- [ ] Response time muncul (tidak N/A lagi)
- [ ] Memory usage <80% (`free -h`)
- [ ] Disk usage <80% (`df -h`)
- [ ] Tidak ada error di logs (`docker-compose logs`)

---

## 📚 Dokumentasi Tambahan

Kalau butuh info lebih detail:

| File | Isi |
|------|-----|
| `QUICK_FIX_PENDING.md` | Panduan singkat (yang ini) |
| `.github/TROUBLESHOOTING_SUMMARY.md` | Summary semua tools |
| `.github/TROUBLESHOOTING_README.md` | Overview tools lengkap |
| `.github/TROUBLESHOOTING_PENDING_STATUS.md` | Panduan super detail |

---

## 💡 Tips Tambahan

1. **Simpan SSH command**: Buat shortcut di terminal/PowerShell Anda:
   ```bash
   # Tambahkan ke ~/.bashrc atau ~/.zshrc (Linux/Mac)
   alias pzem-ssh='ssh -i ~/.ssh/foom-vps foom@103.31.39.189'
   alias pzem-check='pzem-ssh "cd /opt/pzem-monitoring && bash quick-fix.sh check"'
   
   # Setelah itu tinggal ketik:
   pzem-ssh
   pzem-check
   ```

2. **Bookmark URLs penting**:
   - Dashboard: https://pzem.moof-set.web.id
   - Health: https://pzem.moof-set.web.id/health
   - VPS Direct: http://103.31.39.189:5000

3. **Install tools di lokal** (optional tapi helpful):
   ```bash
   # Install jq untuk format JSON
   # Ubuntu/Debian
   sudo apt install jq
   
   # Mac
   brew install jq
   
   # Windows
   # Download dari: https://stedolan.github.io/jq/download/
   ```

---

## 🆘 Kalau Masih Bingung

Kalau masih ada masalah atau bingung:

1. **Simpan output diagnosis:**
   ```powershell
   # Windows
   cd .github
   .\diagnose-vps.ps1 > hasil-diagnosis.txt
   ```
   
   ```bash
   # Linux/Mac
   cd .github
   ./diagnose-vps.sh > hasil-diagnosis.txt
   ```

2. **Simpan logs dari VPS:**
   ```bash
   ssh -i ~/.ssh/foom-vps foom@103.31.39.189 "cd /opt/pzem-monitoring && docker-compose logs" > semua-logs.txt
   ```

3. **Share kedua file** (`hasil-diagnosis.txt` dan `semua-logs.txt`) untuk analisis lebih lanjut

---

## 🎯 Expected Timeline

Setelah fix:
- **5 menit pertama**: Containers mulai running
- **10 menit**: Health check mulai OK
- **15-30 menit**: Monitoring service detect system is UP
- **24 jam**: Uptime percentage mulai naik (dari 65.93% → 90%+)
- **7 hari**: Uptime stabil di >99%

---

**Dibuat**: 2026-01-17  
**Untuk**: Masalah "Status PENDING" di PZEM Monitoring System  
**Versi**: 1.0 - Bahasa Indonesia

---

## 🚀 Mulai Sekarang

```bash
# STEP 1: Diagnosis
cd .github
./diagnose-vps.sh

# STEP 2: Quick Fix
ssh -i ~/.ssh/foom-vps foom@103.31.39.189
cd /opt/pzem-monitoring
bash quick-fix.sh restart

# STEP 3: Verify
bash quick-fix.sh check

# DONE! ✅
```

**Selamat mencoba! Jika butuh bantuan lebih lanjut, jangan ragu untuk bertanya.** 👍
