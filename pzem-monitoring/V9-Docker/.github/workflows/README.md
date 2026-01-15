# GitHub Actions Workflows

Koleksi workflow CI/CD untuk PZEM Monitoring System.

## 📋 Workflows

### 1. `ci.yml` - Continuous Integration
- **Trigger**: Push/PR ke main/master/develop
- **Fungsi**: Test, lint, build Docker images
- **Status**: ✅ Required untuk merge

### 2. `deploy.yml` - Continuous Deployment
- **Trigger**: Push ke main/master atau manual
- **Fungsi**: Deploy otomatis ke VPS
- **Status**: 🚀 Production deployment

### 3. `deploy-manual.yml` - Manual Deployment
- **Trigger**: Manual only
- **Fungsi**: Deploy dengan opsi fresh deployment
- **Status**: 🔧 Manual control

### 4. `release.yml` - Release Package
- **Trigger**: Release created/published
- **Fungsi**: Create release package
- **Status**: 📦 Release artifacts

## 🔧 Setup

Lihat [SETUP_CI_CD.md](./SETUP_CI_CD.md) untuk panduan lengkap setup.

## 📝 Quick Start

1. **Setup GitHub Secrets** (lihat SETUP_CI_CD.md)
2. **Push ke main** → Automatic deployment
3. **Manual deploy** → Actions → Manual Deploy to VPS

## 🔍 Monitoring

- **GitHub Actions**: Tab "Actions" di repository
- **VPS**: `ssh foom@103.31.39.189` → `cd /opt/pzem-monitoring` → `docker-compose ps`

