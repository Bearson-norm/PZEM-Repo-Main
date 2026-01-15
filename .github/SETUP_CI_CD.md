# Setup CI/CD untuk PZEM Monitoring Project

Panduan lengkap untuk setup CI/CD dengan GitHub Actions untuk deployment otomatis ke VPS.

## 🎯 Lokasi Deployment

- **VPS User**: `foom`
- **VPS Host**: `103.31.39.189` (IP address)
- **Deploy Directory**: `/opt/pzem-monitoring`

## 📋 Prerequisites

1. Repository GitHub sudah di-setup
2. Akses SSH ke VPS `foom@ProductionDashboard`
3. Docker dan Docker Compose sudah terinstall di VPS
4. Python 3.11+ untuk testing lokal (optional)

## 🔑 Setup GitHub Secrets

### Langkah 1: Gunakan SSH Key yang Sudah Ada

Jika Anda sudah punya SSH key yang bisa connect ke VPS, gunakan key tersebut.

**Windows PowerShell:**
```powershell
# Test koneksi dengan key yang sudah ada
ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189

# Jika berhasil, lanjut ke langkah berikutnya
```

**Catatan**: Pastikan key ini sudah ada di VPS `authorized_keys`. Jika belum:
```powershell
# Copy public key ke clipboard
Get-Content "C:\Users\info\.ssh\github_actions_vps.pub" | Set-Clipboard

# SSH ke VPS dan paste ke authorized_keys
ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189
# Kemudian di VPS:
# mkdir -p ~/.ssh
# echo "<paste-public-key>" >> ~/.ssh/authorized_keys
# chmod 600 ~/.ssh/authorized_keys
```

### Langkah 2: Setup GitHub Secrets

**Cara Mudah (Menggunakan Script):**

Jalankan script PowerShell yang sudah disediakan:

```powershell
# Dari root project
cd .github
.\setup-github-secrets.ps1
```

Script akan:
- Menampilkan SSH key yang perlu di-copy
- Copy key ke clipboard otomatis
- Memberikan instruksi langkah selanjutnya

**Cara Manual:**

1. Buka repository GitHub Anda
2. Pergi ke **Settings** → **Secrets and variables** → **Actions**
3. Klik **New repository secret**

#### Secret 1: `VPS_SSH_KEY`
- **Name**: `VPS_SSH_KEY`
- **Value**: Copy seluruh isi file private key

**Windows PowerShell:**
```powershell
# Baca isi private key
Get-Content "C:\Users\info\.ssh\github_actions_vps" -Raw

# Copy seluruh output (termasuk BEGIN dan END lines)
# Paste ke GitHub Secret VPS_SSH_KEY
```

**Format yang benar:**
```
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
...
-----END RSA PRIVATE KEY-----
```

**Atau jika format OpenSSH:**
```
-----BEGIN OPENSSH PRIVATE KEY-----
...
-----END OPENSSH PRIVATE KEY-----
```

#### Secret 2: `VPS_HOST` (Optional)
- **Name**: `VPS_HOST`
- **Value**: `103.31.39.189`
- **Note**: Jika tidak di-set, akan menggunakan default `103.31.39.189`

## ✅ Verifikasi Setup

### Test Workflow Manual

1. Pergi ke tab **Actions** di GitHub
2. Pilih workflow **CD - Deploy to Production VPS**
3. Klik **Run workflow**
4. Pilih branch `main` atau `master`
5. Klik **Run workflow**

### Check Logs

- Monitor workflow execution di tab **Actions**
- Jika ada error, check logs untuk detail

## 🔄 Workflow Otomatis

Setelah setup, workflows akan berjalan otomatis:

### CI Workflow
- **Trigger**: Push atau PR ke `main`, `master`, atau `develop`
- **Aksi**: 
  - Linting code
  - Unit tests
  - Build Docker images
  - Security scanning

### CD Workflow
- **Trigger**: Push ke `main` atau `master`
- **Aksi**:
  - Build deployment package
  - Backup existing deployment
  - Deploy ke VPS
  - Start Docker containers
  - Verify deployment

## 🛠️ Troubleshooting

### Error: SSH Connection Failed

**Penyebab**: SSH key tidak valid atau VPS tidak accessible

**Solusi**:
```powershell
# Test SSH connection manual (Windows)
ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189

# Check SSH key format di GitHub Secret
# Pastikan include BEGIN dan END lines
# Pastikan tidak ada extra spaces atau line breaks
```

### Error: Docker Not Found

**Penyebab**: Docker tidak terinstall di VPS

**Solusi**:
```powershell
# SSH ke VPS (Windows)
ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189

# Di VPS, check Docker
docker --version
docker-compose --version

# Install jika belum ada
# (sesuai dengan OS VPS)
```

### Error: Permission Denied

**Penyebab**: User tidak punya permission ke `/opt/pzem-monitoring`

**Solusi**:
```powershell
# SSH ke VPS (Windows)
ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189

# Di VPS, check permission
ls -la /opt/

# Fix permission (jika perlu)
sudo mkdir -p /opt/pzem-monitoring
sudo chown -R foom:foom /opt/pzem-monitoring
```

### Error: Port Already in Use

**Penyebab**: Port 5000 sudah digunakan

**Solusi**:
```powershell
# Check port usage (Windows)
ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189 "netstat -tulpn | grep 5000"

# Stop existing container
ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189 "cd /opt/pzem-monitoring && docker-compose down"
```

## 📊 Monitoring Deployment

### Check Service Status

```powershell
# Windows PowerShell
ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189 "cd /opt/pzem-monitoring && docker-compose ps"
```

### Check Logs

```powershell
# Dashboard logs
ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189 "cd /opt/pzem-monitoring && docker-compose logs dashboard"

# MQTT logs
ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189 "cd /opt/pzem-monitoring && docker-compose logs mqtt-listener"

# Database logs
ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189 "cd /opt/pzem-monitoring && docker-compose logs db"
```

### Check Health

```powershell
# Health check dari lokal
curl http://103.31.39.189:5000/health

# Atau dari VPS
ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189 "curl http://localhost:5000/health"
```

## 🔐 Security Best Practices

1. **SSH Key Security**:
   - Jangan commit SSH keys ke repository
   - Gunakan GitHub Secrets untuk store keys
   - Rotate keys secara berkala

2. **VPS Security**:
   - Update sistem secara berkala
   - Gunakan firewall
   - Monitor logs

3. **Docker Security**:
   - Update images secara berkala
   - Scan untuk vulnerabilities
   - Gunakan non-root user di containers

## 📝 Notes

- Backup otomatis dibuat di `/opt/backups/pzem-monitoring`
- Database backup dibuat sebelum deployment
- `.env` file akan di-restore dari backup
- Docker volumes di-preserve untuk data persistence

## 🆘 Support

Jika ada masalah:
1. Check workflow logs di GitHub Actions
2. Check deployment logs di VPS
3. Verify semua prerequisites terpenuhi
4. Test SSH connection manual

## 📚 Referensi

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [SSH Key Setup](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
