# 🚀 PZEM Monitoring System - Ubuntu VPS Deployment Guide

Complete guide to deploy your PZEM 3-Phase Energy Monitoring System to an Ubuntu VPS.

## 📋 Prerequisites

### VPS Requirements
- **OS**: Ubuntu 20.04+ or Debian 11+
- **RAM**: Minimum 2GB (4GB recommended)
- **Storage**: Minimum 20GB SSD
- **CPU**: 1-2 cores
- **Network**: Public IP with port 5000 accessible

### Domain (Optional)
- A domain name pointing to your VPS IP
- SSL certificate (Let's Encrypt recommended)

## 🛠️ Quick Deployment (Recommended)

> 📖 **Panduan Lengkap Transfer**: Lihat [TRANSFER_GUIDE.md](TRANSFER_GUIDE.md) untuk berbagai metode transfer tanpa Git

### Step 1: Create Deployment Package (Windows)

On your Windows machine:

**Opsi A: Package Script (Recommended)**
```cmd
# Run the package script
package.bat
```

**Opsi B: Quick Transfer Tool (Interactive)**
```cmd
# Interactive tool dengan pilihan metode transfer
transfer-quick.bat
```

This creates a `pzem-monitoring-ubuntu-YYYYMMDD_HHMMSS.zip` file.

### Step 2: Upload to Ubuntu VPS

**Metode 1: SCP (Command Line)**
```bash
# Upload package to your VPS
scp pzem-monitoring-ubuntu-*.zip user@your-vps-ip:/opt/
```

**Metode 2: WinSCP (GUI - Recommended untuk pemula)**
1. Download WinSCP: https://winscp.net/
2. Connect ke VPS dengan SFTP
3. Drag & drop file ZIP ke `/opt/`

**Metode 3: FileZilla (GUI)**
1. Download FileZilla: https://filezilla-project.org/
2. Connect dengan SFTP protocol
3. Upload file ZIP ke `/opt/`

**Metode 4: Cloud Storage**
1. Upload ZIP ke Google Drive/Dropbox/OneDrive
2. Download di VPS dengan `wget` atau `curl`

> 💡 **Tips**: Lihat [TRANSFER_GUIDE.md](TRANSFER_GUIDE.md) untuk detail semua metode transfer

### Step 3: Deploy on Ubuntu VPS

SSH into your Ubuntu VPS:

```bash
ssh user@your-vps-ip
cd /opt

# Install unzip if not present
sudo apt update && sudo apt install unzip -y

# Extract package
unzip pzem-monitoring-ubuntu-*.zip
mv pzem-monitoring-ubuntu pzem-monitoring
cd pzem-monitoring

# Run Ubuntu deployment script
chmod +x ubuntu-deploy.sh
sudo ./ubuntu-deploy.sh
```

### Step 4: Configure and Start

```bash
# Edit configuration
nano .env

# Start the system
./start.sh
```

## ⚙️ Configuration

### Environment Variables (.env file)

```bash
# Database Configuration
DB_PASSWORD=your_secure_password_here

# MQTT Configuration
MQTT_BROKER=103.87.67.139
MQTT_PORT=1883
MQTT_TOPIC=energy/pzem/data

# Optional: MQTT Authentication
# MQTT_USERNAME=your_username
# MQTT_PASSWORD=your_password
```

### Security Configuration

The deployment script automatically configures:

- **Firewall (UFW)**: Only allows SSH, port 5000, and port 1883
- **Fail2ban**: Protects SSH from brute force attacks
- **Automatic backups**: Daily backups at 2 AM
- **Health monitoring**: Checks system health every 5 minutes
- **Log rotation**: Prevents log files from growing too large

## 🔧 Service Management

### Systemd Service (Auto-start)

```bash
# Enable auto-start
sudo systemctl enable pzem-monitoring

# Start service
sudo systemctl start pzem-monitoring

# Check status
sudo systemctl status pzem-monitoring

# View logs
sudo journalctl -u pzem-monitoring -f
```

### Docker Commands

```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Start services
docker-compose up -d

# Check container status
docker-compose ps
```

### Monitoring Commands

```bash
# System status
./monitor.sh

# Health check
./health-check.sh

# Resource usage
docker stats

# Disk usage
df -h /opt/pzem-monitoring
```

## 📊 Monitoring & Maintenance

### Health Checks

- **Dashboard**: http://your-vps-ip:5000/health
- **System Status**: `./monitor.sh`
- **Resource Usage**: `docker stats`
- **Logs**: `docker-compose logs -f`

### Backup

```bash
# Manual backup
./backup.sh

# Automatic backups run daily at 2 AM
# Backups are stored in /opt/backups/pzem-monitoring/
# Old backups are automatically cleaned up after 7 days
```

### Updates

```bash
# Update system
./update.sh

# Or manually
docker-compose down
docker-compose pull
docker-compose build --no-cache
docker-compose up -d
```

## 🌐 Access URLs

After deployment, access your system at:

- **Main Dashboard**: http://your-vps-ip:5000
- **Report Generator**: http://your-vps-ip:5000/reports
- **Health Check**: http://your-vps-ip:5000/health

## 🔒 SSL Setup (Optional)

### Using Let's Encrypt

```bash
# Run SSL setup script
./setup-ssl.sh

# Or manually
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

After SSL setup, access via:
- **Main Dashboard**: https://yourdomain.com
- **Report Generator**: https://yourdomain.com/reports

## 🚨 Troubleshooting

### Common Issues

1. **Port already in use:**
```bash
sudo netstat -tulpn | grep :5000
sudo kill -9 <PID>
```

2. **Permission denied:**
```bash
sudo chown -R $USER:$USER /opt/pzem-monitoring
chmod +x *.sh
```

3. **Database connection failed:**
```bash
docker-compose logs db
docker-compose restart db
```

4. **MQTT connection issues:**
```bash
# Check MQTT broker settings in .env
# Test connection: telnet your-mqtt-broker 1883
```

5. **Service won't start:**
```bash
# Check Docker status
sudo systemctl status docker

# Check service logs
sudo journalctl -u pzem-monitoring -f

# Check container logs
docker-compose logs
```

6. **Firewall issues:**
```bash
# Check firewall status
sudo ufw status

# Allow port if needed
sudo ufw allow 5000/tcp
```

7. **docker-compose: command not found:**

**Mengapa ini bisa terjadi?**
- **Docker versi baru (v2+)**: Docker versi terbaru menggunakan `docker compose` (plugin) bukan `docker-compose` (standalone binary)
- **System update**: Ubuntu update atau Docker update bisa menghapus `docker-compose` standalone
- **Install ulang Docker**: Jika Docker diinstall ulang dengan metode baru, mungkin hanya install plugin
- **PATH issue**: `docker-compose` mungkin tidak ada di PATH

**Solusi:**
```bash
# Check if docker-compose is installed
docker-compose --version

# If not found, check if docker compose (plugin) is available
docker compose version

# If neither works, install docker-compose:
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Or install docker-compose-plugin (recommended for newer Docker versions):
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Verify installation
docker compose version
```

**Catatan**: Script yang sudah diperbaiki (`start.sh`, `update.sh`, `backup.sh`) sekarang auto-detect dan mendukung kedua format.

8. **Script cannot execute: required file not found:**
```bash
# This is usually a line ending issue (Windows CRLF vs Linux LF)
# Fix with dos2unix:
sudo apt install dos2unix -y
dos2unix update.sh
chmod +x update.sh

# Or use sed:
sed -i 's/\r$//' update.sh
chmod +x update.sh

# Or run directly with bash:
bash update.sh
```

9. **Nginx 502 Bad Gateway:**
```bash
# Step 1: Check if dashboard container is running
cd /opt/pzem-monitoring
docker compose ps

# Step 2: Test if dashboard is accessible from host
curl http://localhost:5000/health

# Step 3: Check dashboard logs for errors
docker compose logs dashboard --tail=50

# Step 4: Restart dashboard if needed
docker compose restart dashboard

# Step 5: Check nginx configuration
sudo cat /etc/nginx/sites-available/pzem.moof-set.web.id

# Step 6: Verify proxy_pass points to correct address
# Should be: proxy_pass http://127.0.0.1:5000;
# Or: proxy_pass http://localhost:5000;

# Step 7: Check nginx error logs
sudo tail -20 /var/log/nginx/error.log

# Step 8: Test and reload nginx config
sudo nginx -t
sudo systemctl reload nginx

# Step 9: If still not working, check firewall
sudo ufw status
sudo ufw allow 5000/tcp
```

**Common causes:**
- Dashboard container not running or crashed
- Nginx `proxy_pass` pointing to wrong address (should be `http://127.0.0.1:5000`)
- Dashboard not listening on `0.0.0.0:5000` (check Dockerfile CMD)
- Firewall blocking port 5000
- Container not fully started yet (wait a few seconds after `docker compose up -d`)

### Performance Optimization

1. **Increase Docker resources:**
```bash
# Edit /etc/docker/daemon.json
sudo nano /etc/docker/daemon.json
```

Add:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

2. **Database optimization:**
```bash
# Connect to database
docker-compose exec db psql -U postgres -d pzem_monitoring

# Create indexes for better performance
CREATE INDEX CONCURRENTLY idx_pzem_data_created_device ON pzem_data(created_at DESC, device_address);
CREATE INDEX CONCURRENTLY idx_pzem_data_device_created ON pzem_data(device_address, created_at DESC);
```

3. **System optimization:**
```bash
# Increase file limits
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Optimize kernel parameters
echo "vm.max_map_count=262144" >> /etc/sysctl.conf
sysctl -p
```

## 📈 Scaling

### Vertical Scaling
- Increase VPS resources (RAM, CPU, Storage)
- Optimize database queries
- Use SSD storage for better I/O performance

### Horizontal Scaling
- Use load balancer (nginx, HAProxy)
- Database clustering
- Add monitoring (Prometheus + Grafana)

## 🔄 Updates

### Safe System Updates (Database Preserved) ⭐

The `update.sh` script has been designed to **safely update the application WITHOUT deleting your database**. 

#### ✅ Safety Features:

1. **Automatic Backup**: Creates database backup before update
2. **Volume Preservation**: Database volume (`pgdata`) is never deleted
3. **Verification**: Checks database integrity after update
4. **Rollback Support**: Can restore from backup if update fails
5. **Health Checks**: Verifies services are running correctly

#### 📋 Update Process:

```bash
# Navigate to deployment directory
cd /opt/pzem-monitoring

# Run safe update script (recommended)
./update.sh

# Or force complete rebuild (slower, but ensures clean build)
./update.sh --force-rebuild
```

#### 🔍 What the Update Script Does:

1. ✅ **Backs up database** to `/opt/backups/pzem-monitoring/`
2. ✅ **Backs up reports** and configuration files
3. ✅ **Verifies database volume** exists and will be preserved
4. ✅ **Stops services** (volumes remain intact)
5. ✅ **Pulls latest images** (if using registry)
6. ✅ **Rebuilds containers** (incremental build, faster)
7. ✅ **Starts services** with new code
8. ✅ **Verifies database** connection and data integrity
9. ✅ **Performs health check** on dashboard

#### 🛡️ Database Safety:

- **Database volume is NEVER deleted** during update
- Named volume `pgdata` persists across container restarts
- Backup is created before every update
- Automatic rollback if update fails

#### 📊 Verify Update:

After update, verify everything works:

```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs -f

# Verify database has data
docker-compose exec db psql -U postgres -d pzem_monitoring -c "SELECT COUNT(*) FROM pzem_data;"

# Access dashboard
curl http://localhost:5000/health
```

#### 🔙 Rollback (if needed):

If update fails, backups are available:

```bash
# List backups
ls -lh /opt/backups/pzem-monitoring/

# Restore database from backup
docker-compose exec -T db psql -U postgres -d pzem_monitoring < /opt/backups/pzem-monitoring/database_pre_update_YYYYMMDD_HHMMSS.sql
```

### System Package Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y
```

## 📞 Support

If you encounter issues:

1. Check the logs: `docker-compose logs -f`
2. Verify configuration: `docker-compose config`
3. Test connectivity: `curl http://localhost:5000/health`
4. Check system resources: `htop` or `docker stats`
5. Verify firewall: `sudo ufw status`
6. Check service status: `sudo systemctl status pzem-monitoring`

## 📝 File Structure

After deployment, your Ubuntu VPS will have:

```
/opt/pzem-monitoring/
├── dashboard/              # Web application
├── mqtt/                   # MQTT client
├── docker-compose.yml      # Development compose
├── docker-compose.production.yml  # Production compose
├── .env                    # Environment configuration
├── start.sh               # Start script
├── backup.sh              # Backup script
├── update.sh              # Update script
├── monitor.sh             # Monitoring script
├── health-check.sh        # Health check script
├── setup-ssl.sh           # SSL setup script
├── ubuntu-deploy.sh       # Ubuntu deployment script
└── logs/                  # Application logs

/opt/backups/pzem-monitoring/  # Backup storage
```

## 🎯 Production Checklist

Before going live:

- [ ] Change all default passwords in `.env`
- [ ] Configure firewall (automatically done by script)
- [ ] Set up SSL certificate (optional)
- [ ] Test all functionality
- [ ] Monitor system resources
- [ ] Verify backup schedule
- [ ] Test health monitoring
- [ ] Configure monitoring alerts

## 🔧 Security Features

The deployment includes:

- **UFW Firewall**: Only necessary ports open
- **Fail2ban**: SSH brute force protection
- **Automatic Backups**: Daily backups with cleanup
- **Health Monitoring**: Automatic service restart on failure
- **Log Rotation**: Prevents disk space issues
- **Non-root Docker**: Runs as regular user
- **SSL Support**: Easy Let's Encrypt integration

## 📊 Monitoring Features

- **Health Checks**: Every 5 minutes
- **Automatic Restart**: On service failure
- **Resource Monitoring**: CPU, memory, disk usage
- **Log Monitoring**: Centralized logging
- **Backup Monitoring**: Automatic backup verification

---

**🎉 Congratulations!** Your PZEM monitoring system is now deployed on Ubuntu VPS with enterprise-grade security and monitoring!

## 📞 Quick Commands Reference

```bash
# Start system
./start.sh

# Stop system
docker-compose down

# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Monitor status
./monitor.sh

# Backup data
./backup.sh

# Update system
./update.sh

# Setup SSL
./setup-ssl.sh

# Check health
./health-check.sh

# Access dashboard
curl http://localhost:5000/health
```



