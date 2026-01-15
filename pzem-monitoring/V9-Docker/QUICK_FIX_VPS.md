# 🔧 Quick Fix untuk VPS - Update Script Auto-Detect

## Opsi 1: Edit Langsung di VPS (Paling Cepat) ⚡

SSH ke VPS dan edit `update.sh`:

```bash
cd /opt/pzem-monitoring
nano update.sh
```

**Tambahkan setelah baris 6** (setelah `print_info() { ... }`):

```bash
# Detect docker-compose command (support both docker-compose and docker compose)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    print_error "docker-compose not found. Please install docker-compose first."
    exit 1
fi
```

**Lalu ganti semua `docker-compose` dengan `$DOCKER_COMPOSE`** di seluruh file.

**Atau gunakan sed untuk auto-replace:**

```bash
cd /opt/pzem-monitoring

# Backup dulu
cp update.sh update.sh.backup

# Tambahkan auto-detect setelah line 6
sed -i '6a\
# Detect docker-compose command (support both docker-compose and docker compose)\
if command -v docker-compose &> /dev/null; then\
    DOCKER_COMPOSE="docker-compose"\
elif docker compose version &> /dev/null; then\
    DOCKER_COMPOSE="docker compose"\
else\
    print_error "docker-compose not found. Please install docker-compose first."\
    exit 1\
fi
' update.sh

# Replace semua docker-compose dengan $DOCKER_COMPOSE
sed -i 's/docker-compose/$DOCKER_COMPOSE/g' update.sh

# Fix line endings
sed -i 's/\r$//' update.sh
chmod +x update.sh
```

---

## Opsi 2: Upload Hanya File yang Berubah 📤

**Di Windows:**
1. Jalankan `package.bat` untuk generate package baru
2. Extract ZIP lokal
3. Upload hanya file yang berubah:

```bash
# Di Windows PowerShell atau CMD
scp start.sh user@vps-ip:/opt/pzem-monitoring/
scp update.sh user@vps-ip:/opt/pzem-monitoring/
```

**Di VPS:**
```bash
cd /opt/pzem-monitoring
sed -i 's/\r$//' update.sh start.sh
chmod +x update.sh start.sh
```

---

## Opsi 3: Re-Package (Tapi Tidak Perlu ubuntu-deploy.sh) 📦

**Di Windows:**
```cmd
package.bat
```

**Upload ke VPS:**
```bash
# Upload ke home directory
scp pzem-monitoring-ubuntu-*.zip user@vps-ip:~/

# Di VPS
cd /opt/pzem-monitoring
sudo mv ~/pzem-monitoring-ubuntu-*.zip /tmp/
cd /tmp
unzip pzem-monitoring-ubuntu-*.zip

# Copy hanya file yang berubah
cp pzem-monitoring-ubuntu/update.sh /opt/pzem-monitoring/
cp pzem-monitoring-ubuntu/start.sh /opt/pzem-monitoring/

# Fix permissions
cd /opt/pzem-monitoring
sed -i 's/\r$//' update.sh start.sh
chmod +x update.sh start.sh
```

---

## ✅ Verifikasi

Setelah fix, test:

```bash
cd /opt/pzem-monitoring
./update.sh
```

Jika masih error, cek:
```bash
docker compose version  # Test plugin
docker-compose --version  # Test standalone
```

---

## 🎯 Rekomendasi

**Gunakan Opsi 1** jika Anda nyaman dengan nano/vi editor - paling cepat dan tidak perlu upload file.

**Gunakan Opsi 2** jika Anda ingin file yang konsisten dengan versi lokal.

**Gunakan Opsi 3** hanya jika Anda ingin update banyak file sekaligus.











