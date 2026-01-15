# 📦 Panduan Transfer Project Tanpa Git

Panduan lengkap untuk mentransfer project PZEM Monitoring ke server Ubuntu tanpa menggunakan Git.

## 🎯 Metode Transfer

### Metode 1: Package Script (Paling Mudah) ⭐

#### Windows → Ubuntu VPS

**Step 1: Buat Package di Windows**

```cmd
# Jalankan script package
package.bat
```

Script ini akan membuat file ZIP: `pzem-monitoring-ubuntu-YYYYMMDD_HHMMSS.zip`

**Step 2: Upload ke VPS**

**Opsi A: Menggunakan SCP (Command Line)**

⚠️ **PENTING**: User biasanya tidak punya permission langsung ke `/opt/`. Upload ke home directory dulu!

```bash
# Dari Windows (PowerShell atau Git Bash)
# Upload ke home directory dulu (biasanya ~ atau /home/username)
scp pzem-monitoring-ubuntu-20251811_081518.zip user@your-vps-ip:~/

# Atau upload ke /tmp (temporary directory)
scp pzem-monitoring-ubuntu-20251811_081518.zip user@your-vps-ip:/tmp/
```

Kemudian di VPS, pindahkan ke /opt/ dengan sudo:
```bash
ssh user@your-vps-ip
# Pindahkan dari home ke /opt/
sudo mv ~/pzem-monitoring-ubuntu-*.zip /opt/
# Atau jika upload ke /tmp:
sudo mv /tmp/pzem-monitoring-ubuntu-*.zip /opt/
```

**Opsi B: Menggunakan WinSCP (GUI)**
1. Download WinSCP: https://winscp.net/
2. Connect ke VPS dengan SSH
3. **Upload ke home directory dulu** (biasanya `/home/username/` atau `~`)
4. Di WinSCP, klik kanan file → Move/Rename → pindahkan ke `/opt/` (akan minta password sudo)
5. Atau gunakan terminal di WinSCP untuk pindahkan dengan sudo

**Opsi C: Menggunakan FileZilla (FTP/SFTP)**
1. Download FileZilla: https://filezilla-project.org/
2. Connect dengan SFTP protocol
3. **Upload ke home directory dulu** (`/home/username/`)
4. Setelah upload, gunakan terminal untuk pindahkan:
   ```bash
   sudo mv ~/pzem-monitoring-ubuntu-*.zip /opt/
   ```

**Step 3: Extract dan Deploy di VPS**

```bash
# SSH ke VPS
ssh user@your-vps-ip

# Jika upload ke home directory, pindahkan dulu ke /opt/
sudo mv ~/pzem-monitoring-ubuntu-*.zip /opt/
# Atau jika upload ke /tmp:
sudo mv /tmp/pzem-monitoring-ubuntu-*.zip /opt/

# Masuk ke directory
cd /opt

# Install unzip jika belum ada
sudo apt update && sudo apt install unzip -y

# Extract package (perlu sudo karena di /opt/)
sudo unzip pzem-monitoring-ubuntu-*.zip

# Jika folder sudah ada, backup dulu
if [ -d "pzem-monitoring" ]; then
    sudo mv pzem-monitoring pzem-monitoring-backup-$(date +%Y%m%d_%H%M%S)
fi

# Rename folder
sudo mv pzem-monitoring-ubuntu pzem-monitoring

# Set ownership (ganti 'user' dengan username Anda)
sudo chown -R $USER:$USER /opt/pzem-monitoring

# Masuk ke folder
cd pzem-monitoring

# Deploy
chmod +x ubuntu-deploy.sh
sudo ./ubuntu-deploy.sh
```

---

### Metode 2: Transfer Langsung dengan SCP (Tanpa Package)

**Step 1: Kompresi Manual di Windows**

```cmd
# Buat folder untuk transfer
mkdir pzem-transfer
xcopy /E /I /Y dashboard pzem-transfer\dashboard
xcopy /E /I /Y mqtt pzem-transfer\mqtt
copy docker-compose.yml pzem-transfer\
copy ubuntu-deploy.sh pzem-transfer\
copy start.sh pzem-transfer\
copy *.md pzem-transfer\

# Kompres dengan 7-Zip atau WinRAR
# Buat file: pzem-transfer.zip
```

**Step 2: Upload ke VPS**

```bash
# Upload folder
scp -r pzem-transfer.zip user@your-vps-ip:/opt/
```

**Step 3: Extract di VPS**

```bash
ssh user@your-vps-ip
cd /opt
unzip pzem-transfer.zip
mv pzem-transfer pzem-monitoring
cd pzem-monitoring
chmod +x ubuntu-deploy.sh
sudo ./ubuntu-deploy.sh
```

