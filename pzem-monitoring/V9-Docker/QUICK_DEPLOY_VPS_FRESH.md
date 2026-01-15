# 🚀 Quick Deploy ke VPS (Fresh Database)

Panduan cepat untuk mendeploy PZEM Monitoring ke VPS dengan database fresh.

## ⚠️ PERINGATAN

Script ini akan **MENGHAPUS database lama** dan membuat database baru. Backup otomatis dibuat sebelum penghapusan.

## 🎯 Cara Menggunakan

### Di Windows (Git Bash atau WSL)

1. **Buka Git Bash atau WSL**

2. **Jalankan script deployment:**
   ```bash
   ./deploy-vps-fresh.sh
   ```

3. **Konfirmasi deployment** (ketik `yes` saat diminta)

4. **Tunggu hingga selesai** (5-10 menit)

### Setelah Deployment

1. **SSH ke VPS:**
   ```bash
   ssh foom@103.31.39.189
   ```

2. **Setup Nginx & SSL:**
   ```bash
   cd /opt/pzem-monitoring
   sudo bash setup-nginx-ssl.sh
   ```

3. **Update .env dengan MQTT broker:**
   ```bash
   nano /opt/pzem-monitoring/.env
   ```
   
   Update:
   ```env
   MQTT_BROKER=your-mqtt-broker-ip
   MQTT_PORT=1883
   MQTT_TOPIC=energy/pzem/data
   ```

4. **Restart services:**
   ```bash
   cd /opt/pzem-monitoring
   docker-compose restart
   ```

## ✅ Verifikasi

### Check Status
```bash
cd /opt/pzem-monitoring
docker-compose ps
```

### Check Logs
```bash
docker-compose logs -f
```

### Test Access
- Dashboard: http://103.31.39.189:5000
- Domain: https://pzem.moof-set.web.id (setelah SSL setup)
- Health: http://103.31.39.189:5000/health

## 📋 Checklist

- [ ] Deployment selesai
- [ ] Services running (`docker-compose ps`)
- [ ] Dashboard accessible
- [ ] Nginx configured
- [ ] SSL certificate obtained
- [ ] .env updated dengan MQTT broker
- [ ] MQTT listener running
- [ ] Test report generation

## 🔧 Troubleshooting

### Port 5000 sudah digunakan
```bash
# Check
sudo netstat -tulpn | grep :5000

# Stop service yang menggunakan port
sudo systemctl stop <service-name>
```

### Nginx 502 Bad Gateway
```bash
# Check dashboard
docker-compose ps dashboard
docker-compose logs dashboard

# Restart
docker-compose restart dashboard
```

### SSL Certificate Failed
```bash
# Check DNS
nslookup pzem.moof-set.web.id

# Retry
sudo certbot --nginx -d pzem.moof-set.web.id
```

## 📞 Quick Commands

```bash
# SSH ke VPS
ssh foom@103.31.39.189

# Check status
cd /opt/pzem-monitoring && docker-compose ps

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Stop
docker-compose down

# Start
docker-compose up -d
```

---

**✅ Siap deploy!** Jalankan `./deploy-vps-fresh.sh` untuk memulai.
