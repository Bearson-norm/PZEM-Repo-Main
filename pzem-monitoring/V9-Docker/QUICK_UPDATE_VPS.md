# Quick Update Frontend di VPS

Jika Anda sudah melakukan `git push` ke branch main dan perubahan tidak muncul di VPS, ikuti langkah berikut:

## Metode 1: Menggunakan Script (Recommended)

```bash
# SSH ke VPS
ssh user@your-vps-ip

# Masuk ke direktori project
cd /opt/pzem-monitoring/V9-Docker  # atau path sesuai instalasi Anda

# Pull latest changes
git pull origin main

# Jalankan script update
./update-vps-frontend.sh
```

## Metode 2: Manual Update

```bash
# 1. SSH ke VPS
ssh user@your-vps-ip

# 2. Masuk ke direktori project
cd /opt/pzem-monitoring/V9-Docker

# 3. Pull latest changes dari git
git pull origin main

# 4. Restart dashboard container
docker-compose restart dashboard
# atau
docker compose restart dashboard

# 5. Verifikasi container running
docker-compose ps dashboard
```

## Metode 3: Full Rebuild (Jika masih tidak berfungsi)

```bash
# SSH ke VPS
ssh user@your-vps-ip
cd /opt/pzem-monitoring/V9-Docker

# Pull latest changes
git pull origin main

# Stop containers
docker-compose down

# Rebuild dashboard
docker-compose build dashboard

# Start containers
docker-compose up -d

# Check logs
docker-compose logs -f dashboard
```

## Troubleshooting

### 1. Perubahan tidak muncul setelah restart

**Penyebab:** Browser cache atau Flask template cache

**Solusi:**
- Clear browser cache: `Ctrl+Shift+R` atau `Ctrl+F5`
- Atau buka di Incognito/Private mode
- Restart container dengan force:
  ```bash
  docker-compose restart dashboard
  docker-compose exec dashboard pkill -HUP gunicorn
  ```

### 2. File tidak ter-update di container

**Penyebab:** Volume mount tidak sync

**Solusi:**
```bash
# Cek apakah file sudah ter-update di host
ls -lh dashboard/templates/dashboard.html

# Cek apakah file di container sama
docker-compose exec dashboard ls -lh /app/templates/dashboard.html

# Jika berbeda, restart container
docker-compose restart dashboard
```

### 3. Container tidak restart

**Penyebab:** Container error atau dependency issue

**Solusi:**
```bash
# Check container status
docker-compose ps

# Check logs
docker-compose logs dashboard

# Force restart
docker-compose down dashboard
docker-compose up -d dashboard
```

### 4. Git pull gagal

**Penyebab:** Konflik atau permission issue

**Solusi:**
```bash
# Check git status
git status

# Jika ada konflik, resolve dulu
git stash
git pull origin main
git stash pop

# Atau force pull (hati-hati, akan overwrite local changes)
git fetch origin
git reset --hard origin/main
```

## Verifikasi Update Berhasil

```bash
# 1. Cek apakah file sudah ter-update
docker-compose exec dashboard grep -c "locationsContainer" /app/templates/dashboard.html

# 2. Cek apakah fungsi baru ada
docker-compose exec dashboard grep -c "updateLocationPanels" /app/templates/dashboard.html

# 3. Cek timestamp file
docker-compose exec dashboard stat /app/templates/dashboard.html

# 4. Test dashboard
curl http://localhost:5000/health
```

## Catatan Penting

1. **Volume Mount**: Karena menggunakan volume mount (`./dashboard:/app`), perubahan file di host langsung terlihat di container. Tapi Flask/Gunicorn mungkin perlu restart untuk reload template.

2. **Template Cache**: Flask/Gunicorn cache template di memory. Restart container akan clear cache.

3. **Browser Cache**: Browser juga cache JavaScript dan CSS. Selalu clear cache setelah update.

4. **Git Pull**: Pastikan melakukan `git pull` di VPS untuk mendapatkan perubahan terbaru.

## Quick Command Reference

```bash
# Update dan restart
cd /opt/pzem-monitoring/V9-Docker && git pull && docker-compose restart dashboard

# Check status
docker-compose ps

# View logs
docker-compose logs -f dashboard

# Force rebuild
docker-compose build --no-cache dashboard && docker-compose up -d dashboard
```