---

### Metode 3: Transfer dengan USB Drive

**Step 1: Copy ke USB**

```cmd
# Copy semua file ke USB drive
xcopy /E /I /Y *.* E:\pzem-monitoring\
```

**Step 2: Transfer ke VPS**

```bash
# Di VPS, mount USB atau copy via network share
# Atau gunakan scp dari komputer lain yang sudah copy dari USB

# Contoh jika USB sudah di-mount di VPS:
sudo cp -r /media/usb/pzem-monitoring /opt/
cd /opt/pzem-monitoring
chmod +x ubuntu-deploy.sh
sudo ./ubuntu-deploy.sh
```

---

### Metode 4: Transfer dengan Cloud Storage

**Step 1: Upload ke Cloud**

- **Google Drive**: Upload ZIP file
- **Dropbox**: Upload ZIP file
- **OneDrive**: Upload ZIP file
- **Mega.nz**: Upload ZIP file

**Step 2: Download di VPS**

```bash
# Install wget atau curl
sudo apt install wget curl -y

# Download dari Google Drive (gunakan shareable link)
# Atau gunakan rclone untuk sync

# Contoh dengan wget (jika ada direct link):
wget -O pzem-monitoring.zip "YOUR_CLOUD_DOWNLOAD_LINK"

# Extract
unzip pzem-monitoring.zip
cd pzem-monitoring
chmod +x ubuntu-deploy.sh
sudo ./ubuntu-deploy.sh
```

---

### Metode 5: Transfer dengan rsync (Jika Ada Akses Network)

**Step 1: Install rsync di Windows**

Download: https://www.itefix.net/cwrsync

**Step 2: Sync ke VPS**

```cmd
# Di Windows Command Prompt
rsync -avz --exclude '__pycache__' --exclude '*.log' --exclude '*.pyc' ^
  ./dashboard/ user@your-vps-ip:/opt/pzem-monitoring/dashboard/
rsync -avz --exclude '__pycache__' --exclude '*.log' --exclude '*.pyc' ^
  ./mqtt/ user@your-vps-ip:/opt/pzem-monitoring/mqtt/
rsync -avz docker-compose.yml ubuntu-deploy.sh start.sh ^
  user@your-vps-ip:/opt/pzem-monitoring/
```

**Step 3: Deploy di VPS**

```bash
ssh user@your-vps-ip
cd /opt/pzem-monitoring
chmod +x ubuntu-deploy.sh
sudo ./ubuntu-deploy.sh
```

---

## 📋 Checklist File yang Perlu Ditransfer

### File Wajib:
- ✅ `docker-compose.yml`
- ✅ `ubuntu-deploy.sh`
- ✅ `start.sh`
- ✅ Folder `dashboard/` (semua file kecuali `__pycache__`, `*.log`)
- ✅ Folder `mqtt/` (semua file kecuali `__pycache__`, `*.log`)
- ✅ `README.md` atau `UBUNTU-DEPLOYMENT.md`

### File Opsional:
- ⚠️ `.env` (jika sudah dikonfigurasi, jangan lupa edit password di VPS)
- ⚠️ `env.example` (template untuk konfigurasi)
- ⚠️ Folder `reports/` (jika ada report yang ingin dipertahankan)

### File yang TIDAK Perlu:
- ❌ `__pycache__/` (akan dibuat ulang)
- ❌ `*.log` (log files)
- ❌ `*.pyc` (compiled Python files)
- ❌ `node_modules/` (jika ada)
- ❌ `.git/` (jika ada)

---

## 🔧 Script Bantuan untuk Windows

### Script untuk Exclude File yang Tidak Perlu

Buat file `package-clean.bat`:

```batch
@echo off
echo Creating clean package...

set PACKAGE_DIR=pzem-monitoring-clean
if exist "%PACKAGE_DIR%" rmdir /s /q "%PACKAGE_DIR%"
mkdir "%PACKAGE_DIR%"

echo Copying files...
xcopy /E /I /Y /EXCLUDE:exclude.txt dashboard "%PACKAGE_DIR%\dashboard"
xcopy /E /I /Y /EXCLUDE:exclude.txt mqtt "%PACKAGE_DIR%\mqtt"
copy docker-compose.yml "%PACKAGE_DIR%\"
copy ubuntu-deploy.sh "%PACKAGE_DIR%\"
copy start.sh "%PACKAGE_DIR%\"
copy *.md "%PACKAGE_DIR%\"

echo Creating exclude.txt...
(
echo __pycache__
echo *.log
echo *.pyc
echo .git
echo node_modules
) > exclude.txt

echo Creating ZIP...
powershell Compress-Archive -Path "%PACKAGE_DIR%\*" -DestinationPath "pzem-clean.zip" -Force

rmdir /s /q "%PACKAGE_DIR%"
echo Done! File: pzem-clean.zip
pause
```

