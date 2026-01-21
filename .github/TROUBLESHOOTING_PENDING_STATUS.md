# 🔍 Panduan Troubleshooting - Status PENDING di Monitoring

Dokumen ini dibuat untuk mengatasi masalah yang Anda alami berdasarkan screenshot monitoring:
- **Status**: PENDING (tidak merespons)
- **Response**: N/A
- **Uptime 24 jam**: 65.93% (sangat rendah, seharusnya >99%)
- **Grafik**: Banyak bar merah/orange menandakan kegagalan

---

## 🚀 Quick Fix - Jalankan Script Diagnosis

Saya telah membuat script otomatis untuk mendiagnosis masalah Anda:

### Windows (PowerShell):
```powershell
cd .github
.\diagnose-vps.ps1
```

### Linux/Mac (Bash):
```bash
cd .github
chmod +x diagnose-vps.sh
./diagnose-vps.sh
```

Script ini akan memeriksa:
1. ✅ Koneksi SSH ke VPS
2. ✅ Status Docker service
3. ✅ Status container (dashboard, mqtt, database)
4. ✅ Port accessibility
5. ✅ HTTP response (internal & external)
6. ✅ Domain accessibility
7. ✅ Container logs (20 baris terakhir)
8. ✅ Resource usage (CPU, Memory, Disk)

---

## 🔍 Diagnosis Manual (Step by Step)

Jika Anda ingin melakukan diagnosis manual, ikuti langkah berikut:

### 1. Cek Status Containers di VPS

```bash
ssh -i ~/.ssh/foom-vps foom@103.31.39.189
cd /opt/pzem-monitoring
docker ps
```

**Yang harus Anda lihat:**
- ✅ `pzem-monitoring-dashboard-1` - Status: Up
- ✅ `pzem-monitoring-mqtt-listener-1` - Status: Up  
- ✅ `pzem-monitoring-db-1` - Status: Up

**Jika ada yang tidak Up:**
```bash
# Lihat kenapa container mati
docker ps -a | grep pzem

# Lihat log container yang bermasalah
docker logs pzem-monitoring-dashboard-1
docker logs pzem-monitoring-mqtt-listener-1
docker logs pzem-monitoring-db-1
```

### 2. Cek Logs untuk Error

```bash
# Dashboard logs
docker logs --tail 50 pzem-monitoring-dashboard-1

# MQTT listener logs
docker logs --tail 50 pzem-monitoring-mqtt-listener-1

# Database logs
docker logs --tail 50 pzem-monitoring-db-1
```

**Error umum yang sering ditemukan:**

| Error Message | Penyebab | Solusi |
|--------------|----------|---------|
| `Connection refused` | Database belum ready | Restart containers: `docker-compose restart` |
| `Out of memory` | RAM habis | Lihat bagian "Resource Issues" di bawah |
| `Network error` | Container tidak bisa komunikasi | Restart Docker network |
| `Port already in use` | Port 5000 sudah dipakai | Stop service lain yang pakai port 5000 |
| `MQTT connection failed` | MQTT broker down | Cek ESP32/MQTT broker |

### 3. Cek Resource VPS (CPU, Memory, Disk)

```bash
# Memory usage
free -h

# Disk usage
df -h

# CPU load
top -bn1 | head -10

# Docker container stats
docker stats --no-stream
```

**Tanda-tanda resource habis:**
- Memory Usage > 90%
- Disk Usage > 90%
- Load Average > jumlah CPU core

### 4. Test Health Endpoint

```bash
# Dari dalam VPS
curl http://localhost:5000/health

# Dari luar VPS (dari komputer Anda)
curl http://103.31.39.189:5000/health

# Test domain
curl https://pzem.moof-set.web.id/health
```

**Response yang benar:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-17T...",
  "database": "connected",
  ...
}
```

### 5. Cek Firewall & Port

```bash
# Cek port yang listening
netstat -tlnp | grep 5000
# atau
ss -tlnp | grep 5000

# Cek firewall (Ubuntu/Debian)
sudo ufw status

# Pastikan port 5000 terbuka
sudo ufw allow 5000/tcp
```

---

## 🛠️ Solusi Berdasarkan Penyebab

### A. Container Restart Terus-Menerus

**Diagnosis:**
```bash
docker ps -a | grep pzem
# Lihat "STATUS" column - jika ada "Restarting" atau "Exited"
```

**Solusi:**
```bash
cd /opt/pzem-monitoring

# Stop semua
docker-compose down

# Start ulang dengan log
docker-compose up -d

# Monitor logs realtime
docker-compose logs -f
```

### B. Database Connection Error

**Diagnosis:**
```bash
# Test koneksi database
docker exec pzem-monitoring-db-1 pg_isready -U postgres
```

**Solusi:**
```bash
# Restart database container
docker restart pzem-monitoring-db-1

# Tunggu 10 detik
sleep 10

# Restart dashboard & mqtt
docker restart pzem-monitoring-dashboard-1
docker restart pzem-monitoring-mqtt-listener-1
```

### C. Memory/Resource Habis

**Diagnosis:**
```bash
free -h
docker stats --no-stream
```

**Solusi:**

1. **Restart containers untuk free up memory:**
```bash
cd /opt/pzem-monitoring
docker-compose restart
```

2. **Clear Docker cache:**
```bash
# Hapus unused images
docker image prune -a -f

# Hapus unused containers
docker container prune -f

# Hapus unused volumes (HATI-HATI: backup dulu!)
docker volume prune -f
```

3. **Tambah swap memory (jika RAM kecil):**
```bash
# Cek swap saat ini
free -h

# Buat swap 2GB (jika belum ada)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Permanent (tambah ke /etc/fstab)
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### D. Port Tidak Accessible dari Luar

