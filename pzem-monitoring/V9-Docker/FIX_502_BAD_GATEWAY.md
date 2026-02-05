# 🔧 Fix 502 Bad Gateway Error

## Masalah
Error `502 Bad Gateway` saat mengakses `https://pzem.moof-set.web.id/`

## Penyebab
Nginx tidak bisa terhubung ke backend (dashboard container). Kemungkinan:
1. Dashboard container tidak running atau crash
2. Port 5000 tidak accessible
3. Nginx config salah (proxy_pass tidak benar)
4. Dashboard container error saat startup

## 🔍 Troubleshooting (Lakukan di VPS)

### Step 1: Cek Status Container

```bash
cd /opt/pzem-monitoring
docker-compose ps
```

**Expected output**: Semua container harus `Up` (running)
- ✅ `dashboard` - harus `Up`
- ✅ `db` - harus `Up`
- ✅ `mqtt-listener` - harus `Up`

**Jika dashboard tidak running:**
```bash
# Start dashboard
docker-compose up -d dashboard

# Tunggu 5 detik, lalu cek lagi
docker-compose ps dashboard
```

### Step 2: Cek Logs Dashboard

```bash
# Cek logs terakhir (20 baris)
docker-compose logs dashboard --tail=20

# Cek logs real-time (Ctrl+C untuk stop)
docker-compose logs -f dashboard
```

**Cari error seperti:**
- ❌ `ModuleNotFoundError`
- ❌ `ImportError`
- ❌ `FileNotFoundError`
- ❌ `Permission denied`
- ❌ `Port already in use`

### Step 3: Test Dashboard dari Host

```bash
# Test apakah dashboard accessible di localhost:5000
curl http://localhost:5000/health

# Atau test dengan browser di VPS
curl http://localhost:5000/
```

**Expected output**: 
- ✅ HTTP 200 OK dengan response JSON atau HTML
- ❌ Jika error: `Connection refused` atau timeout = dashboard tidak running

### Step 4: Cek Nginx Config

```bash
# Cek nginx config
sudo cat /etc/nginx/sites-available/pzem.moof-set.web.id | grep -A 5 "proxy_pass"

# Test nginx config
sudo nginx -t
```

**Expected output:**
- ✅ `proxy_pass http://127.0.0.1:5000;` atau `proxy_pass http://pzem_dashboard;`
- ✅ `nginx: configuration file /etc/nginx/nginx.conf test is successful`

### Step 5: Cek Port 5000

```bash
# Cek apakah port 5000 listening
sudo netstat -tlnp | grep 5000
# atau
sudo ss -tlnp | grep 5000
```

**Expected output:**
- ✅ `0.0.0.0:5000` atau `127.0.0.1:5000` dengan status `LISTEN`

## 🔧 Solusi Cepat

### Solusi 1: Restart Dashboard Container

```bash
cd /opt/pzem-monitoring

# Stop dashboard
docker-compose stop dashboard

# Start dashboard
docker-compose up -d dashboard

# Tunggu 10 detik untuk startup
sleep 10

# Cek status
docker-compose ps dashboard

# Test
curl http://localhost:5000/health

# Reload nginx
sudo systemctl reload nginx
```

### Solusi 2: Rebuild Dashboard Container (Jika ada perubahan code)

```bash
cd /opt/pzem-monitoring

# Rebuild dashboard
docker-compose build --no-cache dashboard

# Restart
docker-compose up -d dashboard

# Tunggu 10 detik
sleep 10

# Cek logs
docker-compose logs dashboard --tail=30

# Test
curl http://localhost:5000/health
```

### Solusi 3: Fix Nginx Config (Jika proxy_pass salah)

```bash
# Backup config
sudo cp /etc/nginx/sites-available/pzem.moof-set.web.id /etc/nginx/sites-available/pzem.moof-set.web.id.backup

# Edit config
sudo nano /etc/nginx/sites-available/pzem.moof-set.web.id

# Pastikan di dalam location / ada:
#     proxy_pass http://127.0.0.1:5000;
# atau
#     proxy_pass http://pzem_dashboard;

# Test config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Solusi 4: Cek File dashboard.html (Jika error saat startup)

```bash
# Cek apakah file ada dan readable
ls -lh /opt/pzem-monitoring/dashboard/templates/dashboard.html

# Cek permission
chmod 644 /opt/pzem-monitoring/dashboard/templates/dashboard.html

# Cek syntax (jika ada error di logs)
# File harus valid HTML
```

## 🚨 Error Umum dan Solusinya

### Error: "Connection refused" di curl localhost:5000

**Penyebab**: Dashboard container tidak running atau crash

**Solusi**:
```bash
docker-compose logs dashboard --tail=50
# Cari error, fix error tersebut
docker-compose up -d dashboard
```

### Error: "ModuleNotFoundError" di logs

**Penyebab**: Python dependencies tidak terinstall

**Solusi**:
```bash
docker-compose build --no-cache dashboard
docker-compose up -d dashboard
```

### Error: "Port 5000 already in use"

**Penyebab**: Port 5000 digunakan oleh process lain

**Solusi**:
```bash
# Cek process yang menggunakan port 5000
sudo lsof -i :5000
# atau
sudo netstat -tlnp | grep 5000

# Kill process tersebut (ganti PID dengan process ID)
sudo kill -9 PID

# Restart dashboard
docker-compose restart dashboard
```

### Error: "FileNotFoundError: dashboard.html"

**Penyebab**: File tidak ada atau path salah

**Solusi**:
```bash
# Cek file
ls -la /opt/pzem-monitoring/dashboard/templates/dashboard.html

# Jika tidak ada, copy dari backup atau pull dari git
cd /opt/pzem-monitoring
git pull origin main
# atau copy manual
```

## ✅ Verifikasi Setelah Fix

```bash
# 1. Cek container running
docker-compose ps

# 2. Test dashboard dari host
curl http://localhost:5000/health

# 3. Test dari browser
# Buka: https://pzem.moof-set.web.id/
# Harus load tanpa error 502

# 4. Cek nginx error log
sudo tail -f /var/log/nginx/pzem_error.log
```

## 📝 Script Otomatis

Gunakan script `fix-nginx-502.sh` untuk troubleshooting otomatis:

```bash
cd /opt/pzem-monitoring
chmod +x fix-nginx-502.sh
./fix-nginx-502.sh
```

Script ini akan:
- ✅ Cek status container
- ✅ Cek logs dashboard
- ✅ Test koneksi localhost:5000
- ✅ Cek nginx config
- ✅ Berikan rekomendasi fix

---

**Catatan**: Setelah fix, tunggu 10-30 detik untuk dashboard fully startup, lalu test lagi.