---

## 🚀 Quick Transfer Commands

### Windows PowerShell (Paling Cepat)

```powershell
# 1. Buat package
.\package.bat

# 2. Upload ke home directory (recommended - no permission issue)
$zipFile = Get-ChildItem pzem-monitoring-ubuntu-*.zip | Sort-Object LastWriteTime -Descending | Select-Object -First 1
scp $zipFile.Name user@your-vps-ip:~/

# 3. Di VPS, pindahkan ke /opt/
# ssh user@your-vps-ip
# sudo mv ~/pzem-monitoring-ubuntu-*.zip /opt/
```

### Windows - Automated Upload Script

```cmd
# Gunakan script upload otomatis
upload-to-vps.bat
```

Script ini akan:
- Mencari package file terbaru
- Menanyakan VPS username dan IP
- Memberikan opsi upload (home, /tmp, atau /opt/)
- Menampilkan instruksi lengkap untuk deploy

### Windows CMD

```cmd
# 1. Buat package
package.bat

# 2. Upload dengan WinSCP atau FileZilla (GUI lebih mudah)
```

### Linux/Mac (Jika Ada)

```bash
# 1. Buat tar.gz
tar -czf pzem-monitoring.tar.gz \
  --exclude='__pycache__' \
  --exclude='*.log' \
  --exclude='*.pyc' \
  dashboard/ mqtt/ docker-compose.yml ubuntu-deploy.sh start.sh *.md

# 2. Upload
scp pzem-monitoring.tar.gz user@your-vps-ip:/opt/

# 3. Di VPS
ssh user@your-vps-ip
cd /opt
tar -xzf pzem-monitoring.tar.gz
mv pzem-monitoring-* pzem-monitoring
cd pzem-monitoring
chmod +x ubuntu-deploy.sh
sudo ./ubuntu-deploy.sh
```

---

## ✅ Verifikasi Transfer

Setelah transfer, verifikasi di VPS:

```bash
# Check file structure
cd /opt/pzem-monitoring
ls -la

# Check file permissions
chmod +x *.sh

# Verify docker-compose.yml exists
cat docker-compose.yml

# Check dashboard files
ls -la dashboard/

# Check mqtt files
ls -la mqtt/
```

---

## 🆘 Troubleshooting

### Problem: File terlalu besar untuk transfer

**Solusi:**
```bash
# Exclude file besar
tar -czf pzem-small.tar.gz \
  --exclude='*.log' \
  --exclude='__pycache__' \
  --exclude='reports/*.pdf' \
  dashboard/ mqtt/ docker-compose.yml *.sh *.md
```

### Problem: Permission denied saat upload ke /opt/

**Solusi:**
```bash
# Upload ke home directory dulu (tidak perlu permission)
scp pzem-monitoring-ubuntu-*.zip user@vps-ip:~/

# Di VPS, pindahkan dengan sudo
ssh user@vps-ip
sudo mv ~/pzem-monitoring-ubuntu-*.zip /opt/
cd /opt
sudo unzip pzem-monitoring-ubuntu-*.zip
sudo mv pzem-monitoring-ubuntu pzem-monitoring
sudo chown -R $USER:$USER /opt/pzem-monitoring
```

**Alternatif: Berikan permission ke /opt/ (tidak direkomendasikan untuk production)**
```bash
# Hanya jika benar-benar diperlukan
sudo chmod 777 /opt  # Temporary, untuk upload
# Setelah upload, kembalikan permission:
sudo chmod 755 /opt
```

### Problem: Connection timeout saat upload

**Solusi:**
```bash
# Gunakan compression yang lebih baik
# Atau split file besar menjadi beberapa bagian
split -b 50M pzem-monitoring.zip pzem-part-
# Upload satu per satu, lalu join di VPS:
cat pzem-part-* > pzem-monitoring.zip
```

---

## 📝 Tips

1. **Selalu gunakan package.bat** untuk memastikan semua file penting termasuk
2. **Backup dulu** jika update ke server yang sudah running
3. **Test di local** sebelum deploy ke production
4. **Gunakan .env** untuk konfigurasi, jangan hardcode password
5. **Verifikasi file size** setelah transfer untuk memastikan tidak corrupt

---

## 🎯 Rekomendasi

**Untuk transfer pertama kali:** Gunakan **Metode 1 (Package Script)** - paling mudah dan aman

**Untuk update berkala:** Gunakan **Metode 2 (SCP langsung)** - lebih cepat untuk perubahan kecil

**Untuk transfer besar:** Gunakan **Metode 4 (Cloud Storage)** - lebih reliable untuk file besar

