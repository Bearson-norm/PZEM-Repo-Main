# 🚀 Panduan Deployment ke VPS yang Sudah Ada

Panduan lengkap untuk mendeploy PZEM Monitoring System ke VPS yang sudah ada program sebelumnya **TANPA menghapus database**.

## ⚠️ Penting: Database Akan Dipertahankan

Script deployment ini dirancang khusus untuk:
- ✅ **Mempertahankan database existing** (volume `pgdata` tidak akan dihapus)
- ✅ **Backup otomatis** sebelum deployment
- ✅ **Preserve konfigurasi** (.env file)
- ✅ **Safe rollback** jika terjadi masalah

## 📋 Prerequisites

### Di Local Machine (Windows)
- Git atau file transfer tool (WinSCP, FileZilla)
- SSH client (PuTTY, atau built-in Windows SSH)
- Access ke VPS via SSH

### Di VPS
- Ubuntu 20.04+ atau Debian 11+
- Docker dan Docker Compose terinstall
- SSH access dengan user `foom`
- Port 5000 terbuka (untuk dashboard)

## 🎯 Metode Deployment

### Metode 1: Automated Script (Recommended) ⭐

Script otomatis yang melakukan semua langkah deployment dengan aman.

#### Step 1: Jalankan Script Deployment

```bash
# Di local machine (Windows dengan Git Bash atau WSL)
./deploy-to-existing-vps.sh
```

Script ini akan:
1. ✅ Membuat package deployment
2. ✅ Upload ke VPS via SCP
3. ✅ Backup database existing
4. ✅ Deploy aplikasi baru
5. ✅ Verify database preserved
6. ✅ Start services

#### Step 2: Verifikasi Deployment

Setelah script selesai, verifikasi:

```bash
# SSH ke VPS
ssh foom@103.31.39.189

# Check status
cd /opt/pzem-monitoring
docker-compose ps

# Check logs
docker-compose logs -f

# Verify database
docker-compose exec db psql -U postgres -d pzem_monitoring -c "SELECT COUNT(*) FROM pzem_data;"
```

### Metode 2: Manual Deployment

Jika automated script tidak bisa digunakan, ikuti langkah manual:

#### Step 1: Package Project

```bash
# Di local machine
tar -czf pzem-monitoring-deploy.tar.gz \
    dashboard/ \
    mqtt/ \
    docker-compose.yml \
    start.sh \
    *.md
```

#### Step 2: Upload ke VPS

**Opsi A: SCP**
```bash
scp pzem-monitoring-deploy.tar.gz foom@103.31.39.189:/tmp/
```

**Opsi B: WinSCP/FileZilla**
- Connect ke VPS dengan SFTP
- Upload file ke `/tmp/`

#### Step 3: Backup Database Existing

```bash
# SSH ke VPS
ssh foom@103.31.39.189

# Backup database (jika container running)
cd /opt/pzem-monitoring
docker-compose exec -T db pg_dump -U postgres pzem_monitoring > /opt/backups/database_backup_$(date +%Y%m%d_%H%M%S).sql

# Backup .env jika ada
cp .env /opt/backups/.env.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
```

#### Step 4: Stop Services (Volume Tetap Terjaga)

```bash
# Stop services - volume pgdata TIDAK akan dihapus
cd /opt/pzem-monitoring
docker-compose down
```

#### Step 5: Extract Package Baru

```bash
# Backup directory existing
mv /opt/pzem-monitoring /opt/pzem-monitoring_backup_$(date +%Y%m%d_%H%M%S)

# Extract package baru
cd /opt
tar -xzf /tmp/pzem-monitoring-deploy.tar.gz
mv pzem-monitoring-* pzem-monitoring
cd pzem-monitoring
```

#### Step 6: Restore .env

```bash
# Restore .env dari backup jika ada
cp /opt/backups/.env.backup.* .env 2>/dev/null || {
    # Atau buat .env baru
    nano .env
}
```

#### Step 7: Build dan Start

```bash
# Build containers
docker-compose build

# Start services (database volume akan digunakan kembali)
docker-compose up -d

# Verify database
docker-compose exec db psql -U postgres -d pzem_monitoring -c "SELECT COUNT(*) FROM pzem_data;"
```

## 🔍 Verifikasi Database Terjaga

