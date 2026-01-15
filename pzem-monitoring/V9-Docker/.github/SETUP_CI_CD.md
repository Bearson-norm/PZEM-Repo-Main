# 🔄 Setup CI/CD dengan GitHub Actions

Panduan lengkap untuk setup CI/CD otomatis dengan GitHub Actions untuk PZEM Monitoring System.

## 📋 Overview

Sistem CI/CD ini menyediakan:
- ✅ **CI (Continuous Integration)**: Test dan build otomatis
- ✅ **CD (Continuous Deployment)**: Deploy otomatis ke VPS
- ✅ **Manual Deploy**: Deploy manual dengan opsi fresh deployment
- ✅ **Release**: Package untuk release

## 🔧 Setup GitHub Secrets

Sebelum menggunakan CI/CD, setup GitHub Secrets terlebih dahulu:

### Step 1: Generate SSH Key untuk VPS

```bash
# Generate SSH key (jika belum ada)
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions_vps

# Copy public key ke VPS
ssh-copy-id -i ~/.ssh/github_actions_vps.pub foom@103.31.39.189

# Atau manual copy
cat ~/.ssh/github_actions_vps.pub
# Copy output dan paste ke VPS: ~/.ssh/authorized_keys
```

### Step 2: Setup GitHub Secrets

1. **Buka repository di GitHub**
2. **Settings → Secrets and variables → Actions**
3. **Klik "New repository secret"**
4. **Tambahkan secrets berikut:**

| Secret Name | Value | Description |
|------------|-------|-------------|
| `VPS_USER` | `foom` | Username SSH untuk VPS |
| `VPS_HOST` | `103.31.39.189` | IP atau hostname VPS |
| `VPS_SSH_KEY` | `(isi dengan private key)` | Private SSH key untuk akses VPS |

**Cara mendapatkan VPS_SSH_KEY:**
```bash
# Di local machine
cat ~/.ssh/github_actions_vps
# Copy seluruh output (termasuk -----BEGIN dan -----END)
```

### Step 3: Verify SSH Access

```bash
# Test SSH connection
ssh -i ~/.ssh/github_actions_vps foom@103.31.39.189
```

## 🚀 Workflow yang Tersedia

### 1. CI - Build and Test (`ci.yml`)

**Trigger:**
- Push ke branch `main`, `master`, atau `develop`
- Pull request ke branch `main`, `master`, atau `develop`

**Aksi:**
- ✅ Lint code dengan flake8
- ✅ Test database connection
- ✅ Test PLN Calculator
- ✅ Test imports
- ✅ Build Docker images
- ✅ Security scan dengan Trivy

**Lihat hasil:** Actions tab → CI - Build and Test

### 2. CD - Deploy to VPS (`deploy.yml`)

**Trigger:**
- Push ke branch `main` atau `master`
- Manual trigger via workflow_dispatch

**Aksi:**
- ✅ Create deployment package
- ✅ Upload ke VPS
- ✅ Backup database existing
- ✅ Deploy aplikasi baru
- ✅ Verify deployment
- ✅ Health check

**Lihat hasil:** Actions tab → CD - Deploy to VPS

### 3. Manual Deploy (`deploy-manual.yml`)

**Trigger:**
- Manual trigger via workflow_dispatch

**Opsi:**
- **Environment**: production atau staging
- **Fresh Deploy**: true/false (hapus database atau tidak)

**Cara menggunakan:**
1. Buka **Actions** tab
2. Pilih **Manual Deploy to VPS**
3. Klik **Run workflow**
4. Pilih environment dan fresh deploy
5. Klik **Run workflow**

### 4. Release (`release.yml`)

**Trigger:**
- Saat release dibuat atau dipublish

**Aksi:**
- ✅ Create release package
- ✅ Upload sebagai artifact

## 📝 Cara Menggunakan

### Automatic Deployment

1. **Push ke main/master:**
   ```bash
   git add .
   git commit -m "Update application"
   git push origin main
   ```

2. **GitHub Actions akan otomatis:**
   - Run CI tests
   - Build Docker images
   - Deploy ke VPS
   - Verify deployment

3. **Cek status:**
   - Buka **Actions** tab di GitHub
   - Lihat workflow yang sedang berjalan
   - Cek logs jika ada error

### Manual Deployment

1. **Buka GitHub repository**
2. **Klik tab "Actions"**
3. **Pilih "Manual Deploy to VPS"**
4. **Klik "Run workflow"**
5. **Pilih opsi:**
   - Environment: production
   - Fresh Deploy: false (untuk preserve database)
