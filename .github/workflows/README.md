# CI/CD GitHub Actions Workflows yeah

Dokumentasi untuk setup dan penggunaan CI/CD workflows untuk PZEM Monitoring Project.

## 📋 Overview

Workflows ini menyediakan:
- ✅ **Automated Testing**: Linting, unit tests, dan build verification
- ✅ **Docker Build**: Build dan test Docker images
- ✅ **Security Scanning**: Vulnerability scanning dengan Trivy
- ✅ **Automatic Deployment**: Deploy ke VPS saat push ke main/master
- ✅ **Manual Deployment**: Deploy manual via GitHub Actions UI

## 🔧 Setup GitHub Secrets

Sebelum menggunakan workflows, Anda perlu mengkonfigurasi GitHub Secrets:

### Langkah-langkah Setup:

1. **Buka Repository Settings**
   - Pergi ke repository GitHub Anda
   - Klik **Settings** → **Secrets and variables** → **Actions**

2. **Tambahkan Secrets Berikut:**

   | Secret Name | Description | Contoh Value |
   |------------|-------------|--------------|
   | `VPS_SSH_KEY` | Private SSH key untuk akses VPS | `-----BEGIN RSA PRIVATE KEY-----...` atau `-----BEGIN OPENSSH PRIVATE KEY-----...` |
   | `VPS_HOST` | Hostname atau IP VPS (optional) | `103.31.39.189` (default jika tidak di-set) |

### Generate SSH Key (jika belum ada):

```bash
# Generate SSH key pair
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions_deploy

# Copy public key ke VPS
ssh-copy-id -i ~/.ssh/github_actions_deploy.pub foom@ProductionDashboard

# Copy private key untuk GitHub Secret
cat ~/.ssh/github_actions_deploy
# Copy seluruh output (termasuk BEGIN dan END lines) ke GitHub Secret VPS_SSH_KEY
```

### Alternatif: Gunakan Password Authentication

Jika tidak ingin menggunakan SSH key, Anda bisa memodifikasi workflow untuk menggunakan password, namun **tidak disarankan** untuk keamanan.

## 📁 Workflows

### 1. CI Workflow (`ci.yml`)

**Trigger:**
- Push ke branch `main`, `master`, atau `develop`
- Pull request ke branch `main`, `master`, atau `develop`
- Hanya trigger jika ada perubahan di `pzem-monitoring/V9-Docker/**`

**Jobs:**
- **test**: Linting, unit tests, database connection test
- **build**: Build Docker images untuk dashboard dan MQTT client
- **security**: Vulnerability scanning dengan Trivy

### 2. CD Workflow (`deploy.yml`)

**Trigger:**
- Push ke branch `main` atau `master`
- Manual trigger via `workflow_dispatch` dengan pilihan environment

**Jobs:**
- **deploy**: 
  - Membuat deployment package
  - Upload ke VPS
  - Backup existing deployment
  - Extract dan deploy
  - Build dan start Docker containers
  - Verify deployment

**Deployment Path:**
- VPS User: `foom`
- VPS Host: `103.31.39.189` (IP address)
- Deploy Directory: `/opt/pzem-monitoring`

## 🚀 Usage

### Automatic Deployment

1. Push ke branch `main` atau `master`
2. CI workflow akan berjalan otomatis
3. Jika CI berhasil, CD workflow akan deploy ke VPS

### Manual Deployment

1. Pergi ke **Actions** tab di GitHub
2. Pilih workflow **CD - Deploy to Production VPS**
3. Klik **Run workflow**
4. Pilih branch dan environment
5. Klik **Run workflow**

## 🔍 Monitoring

### Check Workflow Status

- Pergi ke **Actions** tab untuk melihat status workflows
- Klik pada workflow run untuk melihat detail logs

### Check Deployment Status

Setelah deployment, workflow akan menampilkan:
- Service status
- Running containers
- Access URLs

## 🛠️ Troubleshooting

### Deployment Gagal

1. **Check SSH Connection:**
   ```powershell
   # Windows PowerShell
   ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189
   ```

2. **Check Docker:**
   ```powershell
   # Windows PowerShell
   ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189 "docker ps"
   ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189 "docker-compose version"
   ```

3. **Check Disk Space:**
   ```powershell
   ssh -i "C:\Users\info\.ssh\github_actions_vps" foom@103.31.39.189 "df -h /opt"
   ```

4. **Check Logs:**
   - Lihat workflow logs di GitHub Actions
   - Check deployment logs di VPS: `/opt/pzem-monitoring`

### CI Tests Gagal

1. **Linting Errors:**
   - Fix code style issues
   - Check flake8 output

2. **Test Failures:**
   - Check test output
   - Verify database connection settings

3. **Build Failures:**
   - Check Dockerfile syntax
   - Verify dependencies

## 📝 Notes

- Backup otomatis dibuat sebelum deployment di `/opt/backups/pzem-monitoring`
- Database backup dibuat jika container berjalan
- `.env` file akan di-restore dari backup jika ada
- Deployment akan preserve Docker volumes untuk data persistence

## 🔐 Security

- SSH keys disimpan sebagai GitHub Secrets (encrypted)
- Tidak ada credentials hardcoded di workflows
- Security scanning otomatis dengan Trivy
- SARIF results di-upload ke GitHub Security

## 📞 Support

Jika ada masalah:
1. Check workflow logs
2. Verify GitHub Secrets configuration
3. Test SSH connection manual
4. Check VPS resources (disk, memory)
