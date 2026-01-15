# ⚡ Quick Deploy ke VPS Existing (Database Terjaga)

Panduan cepat untuk deploy ke VPS **foom@103.31.39.189** tanpa menghapus database.

## 🎯 Metode Tercepat

### Opsi 1: Automated Script (Windows)

```cmd
# Jalankan script
deploy-to-vps.bat
```

Script akan:
- ✅ Package project
- ✅ Upload ke VPS
- ✅ Backup database existing
- ✅ Deploy aplikasi baru
- ✅ Preserve database volume

### Opsi 2: Manual (Step by Step)

#### 1. Package Project

**Windows (PowerShell):**
```powershell
Compress-Archive -Path dashboard,mqtt,docker-compose.yml,start.sh -DestinationPath deploy.zip -Force
```

**Linux/Mac/Git Bash:**
```bash
tar -czf deploy.tar.gz dashboard/ mqtt/ docker-compose.yml start.sh
```

#### 2. Upload ke VPS

**SCP:**
```bash
scp deploy.zip foom@103.31.39.189:/tmp/
```

**WinSCP/FileZilla:**
- Connect: `foom@103.31.39.189`
- Upload ke `/tmp/`

#### 3. Deploy di VPS

```bash
# SSH ke VPS
ssh foom@103.31.39.189

# Backup database (jika running)
cd /opt/pzem-monitoring
docker-compose exec -T db pg_dump -U postgres pzem_monitoring > /tmp/db_backup.sql

# Stop services (volume TIDAK dihapus)
docker-compose down

# Extract package
cd /opt
mv pzem-monitoring pzem-monitoring_backup_$(date +%Y%m%d)
unzip /tmp/deploy.zip -d /opt/
# atau: tar -xzf /tmp/deploy.tar.gz -C /opt/

# Restore .env jika ada
cp pzem-monitoring_backup_*/.env pzem-monitoring/.env 2>/dev/null || true

# Build dan start
cd pzem-monitoring
docker-compose build
docker-compose up -d

# Verify database
docker-compose exec db psql -U postgres -d pzem_monitoring -c "SELECT COUNT(*) FROM pzem_data;"
```

## ✅ Verifikasi

```bash
# Check status
docker-compose ps

# Check database
docker-compose exec db psql -U postgres -d pzem_monitoring -c "SELECT COUNT(*) FROM pzem_data;"

# Check dashboard
curl http://localhost:5000/health
```

## 🔍 Troubleshooting

### Database Empty?
```bash
# Restore from backup
docker-compose exec -T db psql -U postgres -d pzem_monitoring < /tmp/db_backup.sql
```

### Port 5000 in Use?
```bash
# Check
sudo netstat -tulpn | grep :5000

# Stop conflicting service
sudo systemctl stop <service>
```

### Permission Denied?
```bash
sudo chown -R $USER:$USER /opt/pzem-monitoring
chmod +x /opt/pzem-monitoring/*.sh
```

## 📞 Quick Commands

```bash
# SSH
ssh foom@103.31.39.189

# Navigate
cd /opt/pzem-monitoring

# Status
docker-compose ps

# Logs
docker-compose logs -f

# Restart
docker-compose restart

# Stop (volume preserved)
docker-compose down

# Start
docker-compose up -d
```

## 🌐 Access

- **Dashboard**: http://103.31.39.189:5000
- **Reports**: http://103.31.39.189:5000/reports
- **Health**: http://103.31.39.189:5000/health

---

**⚠️ PENTING**: Volume `pgdata` **TIDAK PERNAH** dihapus. Database Anda aman!
