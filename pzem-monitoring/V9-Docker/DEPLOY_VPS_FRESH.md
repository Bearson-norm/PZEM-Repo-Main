# 🚀 Panduan Deployment Fresh ke VPS

Panduan lengkap untuk mendeploy PZEM Monitoring System ke VPS dengan **database fresh** (menghapus database lama).

## ⚠️ PENTING: Database Akan Dihapus!

Script deployment ini akan:
- ✅ **Menghapus database lama** (backup dibuat otomatis)
- ✅ **Membuat database fresh** untuk aplikasi baru
- ✅ **Setup Nginx** untuk domain pzem.moof-set.web.id
- ✅ **Konfigurasi SSL** (dengan Let's Encrypt)

## 📋 Prerequisites

### Di Local Machine (Windows)
- Git Bash atau WSL (untuk menjalankan script bash)
- SSH client
- Access ke VPS via SSH

### Di VPS
- Ubuntu 20.04+ atau Debian 11+
- Docker dan Docker Compose terinstall
- Nginx terinstall
- Certbot terinstall (untuk SSL)
- SSH access dengan user `foom`
- Port 5000, 80, 443 terbuka

## 🎯 Quick Start

### Step 1: Jalankan Script Deployment

**Di Windows (Git Bash atau WSL):**
```bash
./deploy-vps-fresh.sh
```

Script akan:
1. ✅ Membuat package deployment
2. ✅ Upload ke VPS via SCP
3. ✅ Backup database lama (jika ada)
4. ✅ Hapus database lama
5. ✅ Deploy aplikasi baru
6. ✅ Setup Nginx
7. ✅ Start services

### Step 2: Setup SSL Certificate

Setelah deployment selesai, setup SSL:

```bash
# SSH ke VPS
ssh foom@103.31.39.189

# Setup SSL dengan Let's Encrypt
sudo certbot --nginx -d pzem.moof-set.web.id

# Reload nginx
sudo systemctl reload nginx
```

### Step 3: Konfigurasi MQTT

Update file `.env` dengan MQTT broker Anda:

```bash
# SSH ke VPS
ssh foom@103.31.39.189

# Edit .env
nano /opt/pzem-monitoring/.env
```

Update bagian MQTT:
```env
MQTT_BROKER=your-mqtt-broker-ip
MQTT_PORT=1883
MQTT_TOPIC=energy/pzem/data
```

Restart services:
```bash
cd /opt/pzem-monitoring
docker-compose restart mqtt-listener
```

## 📝 Manual Deployment (Jika Script Gagal)

### Step 1: Package Project

```bash
# Di local machine
tar -czf pzem-monitoring-deploy.tar.gz \
    dashboard/ \
    mqtt/ \
    docker-compose.yml \
    start.sh \
    nginx-pzem.conf \
    *.md
```

### Step 2: Upload ke VPS

```bash
scp pzem-monitoring-deploy.tar.gz foom@103.31.39.189:/tmp/
```

### Step 3: SSH ke VPS dan Deploy

```bash
# SSH ke VPS
ssh foom@103.31.39.189

# Backup existing (jika ada)
cd /opt
if [ -d "pzem-monitoring" ]; then
    mv pzem-monitoring pzem-monitoring_backup_$(date +%Y%m%d_%H%M%S)
fi

# Extract package
tar -xzf /tmp/pzem-monitoring-deploy.tar.gz -C /opt/

# Setup
cd /opt/pzem-monitoring
chmod +x *.sh

# Stop existing services (jika ada)
docker-compose down -v 2>/dev/null || true

# Build and start
docker-compose build
docker-compose up -d

# Verify
docker-compose ps
docker-compose logs -f
```

### Step 4: Setup Nginx

```bash
# Copy nginx config
sudo cp /opt/pzem-monitoring/nginx-pzem.conf /etc/nginx/sites-available/pzem.moof-set.web.id

# Create symlink
sudo ln -s /etc/nginx/sites-available/pzem.moof-set.web.id /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Step 5: Setup SSL

```bash
# Install certbot (jika belum)
sudo apt update
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d pzem.moof-set.web.id

# Auto-renewal (sudah otomatis dengan certbot)
```

## 🔍 Verifikasi Deployment

### Check Service Status

```bash
cd /opt/pzem-monitoring
docker-compose ps
```

Expected output:
```
NAME                    STATUS              PORTS
pzem-monitoring-db      Up (healthy)        5432/tcp
pzem-monitoring-dashboard Up                0.0.0.0:5000->5000/tcp
pzem-monitoring-mqtt-listener Up
```

### Check Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f dashboard
docker-compose logs -f db
docker-compose logs -f mqtt-listener
```

### Health Check

```bash
# From VPS
curl http://localhost:5000/health

# From external
curl http://103.31.39.189:5000/health
curl https://pzem.moof-set.web.id/health
```

### Check Database

```bash
# Connect to database
docker-compose exec db psql -U postgres -d pzem_monitoring

# Check tables
\dt

# Check data
SELECT COUNT(*) FROM pzem_data;
```

## 🔧 Troubleshooting

### Issue: Port 5000 Already in Use

```bash
# Check what's using port 5000
sudo netstat -tulpn | grep :5000

# Stop conflicting service
sudo systemctl stop <service-name>

# Or change port in docker-compose.yml
# Edit: ports: "5001:5000" (use 5001 instead)
```

### Issue: Nginx 502 Bad Gateway

```bash
# Check if dashboard is running
docker-compose ps dashboard

# Check dashboard logs
docker-compose logs dashboard

# Check nginx error log
sudo tail -f /var/log/nginx/pzem_error.log

# Restart dashboard
docker-compose restart dashboard
```

### Issue: Database Connection Failed

```bash
# Check database container
docker-compose ps db

# Check database logs
docker-compose logs db

# Restart database
docker-compose restart db

# Verify connection
docker-compose exec db pg_isready -U postgres
```

### Issue: SSL Certificate Failed

```bash
# Check nginx config
sudo nginx -t

# Check domain DNS
nslookup pzem.moof-set.web.id

# Retry certbot
sudo certbot --nginx -d pzem.moof-set.web.id --force-renewal
```

### Issue: Permission Denied

```bash
# Fix permissions
sudo chown -R $USER:$USER /opt/pzem-monitoring
chmod +x /opt/pzem-monitoring/*.sh
```

## 📊 Post-Deployment Checklist

Setelah deployment berhasil:

- [ ] Verify services running: `docker-compose ps`
- [ ] Check dashboard accessible: `http://103.31.39.189:5000`
- [ ] Check domain accessible: `https://pzem.moof-set.web.id`
- [ ] Check health endpoint: `http://103.31.39.189:5000/health`
- [ ] Verify MQTT listener running: `docker-compose logs mqtt-listener`
- [ ] Update .env with MQTT broker settings
- [ ] Test report generation: `https://pzem.moof-set.web.id/reports`
- [ ] Setup SSL certificate: `sudo certbot --nginx -d pzem.moof-set.web.id`
- [ ] Verify SSL working: `https://pzem.moof-set.web.id`
- [ ] Check nginx logs: `sudo tail -f /var/log/nginx/pzem_access.log`

## 🔄 Update di Masa Depan

Untuk update aplikasi (database tetap dipertahankan):

```bash
cd /opt/pzem-monitoring

# Backup database
docker-compose exec -T db pg_dump -U postgres pzem_monitoring > backup_$(date +%Y%m%d_%H%M%S).sql

# Pull new code (jika menggunakan git)
git pull

# Rebuild and restart
docker-compose build
docker-compose up -d
```

## 📞 Support

Jika mengalami masalah:

1. **Check logs**: `docker-compose logs -f`
2. **Verify services**: `docker-compose ps`
3. **Check nginx**: `sudo nginx -t && sudo systemctl status nginx`
4. **Check SSL**: `sudo certbot certificates`
5. **Restore backup**: Gunakan backup SQL jika perlu

## 🎯 Quick Reference

```bash
# SSH to VPS
ssh foom@103.31.39.189

# Navigate to deployment
cd /opt/pzem-monitoring

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Start services
docker-compose up -d

# Check database
docker-compose exec db psql -U postgres -d pzem_monitoring -c "SELECT COUNT(*) FROM pzem_data;"

# Backup database
docker-compose exec -T db pg_dump -U postgres pzem_monitoring > backup.sql

# Check nginx
sudo nginx -t
sudo systemctl status nginx
sudo systemctl reload nginx

# Check SSL
sudo certbot certificates
```

## 📍 VPS Information

- **Host**: 103.31.39.189
- **User**: foom
- **Domain**: pzem.moof-set.web.id
- **Deploy Directory**: /opt/pzem-monitoring
- **Backup Directory**: /opt/backups/pzem-monitoring

---

**✅ Deployment siap!** Jalankan `./deploy-vps-fresh.sh` untuk memulai.