### Check Database Volume

```bash
# List volumes
docker volume ls | grep pgdata

# Inspect volume
docker volume inspect pgdata
```

### Check Data

```bash
# Count records
docker-compose exec db psql -U postgres -d pzem_monitoring -c "SELECT COUNT(*) FROM pzem_data;"

# Check latest data
docker-compose exec db psql -U postgres -d pzem_monitoring -c "SELECT * FROM pzem_data ORDER BY created_at DESC LIMIT 5;"
```

## 🛡️ Safety Features

### 1. Automatic Backup
- Database di-backup sebelum deployment
- Backup disimpan di `/opt/backups/pzem-monitoring/`
- Format: `database_before_deploy_YYYYMMDD_HHMMSS.sql`

### 2. Volume Preservation
- Volume `pgdata` **TIDAK PERNAH** dihapus
- Data tetap ada meskipun container di-recreate
- Named volume persisten across container restarts

### 3. Configuration Preservation
- File `.env` di-backup dan di-restore
- Konfigurasi existing tidak hilang

### 4. Rollback Support
Jika deployment gagal, restore dari backup:

```bash
# Restore database
docker-compose exec -T db psql -U postgres -d pzem_monitoring < /opt/backups/pzem-monitoring/database_before_deploy_*.sql

# Restore .env
cp /opt/backups/pzem-monitoring/.env.backup.* .env
```

## 📊 Monitoring Deployment

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
```

## 🔧 Troubleshooting

### Issue: Database Empty After Deployment

**Kemungkinan Penyebab:**
- Volume tidak terhubung dengan benar
- Database container baru dibuat (fresh install)

**Solusi:**
```bash
# Check volume
docker volume ls | grep pgdata

# Check volume mount
docker-compose config | grep -A 5 volumes

# Restore from backup
docker-compose exec -T db psql -U postgres -d pzem_monitoring < /opt/backups/pzem-monitoring/database_before_deploy_*.sql
```

### Issue: Port 5000 Already in Use

```bash
# Check what's using port 5000
sudo netstat -tulpn | grep :5000

# Stop conflicting service
sudo systemctl stop <service-name>

# Or change port in docker-compose.yml
# Edit: ports: "5001:5000" (use 5001 instead)
```

### Issue: Permission Denied

```bash
# Fix permissions
sudo chown -R $USER:$USER /opt/pzem-monitoring
chmod +x /opt/pzem-monitoring/*.sh
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

## 📝 Post-Deployment Checklist

Setelah deployment berhasil:

- [ ] Verify database has data: `SELECT COUNT(*) FROM pzem_data;`
- [ ] Check dashboard accessible: `http://103.31.39.189:5000`
- [ ] Check health endpoint: `http://103.31.39.189:5000/health`
- [ ] Verify MQTT listener running: `docker-compose logs mqtt-listener`
- [ ] Check backup created: `ls -lh /opt/backups/pzem-monitoring/`
- [ ] Update .env if needed (MQTT broker, etc.)
- [ ] Test report generation: `http://103.31.39.189:5000/reports`

## 🔄 Update di Masa Depan

Untuk update aplikasi tanpa menghapus database:

```bash
cd /opt/pzem-monitoring
./update.sh
```

Script `update.sh` akan:
- ✅ Backup database
- ✅ Preserve volume
- ✅ Update code
- ✅ Restart services
- ✅ Verify data integrity

## 📞 Support

Jika mengalami masalah:

1. **Check logs**: `docker-compose logs -f`
2. **Verify database**: `docker-compose exec db psql -U postgres -d pzem_monitoring -c "SELECT COUNT(*) FROM pzem_data;"`
3. **Check backups**: `ls -lh /opt/backups/pzem-monitoring/`
4. **Restore if needed**: Gunakan backup SQL untuk restore

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

# Stop services (volume preserved)
docker-compose down

# Start services
docker-compose up -d

# Check database
docker-compose exec db psql -U postgres -d pzem_monitoring -c "SELECT COUNT(*) FROM pzem_data;"

# Backup database
docker-compose exec -T db pg_dump -U postgres pzem_monitoring > backup.sql
```

---

**✅ Database Anda aman!** Volume `pgdata` tidak akan pernah dihapus selama deployment.