6. **Klik "Run workflow"**

### Fresh Deployment (Hapus Database)

1. **Buka "Manual Deploy to VPS"**
2. **Pilih:**
   - Environment: production
   - Fresh Deploy: **true** ⚠️
3. **Klik "Run workflow"**

⚠️ **WARNING**: Fresh deployment akan menghapus database!

## 🔍 Monitoring Deployment

### Di GitHub

1. **Actions Tab:**
   - Lihat semua workflow runs
   - Cek status (✅ success, ❌ failed, 🟡 in progress)
   - Lihat logs untuk troubleshooting

2. **Workflow Summary:**
   - Deployment summary
   - Access URLs
   - Service status

### Di VPS

```bash
# SSH ke VPS
ssh foom@103.31.39.189

# Check deployment status
cd /opt/pzem-monitoring
docker-compose ps

# View logs
docker-compose logs -f

# Check health
curl http://localhost:5000/health
```

## 🔧 Troubleshooting

### Issue: SSH Connection Failed

**Error:** `Permission denied (publickey)`

**Solusi:**
1. Verify SSH key di GitHub Secrets
2. Test SSH connection manual:
   ```bash
   ssh -i ~/.ssh/github_actions_vps foom@103.31.39.189
   ```
3. Pastikan public key ada di VPS:
   ```bash
   # Di VPS
   cat ~/.ssh/authorized_keys
   ```

### Issue: Deployment Failed

**Error:** `docker-compose not found`

**Solusi:**
```bash
# Di VPS, install docker-compose
sudo apt update
sudo apt install docker-compose-plugin -y
# atau
sudo pip3 install docker-compose
```

### Issue: Database Connection Failed

**Error:** `Database did not become ready`

**Solusi:**
```bash
# Di VPS
cd /opt/pzem-monitoring
docker-compose logs db
docker-compose restart db
```

### Issue: Health Check Failed

**Error:** `Health check failed`

**Solusi:**
```bash
# Di VPS
cd /opt/pzem-monitoring
docker-compose logs dashboard
docker-compose restart dashboard
```

## 📊 Workflow Status Badge

Tambahkan badge ke README.md:

```markdown
![CI](https://github.com/USERNAME/REPO/workflows/CI%20-%20Build%20and%20Test/badge.svg)
![CD](https://github.com/USERNAME/REPO/workflows/CD%20-%20Deploy%20to%20VPS/badge.svg)
```

## 🔐 Security Best Practices

1. **Jangan commit secrets:**
   - Gunakan GitHub Secrets
   - Jangan hardcode credentials

2. **Rotate SSH keys:**
   - Ganti SSH key secara berkala
   - Update di GitHub Secrets

3. **Limit access:**
   - Gunakan SSH key dengan passphrase
   - Limit SSH access di VPS (firewall)

4. **Monitor logs:**
   - Cek GitHub Actions logs
   - Monitor VPS logs

## 📝 Customization

### Update VPS Configuration

Edit `.github/workflows/deploy.yml`:

```yaml
env:
  VPS_USER: ${{ secrets.VPS_USER }}
  VPS_HOST: ${{ secrets.VPS_HOST }}
  VPS_DEPLOY_DIR: /opt/pzem-monitoring
  DOMAIN: pzem.moof-set.web.id
```

### Add Environment Variables

Tambahkan di `docker-compose.yml` atau `.env`:

```yaml
environment:
  - CUSTOM_VAR=${{ secrets.CUSTOM_VAR }}
```

### Custom Deployment Steps

Edit `.github/workflows/deploy.yml` → `deploy` job → steps

## 🎯 Quick Reference

```bash
# Setup SSH key
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions_vps
ssh-copy-id -i ~/.ssh/github_actions_vps.pub foom@103.31.39.189

# Test deployment manual
gh workflow run deploy-manual.yml -f environment=production -f fresh_deploy=false

# Check workflow status
gh run list --workflow=deploy.yml

# View workflow logs
gh run view <run-id> --log
```

## 📞 Support

Jika mengalami masalah:

1. **Check GitHub Actions logs**
2. **Check VPS logs:** `docker-compose logs -f`
3. **Verify secrets:** GitHub Settings → Secrets
4. **Test SSH:** `ssh -i ~/.ssh/github_actions_vps foom@103.31.39.189`

---

**✅ CI/CD siap digunakan!** Push ke main/master untuk trigger automatic deployment.

