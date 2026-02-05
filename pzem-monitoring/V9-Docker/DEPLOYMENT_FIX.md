# Fix Deployment Issue - Frontend Tidak Ter-update

## Masalah yang Ditemukan

1. **File di VPS masih versi lama** (Jan 21, 73691 bytes)
2. **Fungsi baru tidak ditemukan** (`updateLocationPanels` count = 0)
3. **Git submodule warning** (tidak mempengaruhi deployment utama)

## Analisis

File di local sudah benar (2610 lines, fungsi `updateLocationPanels` ada), tapi file di VPS masih lama. Ini berarti:
- Package yang dibuat GitHub Actions mungkin tidak include file terbaru
- Atau file tidak ter-extract dengan benar di VPS

## Solusi Cepat (Manual Update di VPS)

### Opsi 1: Update via Git (jika VPS menggunakan git)

```bash
# SSH ke VPS
ssh foom@your-vps-ip

# Masuk ke direktori deployment
cd /opt/pzem-monitoring

# Pull latest changes
git pull origin main

# Restart dashboard
docker-compose restart dashboard

# Verify
docker-compose exec dashboard grep -c "updateLocationPanels" /app/templates/dashboard.html
```

### Opsi 2: Copy File Manual via SCP

```bash
# Dari local machine (Windows)
# Install Git Bash atau WSL untuk scp command

# Copy file ke VPS
scp pzem-monitoring/V9-Docker/dashboard/templates/dashboard.html foom@your-vps-ip:/opt/pzem-monitoring/dashboard/templates/

# SSH ke VPS dan restart
ssh foom@your-vps-ip
cd /opt/pzem-monitoring
docker-compose restart dashboard
```

### Opsi 3: Download dari GitHub Raw

```bash
# Di VPS
cd /opt/pzem-monitoring/dashboard/templates

# Backup file lama
cp dashboard.html dashboard.html.backup

# Download file terbaru (ganti YOUR_REPO dengan repo Anda)
curl -o dashboard.html https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/pzem-monitoring/V9-Docker/dashboard/templates/dashboard.html

# Restart dashboard
cd /opt/pzem-monitoring
docker-compose restart dashboard
```

## Perbaikan Workflow (Sudah dilakukan)

Saya sudah menambahkan verifikasi di workflow:
1. ✅ Verifikasi fungsi baru sebelum packaging
2. ✅ Verifikasi fungsi baru setelah extraction  
3. ✅ Verifikasi fungsi baru di container

## Verifikasi Setelah Update

```bash
# Di VPS
cd /opt/pzem-monitoring

# Cek file di host
grep -c "updateLocationPanels" dashboard/templates/dashboard.html
# Output harus > 0

# Cek file di container
docker-compose exec dashboard grep -c "updateLocationPanels" /app/templates/dashboard.html
# Output harus > 0

# Cek ukuran file
ls -lh dashboard/templates/dashboard.html
# Harus sekitar 200KB+ (bukan 73KB)
```

## Troubleshooting

### Jika file masih tidak ter-update setelah manual copy:

1. **Cek permission:**
```bash
ls -la /opt/pzem-monitoring/dashboard/templates/dashboard.html
chmod 644 /opt/pzem-monitoring/dashboard/templates/dashboard.html
```

2. **Force restart dengan rebuild:**
```bash
cd /opt/pzem-monitoring
docker-compose down dashboard
docker-compose up -d dashboard
```

3. **Clear Flask cache:**
```bash
docker-compose exec dashboard pkill -HUP gunicorn
```

4. **Cek volume mount:**
```bash
docker-compose exec dashboard ls -lh /app/templates/dashboard.html
# Bandingkan dengan file di host
ls -lh /opt/pzem-monitoring/dashboard/templates/dashboard.html
```

## Next Steps

1. ✅ Commit dan push perubahan workflow yang sudah diperbaiki
2. ✅ Update manual di VPS menggunakan salah satu opsi di atas
3. ✅ Verifikasi update berhasil
4. ✅ Test deployment berikutnya dengan verifikasi baru