**Diagnosis:**
```bash
# Dari dalam VPS - berhasil?
curl http://localhost:5000

# Dari luar VPS - gagal?
# (test dari komputer lokal Anda)
curl http://103.31.39.189:5000
```

**Solusi:**

1. **Buka firewall:**
```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 5000/tcp
sudo ufw reload

# Firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload

# iptables
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
sudo netfilter-persistent save
```

2. **Pastikan VPS provider tidak block port:**
- Login ke dashboard VPS (Vultr/DigitalOcean/dll)
- Cek Security Groups / Firewall settings
- Tambahkan rule untuk port 5000

### E. NGINX/SSL Issue (untuk domain)

**Diagnosis:**
```bash
# Cek nginx status
sudo systemctl status nginx

# Test nginx config
sudo nginx -t

# Lihat nginx error log
sudo tail -50 /var/log/nginx/error.log
```

**Solusi:**
```bash
# Restart nginx
sudo systemctl restart nginx

# Jika error 502 Bad Gateway
cd /opt/pzem-monitoring
bash fix-nginx-502.sh

# Atau manual fix
sudo nano /etc/nginx/sites-available/pzem.moof-set.web.id

# Pastikan ada:
location / {
    proxy_pass http://localhost:5000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
}
```

---

## 🔄 Full System Restart (Nuclear Option)

Jika semua cara di atas tidak berhasil:

```bash
cd /opt/pzem-monitoring

# 1. Stop semua
docker-compose down

# 2. Backup database
docker exec pzem-monitoring-db-1 pg_dump -U postgres pzem_monitoring > backup.sql

# 3. Remove semua (tanpa hapus volume)
docker-compose down

# 4. Pull ulang images
docker-compose pull

# 5. Build ulang
docker-compose build --no-cache

# 6. Start
docker-compose up -d

# 7. Monitor logs
docker-compose logs -f
```

---

## 📊 Monitoring Uptime Service

Berdasarkan screenshot Anda menggunakan **uptime monitoring service** (seperti UptimeRobot, StatusCake, atau self-hosted).

### Cek Konfigurasi Monitor:

1. **Monitor Type**: Pastikan set ke HTTP(s)
2. **URL**: `https://pzem.moof-set.web.id/` atau `http://103.31.39.189:5000/`
3. **Check Interval**: 60 detik (1 menit) - sesuai screenshot Anda
4. **Timeout**: Set minimal 10-15 detik
5. **Expected Status Code**: 200

### Rekomendasi:

Untuk monitoring lebih baik, tambahkan multiple checks:
- **Main page**: `https://pzem.moof-set.web.id/`
- **Health endpoint**: `https://pzem.moof-set.web.id/health`
- **Direct IP**: `http://103.31.39.189:5000/health`

---

## 📞 Dapatkan Status Real-time

Setelah menjalankan diagnosis, lakukan test ini:

```bash
# Test 1: Ping VPS
ping -c 5 103.31.39.189

# Test 2: HTTP response time
time curl -s http://103.31.39.189:5000/ > /dev/null

# Test 3: Health check dengan detail
curl -i http://103.31.39.189:5000/health

# Test 4: WebSocket connection (untuk real-time data)
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Host: 103.31.39.189:5000" \
  http://103.31.39.189:5000/socket.io/
```

---

## ✅ Checklist Setelah Fix

Setelah melakukan perbaikan, pastikan:

- [ ] Semua 3 containers running (`docker ps`)
- [ ] Health endpoint return 200 (`curl http://localhost:5000/health`)
- [ ] Dashboard accessible dari browser
- [ ] Tidak ada error di logs (`docker-compose logs`)
- [ ] Memory usage < 80% (`free -h`)
- [ ] Disk usage < 80% (`df -h`)
- [ ] Monitoring service menunjukkan status "UP"
- [ ] Uptime > 99% dalam 24 jam ke depan

---

## 📝 Logs & Debugging

### Collect Full Diagnostic Info

```bash
#!/bin/bash
# Run this to collect all diagnostic info

OUTPUT_FILE="pzem-diagnostic-$(date +%Y%m%d_%H%M%S).log"

{
    echo "=== System Info ==="
    uname -a
    
    echo -e "\n=== Docker Info ==="
    docker --version
    docker-compose --version
    
    echo -e "\n=== Container Status ==="
    docker ps -a
    
    echo -e "\n=== Container Stats ==="
    docker stats --no-stream
    
    echo -e "\n=== Resource Usage ==="
    free -h
    df -h
    uptime
    
    echo -e "\n=== Port Listening ==="
    ss -tlnp | grep 5000
    
    echo -e "\n=== Dashboard Logs ==="
    docker logs --tail 100 pzem-monitoring-dashboard-1
    
    echo -e "\n=== MQTT Logs ==="
    docker logs --tail 100 pzem-monitoring-mqtt-listener-1
    
    echo -e "\n=== Database Logs ==="
    docker logs --tail 100 pzem-monitoring-db-1
    
    echo -e "\n=== Nginx Status ==="
    systemctl status nginx
    
    echo -e "\n=== Firewall Status ==="
    ufw status verbose
    
} > "$OUTPUT_FILE"

echo "Diagnostic info saved to: $OUTPUT_FILE"
```

---

## 🆘 Butuh Bantuan Lebih Lanjut?

Jika masih bermasalah, share hasil dari script diagnosis:

```bash
# Windows
.github\diagnose-vps.ps1 > diagnostic-output.txt

# Linux/Mac
.github/diagnose-vps.sh > diagnostic-output.txt
```

Kemudian share file `diagnostic-output.txt` untuk analisis lebih lanjut.

---

**Last Updated**: 2026-01-17  
**Version**: 1.0
