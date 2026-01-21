# 🚨 QUICK FIX - Status PENDING

## Masalah Anda

Berdasarkan screenshot:
- ❌ Status: **PENDING** 
- ❌ Response: **N/A**
- ❌ Uptime 24h: **65.93%** (terlalu rendah!)

## ⚡ Solusi Cepat (5 Menit)

### Step 1: Jalankan Diagnosis

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

### Step 2: Lihat Hasil Diagnosis

Script akan memberitahu masalahnya. Kemungkinan besar:
1. ❌ Container restart terus
2. ❌ Database connection error
3. ❌ Port 5000 tidak accessible
4. ❌ Memory/disk habis

### Step 3: Fix Sesuai Masalah

#### Jika Container Restart Terus:

```bash
# SSH ke VPS
ssh -i ~/.ssh/foom-vps foom@103.31.39.189

# Quick restart
cd /opt/pzem-monitoring
bash quick-fix.sh restart
```

#### Jika Database Error:

```bash
# SSH ke VPS
ssh -i ~/.ssh/foom-vps foom@103.31.39.189

# Restart database & containers
cd /opt/pzem-monitoring
docker restart pzem-monitoring-db-1
sleep 10
docker restart pzem-monitoring-dashboard-1
docker restart pzem-monitoring-mqtt-listener-1
```

#### Jika Port Tidak Accessible:

```bash
# SSH ke VPS
ssh -i ~/.ssh/foom-vps foom@103.31.39.189

# Buka firewall
sudo ufw allow 5000/tcp
sudo ufw reload

# Restart
cd /opt/pzem-monitoring
bash quick-fix.sh restart
```

#### Jika Memory/Disk Habis:

```bash
# SSH ke VPS
ssh -i ~/.ssh/foom-vps foom@103.31.39.189

# Clear cache & restart
cd /opt/pzem-monitoring
bash quick-fix.sh clearcache
bash quick-fix.sh restart
```

### Step 4: Verify

Setelah fix, test:

```bash
# 1. Cek status
bash quick-fix.sh check

# 2. Test health endpoint
curl http://localhost:5000/health

# 3. Lihat dari browser
# Buka: https://pzem.moof-set.web.id
```

---

## 🔍 Jika Masih Bermasalah

### Nuclear Option (Full Reset):

```bash
# SSH ke VPS
ssh -i ~/.ssh/foom-vps foom@103.31.39.189

# Full reset (database tetap aman)
cd /opt/pzem-monitoring
bash quick-fix.sh reset
```

---

## 📚 Dokumentasi Lengkap

Untuk penjelasan detail, baca:
- **[TROUBLESHOOTING_README.md](.github/TROUBLESHOOTING_README.md)** - Tools overview
- **[TROUBLESHOOTING_PENDING_STATUS.md](.github/TROUBLESHOOTING_PENDING_STATUS.md)** - Step-by-step guide

---

## ✅ Indikator Sukses

Setelah fix berhasil, Anda akan lihat:
- ✅ Status monitoring: **UP** 
- ✅ Response time: **<2000ms**
- ✅ Uptime 24h: **>99%**
- ✅ Grafik: bar hijau semua

---

## 🆘 Masih Butuh Bantuan?

Simpan output diagnosis:

**Windows:**
```powershell
.github\diagnose-vps.ps1 > hasil-diagnosis.txt
```

**Linux/Mac:**
```bash
.github/diagnose-vps.sh > hasil-diagnosis.txt
```

Kemudian share file `hasil-diagnosis.txt` untuk analisis lebih lanjut.

---

**Dibuat**: 2026-01-17  
**Untuk**: PZEM Monitoring System Issue
